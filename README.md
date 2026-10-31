# CloudDesk

> An AI-powered support desk built with FastAPI, LangGraph, ChromaDB, and Streamlit.

**Status**: In Development (project scaffold) | **Version**: 0.1.0

---

## Overview

CloudDesk is the next project in this portfolio. At this stage the repository holds the
project scaffold only: a reproducible Python environment, pinned dependencies, build and
lint/test configuration, and a CLI entry point. Application features have not been built yet.

This README will be expanded with architecture, features, and test results as the
implementation lands.

## Technology Stack

| Area | Choice |
|---|---|
| Language | Python 3.12 |
| API backend | FastAPI, Uvicorn, Pydantic |
| Agent orchestration | LangGraph, LangChain (`langchain-openai`) |
| Vector store | ChromaDB |
| UI | Streamlit |
| Configuration | `python-dotenv` |
| Packaging | [uv](https://docs.astral.sh/uv/), Hatchling build backend |
| Dev tooling | pytest, Ruff |

## Getting Started

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 (uv installs it if missing).

```bash
cd 05_CloudDesk
uv sync                 # create .venv and install locked dependencies
uv run clouddesk        # run the CLI entry point (currently prints a greeting)
```

Activate the environment instead of prefixing commands with `uv run`:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### Configuration

`langchain-openai` reads `OPENAI_API_KEY` from the environment. Put it in a local `.env`
file, which is git-ignored. Never commit real keys.

## Development

```bash
uv run ruff check .     # lint
uv run pytest           # tests (none written yet)
```

## Project Structure

```
05_CloudDesk/
├── main.py             # CLI entry point (clouddesk = "main:main")
├── pyproject.toml      # metadata, dependencies, build and tool config
├── uv.lock             # locked dependency versions
├── .python-version     # pinned interpreter (3.12)
└── .gitignore
```

## Roadmap

- [ ] Define the problem statement and architecture
- [ ] Backend API (FastAPI)
- [ ] Agent workflow (LangGraph) with retrieval over ChromaDB
- [ ] Streamlit UI
- [ ] Automated tests and evaluation
- [ ] Deployment

## Author

Built by **Mahesh Kumar**, Founder & CEO of **SaffronyxAI.in**.
