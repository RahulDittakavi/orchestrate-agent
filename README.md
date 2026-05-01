# Support Triage Agent — HackerRank Orchestrate Hackathon

## Setup

```bash
# 1. Install dependencies
pip install -r code/requirements.txt

# 2. Set up your API keys
cp code/.env.example code/.env
# Edit .env and add your GEMINI_API_KEY

# 3. Scrape the support corpus (run ONCE)
python code/scraper.py

# 4. Build the vector DB (run ONCE after scraping)
python code/corpus_builder.py

# 5. Place the input CSVs
# data/support_issues/support_issues.csv
# data/support_issues/sample_support_issues.csv

# 6. Run the agent
python code/agent.py

# Interactive mode (for testing)
python code/agent.py --interactive
```

## Output Files
- `output.csv` — predictions with all required columns
- `log.txt` — full chat transcript

## Architecture
- **Retriever**: ChromaDB + sentence-transformers (all-MiniLM-L6-v2) for RAG
- **LLM**: Google Gemini 1.5 Pro for classification + response generation
- **Risk Engine**: Rule-based keyword detection for fast escalation
- **Pipeline**: Input cleaning → domain inference → risk check → RAG → LLM triage → output

## Project Structure
```
code/
├── agent.py           # Entry point
├── pipeline.py        # Core orchestration
├── retriever.py       # RAG retrieval
├── risk.py            # Escalation rules
├── scraper.py         # One-time corpus scraper
├── corpus_builder.py  # ChromaDB builder
├── prompts.py         # LLM prompts
├── logger.py          # log.txt handler
└── requirements.txt
```
