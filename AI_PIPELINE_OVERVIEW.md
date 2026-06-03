# ChessMate — AI Pipeline: Features, Explanation & Integration Guide

**Author:** Patrick Gupta  
**Branch:** `feature/ai-pipeline`  
**Date:** 4 April 2026  
**Test status:** 27 / 27 passing

---

## 1. What Was Built

The `ai_pipeline` is a self-contained Django app that sits alongside the existing `club` app. It adds three capabilities to ChessMate: automated game import from Lichess, AI-powered move-by-move analysis using Stockfish, and personalised coaching insights for every member.

---

## 2. Architecture Overview

```
Member triggers fetch
        │
        ▼
┌─────────────────────────┐
│  fetch_lichess_games_task│  ← Celery background task
│  (lichess_api.py)        │
└────────────┬────────────┘
             │  saves Game rows, chains ↓
             ▼
┌─────────────────────────┐
│  analyse_game_task       │  ← Celery background task
│  (stockfish_analysis.py) │
└────────────┬────────────┘
             │  saves GameAnalysis + MoveEvaluation rows, chains ↓
             ▼
┌─────────────────────────┐
│  generate_insights_task  │  ← Celery background task
│  (insight_aggregator.py) │
└────────────┬────────────┘
             │
             ▼
     PlayerInsight rows
     visible at /ai/player/<id>/insights/
```

---

## 3. Features

### 3.1 Data Models (`models.py`)

| Model | What it stores |
|---|---|
| `Game` | A chess game fetched from Lichess — PGN, both players, result, time control |
| `GameAnalysis` | Stockfish's verdict on a whole game — avg centipawn loss, blunder / mistake / inaccuracy counts, status (`pending → processing → completed / failed`) |
| `MoveEvaluation` | One row **per move** — move played, best move available, centipawn loss, classification label |
| `PlayerInsight` | Coaching recommendation for a member — category, title, description, suggested improvement actions |

---

### 3.2 Services (`services/`)

#### `stockfish_analysis.py` — Chess Engine Wrapper

- Opens a PGN string and walks every move using `python-chess`
- Before each move: asks Stockfish for the best move and the position score
- After the move is pushed: scores the new position
- Calculates **centipawn loss** — how much worse the played move was compared to the best available move
- Classifies every move:

  | Label | Centipawn loss |
  |---|---|
  | Best | 0 |
  | Excellent | ≤ 10 |
  | Good | ≤ 25 |
  | Inaccuracy | ≤ 50 |
  | Mistake | ≤ 100 |
  | Blunder | > 100 |

- Returns aggregated stats (avg CPL per side, blunder / mistake / inaccuracy counts) plus a full per-move list

#### `lichess_api.py` — Lichess API Client

- `fetch_recent_games(username)` — pulls up to 20 games as NDJSON from `lichess.org/api/games/user/{username}`
- `fetch_game_pgn(game_id)` — fetches the raw PGN for a single game by ID
- `create_challenge(username)` — sends a game challenge to another Lichess user and returns a shareable URL
- All requests authenticated via OAuth Bearer token (`settings.LICHESS_API_TOKEN`)

#### `insight_aggregator.py` — Coaching Engine

- Queries all completed analyses for a member
- Splits moves into game phases: opening (≤ move 15), middlegame (≤ move 35), endgame (> move 35)
- Calculates avg CPL and blunder rate per phase
- Triggers a `PlayerInsight` when avg CPL > 60 or blunder rate > 1.5 per game in a phase
- Also detects recurring blunders across all phases → tactical awareness insight

---

### 3.3 Background Tasks (`tasks.py`)

Three Celery tasks run **asynchronously** — the web request returns instantly, heavy work happens in the background.

| Task | What it does | Retries |
|---|---|---|
| `fetch_lichess_games_task` | Calls Lichess API → saves new `Game` rows → queues analysis | 3× with 60s delay |
| `analyse_game_task` | Runs Stockfish on the PGN → writes `GameAnalysis` + `MoveEvaluation` rows | 3× with 60s delay |
| `generate_insights_task` | Reads all completed analyses → produces `PlayerInsight` rows | 2× with 30s delay |

---

### 3.4 Views & URLs

| URL | View | What it shows |
|---|---|---|
| `/ai/game/<id>/embed/` | `game_embed` | Lichess iframe for replaying the game |
| `/ai/game/<id>/analysis/` | `game_analysis_view` | Full move-by-move Stockfish breakdown |
| `/ai/player/<id>/insights/` | `player_insights_view` | Coaching recommendations for a member |

---

## 4. Test Coverage

| Suite | Tests | Type | Result |
|---|---|---|---|
| `TestClassifyMove` | 8 | Unit — centipawn thresholds | All passed |
| `TestAnalyseGame` | 5 | Unit — mocked Stockfish | All passed |
| `TestLichessClient` | 5 | Unit — mocked HTTP | All passed |
| `TestPhaseHelper` | 3 | Unit — phase boundaries | All passed |
| Integration suite | 5 | Real Stockfish 17.1, real DB | All passed |
| **Total** | **27** | | **27 / 27 · 100%** |

Run all tests:

```powershell
cd patrick_ai_pipeline
python -m pytest -v -s
```

The browser opens `test_report.html` automatically when the run completes.

---

## 5. How to Integrate into the Main Project

### Step 1 — Copy files into the repo

```
chess_club/                    ← repo root
├── ai_pipeline/               ← copy this entire folder here
├── chess_club/
│   ├── celery.py              ← copy from celery_config/celery.py
│   └── __init__.py            ← edit (see Step 4)
```

### Step 2 — Edit `chess_club/settings.py`

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'ai_pipeline',
]

# Celery
CELERY_BROKER_URL      = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND  = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT  = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE        = 'UTC'

# Lichess
LICHESS_API_TOKEN    = os.environ['LICHESS_API_TOKEN']   # never commit this
LICHESS_API_BASE_URL = 'https://lichess.org/api'

# Stockfish
STOCKFISH_PATH    = '/usr/local/bin/stockfish'   # adjust per server OS
STOCKFISH_DEPTH   = 20
STOCKFISH_THREADS = 2
STOCKFISH_HASH_MB = 256
```

### Step 3 — Edit `chess_club/urls.py`

```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns ...
    path('ai/', include('ai_pipeline.urls')),
]
```

### Step 4 — Edit `chess_club/__init__.py`

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### Step 5 — Run migrations

```bash
python manage.py makemigrations ai_pipeline
python manage.py migrate
```

### Step 6 — Start services

```bash
# Terminal 1 — Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 2 — Celery worker
celery -A chess_club worker --loglevel=info

# Terminal 3 — Django dev server
python manage.py runserver
```

### Step 7 — Trigger the pipeline for a member

```python
# From Django shell or an admin button:
from ai_pipeline.tasks import fetch_lichess_games_task

fetch_lichess_games_task.delay('their_lichess_username', member.pk)
```

That one call fetches their recent games from Lichess, analyses every game with Stockfish, and generates personalised coaching insights — all in the background with no further action needed.

---

## 6. Dependencies to Add to `requirements.txt`

```
celery>=5.3
redis>=5.0
requests>=2.31
python-chess>=1.999
stockfish>=3.28
```

---

## 7. Notes

- The `ai_pipeline` app references `club.models.Member` via `ForeignKey` only — it never modifies any `club` models.
- Do not commit `LICHESS_API_TOKEN` to git. Use environment variables or a `.env` file with `python-decouple` or `django-environ`.
- The Stockfish binary (`bin/stockfish_extracted/`) must be present on the server. The Windows AVX2 build is included for local development; replace with the Linux build for deployment.
