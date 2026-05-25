# Getting started

## Requirements

- Python 3.10 or newer
- An LLM API key (Gemini or Groq are free)

## Install

```bash
git clone https://github.com/neej4/ScholarScout.git
cd ScholarScout
pip install -r requirements.txt
python preview_server.py
```

Open http://localhost:5050 in your browser.

## First run

The onboarding wizard appears automatically:

1. Pick a provider (Gemini recommended — free, 15 req/min)
2. Paste your API key and test the connection
3. Choose 2-3 research categories

After setup, click **Run** for a full pipeline (fetches papers, analyzes trends, generates ideas — takes 2-5 minutes) or **Quick** for instant ideas from cached papers (~10 seconds).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pip install` fails | Make sure you have Python 3.10+. Try `python --version`. |
| Port 5050 in use | Kill the other process or change port in `preview_server.py` |
| "LLM unreachable" | Check your API key in Settings tab. Test connection. |
| 0 papers fetched | Rate limited. Wait 5 minutes or use cached papers (Quick mode). |
| Truncated ideas | Fixed in v1.5.1 (chunked generation). Update to latest. |
