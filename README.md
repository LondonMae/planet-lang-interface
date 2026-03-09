# PLanet Composer

A web interface for designing within-subjects, between-subjects, and mixed HCI experiments using the [PLanet DSL](https://pypi.org/project/planet-dsl/).

## Requirements

- Python 3.9+
- No other dependencies needed — the setup script handles everything

## Installation & Usage

```bash
git clone <repo-url>
cd experiment-interface
./run.sh
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

On first run, `run.sh` creates a `.venv` virtual environment and installs all dependencies automatically.

## Features

- **Variables** — define experiment variables and their conditions
- **Designs** — assign variables as within- or between-subjects; set counterbalancing, ordering, trial counts, and plan limits
- **Composition** — nest or cross multiple designs
- **Analysis** — view main effects, interaction effects, time-varying effects, and within-subjects comparisons
- **Run** — generate counterbalancing plans and participant assignments
- **Export** — download results as CSV or LaTeX

## Project Structure

```
app.py          # FastAPI backend — generates and executes PLanet code
index.html      # Single-page frontend (vanilla JS, no build step)
requirements.txt
run.sh          # Start script (sets up venv on first run)
```

## Dependencies

Managed automatically by `run.sh`:

- [`planet-dsl`](https://pypi.org/project/planet-dsl/) — experimental design DSL
- `fastapi` + `uvicorn` — web server
- `pandas` — assignment formatting and CSV export
