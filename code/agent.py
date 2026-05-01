"""
agent.py — Main entry point. Terminal-based support triage agent.

Usage:
    # Process support_issues.csv and generate output.csv
    python agent.py

    # Interactive mode — test single tickets
    python agent.py --interactive

Setup (run once before agent.py):
    python scraper.py          # Scrape support sites
    python corpus_builder.py   # Build ChromaDB vector store
"""

import os
import sys
import argparse
import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import track

from pipeline import TriagePipeline
from logger import setup_logger, log_ticket

load_dotenv()
console = Console()

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DEFAULT_INPUT_CSV = os.path.join(DATA_DIR, "support_issues", "support_issues.csv")
DEFAULT_OUTPUT_CSV = os.path.join(BASE_DIR, "..", "output.csv")

# Required output columns
OUTPUT_COLUMNS = ["status", "product_area", "response", "justification", "request_type"]

def process_csv(pipeline: TriagePipeline, logger, input_csv: str, output_csv: str, limit: int = None):
    """Read input CSV, run pipeline on each row, write output CSV."""

    if not os.path.exists(input_csv):
        console.print(f"[red]Error: Input CSV not found at {input_csv}[/red]")
        sys.exit(1)

    df = pd.read_csv(input_csv)
    # Normalize column names: lowercase + replace spaces with underscores
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    if limit:
        df = df.head(limit)

    console.print(f"\n[green]Loaded {len(df)} tickets from {input_csv}[/green]")

    results = []

    for idx, row in track(df.iterrows(), total=len(df), description="Processing tickets..."):
        issue = str(row.get("issue", "")).strip()
        subject = str(row.get("subject", "")).strip()
        company = str(row.get("company", "")).strip()

        try:
            result = pipeline.process(issue, subject, company)
        except Exception as e:
            console.print(f"[red]Error on row {idx}: {e}[/red]")
            result = {
                "status": "escalated",
                "product_area": "unknown",
                "request_type": "product_issue",
                "response": "An error occurred processing this ticket. Escalating to human agent.",
                "justification": f"Pipeline error: {str(e)}"
            }

        log_ticket(logger, idx, issue, subject, company, result)
        results.append(result)

    # Build output dataframe
    output_df = pd.DataFrame(results)[OUTPUT_COLUMNS]

    # Drop any input columns that clash with output columns before merging
    input_df = df.drop(columns=[c for c in OUTPUT_COLUMNS if c in df.columns], errors="ignore")
    full_output = pd.concat([input_df.reset_index(drop=True), output_df], axis=1)
    full_output.to_csv(output_csv, index=False)

    console.print(f"\n[bold green]✓ Output saved to: {output_csv}[/bold green]")
    _print_summary(output_df)

def _print_summary(df: pd.DataFrame):
    """Print a nice summary table to terminal."""
    console.print("\n[bold]─── Triage Summary ───[/bold]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Count")

    total = len(df)
    replied = (df["status"] == "replied").sum()
    escalated = (df["status"] == "escalated").sum()

    table.add_row("Total Tickets", str(total))
    table.add_row("Replied", f"[green]{replied}[/green]")
    table.add_row("Escalated", f"[yellow]{escalated}[/yellow]")

    console.print(table)

    # Request type breakdown
    console.print("\n[bold]Request Type Breakdown:[/bold]")
    rt_counts = df["request_type"].value_counts()
    for rt, count in rt_counts.items():
        console.print(f"  {rt}: {count}")

def interactive_mode(pipeline: TriagePipeline, logger):
    """Test the agent interactively from terminal."""
    console.print("\n[bold cyan]Interactive Mode — Support Triage Agent[/bold cyan]")
    console.print("Type 'quit' to exit.\n")

    idx = 0
    while True:
        console.print("[bold]─────────────────────────────[/bold]")
        company = console.input("[cyan]Company (HackerRank/Claude/Visa/None): [/cyan]").strip()
        if company.lower() == "quit":
            break

        subject = console.input("[cyan]Subject: [/cyan]").strip()
        issue = console.input("[cyan]Issue: [/cyan]").strip()

        if not issue:
            console.print("[red]Issue cannot be empty.[/red]")
            continue

        console.print("\n[dim]Processing...[/dim]")
        result = pipeline.process(issue, subject, company)
        log_ticket(logger, idx, issue, subject, company, result)
        idx += 1


        # Display result
        console.print(f"\n[bold]Status:[/bold] {'[green]' if result['status'] == 'replied' else '[yellow]'}{result['status'].upper()}[/]")
        console.print(f"[bold]Product Area:[/bold] {result['product_area']}")
        console.print(f"[bold]Request Type:[/bold] {result['request_type']}")
        console.print(f"[bold]Response:[/bold]\n{result['response']}")
        console.print(f"[bold]Justification:[/bold] {result['justification']}")

def main():
    parser = argparse.ArgumentParser(description="Support Triage Agent")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive terminal mode")
    parser.add_argument("--input", default=None, help="Path to input CSV (default: data/support_issues/support_issues.csv)")
    parser.add_argument("--output", default=None, help="Path to output CSV (default: output.csv at repo root)")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N rows")
    args = parser.parse_args()

    # Load API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        console.print("[red]Error: GEMINI_API_KEY not set in .env file[/red]")
        sys.exit(1)

    input_csv = args.input or DEFAULT_INPUT_CSV
    output_csv = args.output or DEFAULT_OUTPUT_CSV

    console.print("[bold]Initializing Support Triage Agent...[/bold]")
    logger = setup_logger()
    pipeline = TriagePipeline(gemini_api_key)

    if args.interactive:
        interactive_mode(pipeline, logger)
    else:
        process_csv(pipeline, logger, input_csv, output_csv, args.limit)

if __name__ == "__main__":
    main()
