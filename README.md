# Eschen Chess Club

A web application for the Eschen Chess Club (Liechtenstein) built with Django. The system manages club members, tracks matches, calculates ELO ratings, and publishes announcements.

## Tech Stack 

| Layer        | Technology                             |
|--------------|----------------------------------------|
| Backend      | Python 3, Django 5                     |
| Frontend     | Bootstrap 5, Chart.js, Bootstrap Icons |
| Database     | SQLite (development)                   |
| Forms        | django-crispy-forms + crispy-bootstrap5|
| Images       | Pillow                                 |
| Static Files | WhiteNoise                             |

## Development Plan

The project is built incrementally across the following phases. Each phase is a separate branch merged into `develop` via pull request, and then into `main` for release.

### Phase 1 — Project Setup & Skeleton

> Branch: `main` (current state)

- [x] Create Django project (`chess_club`)
- [x] Create `club` app
- [x] Configure `settings.py` (database, static files, media, templates)
- [x] Set up `requirements.txt` with core dependencies
- [x] Add `.gitignore`
- [x] Initialize Git repository with `main` and `develop` branches

### Phase 2 — Data Models & Migrations

> Branch: `feature/models`

- [x] Define `Member` model (linked to Django `User`, ELO rating, avatar, win/loss/draw stats)
- [x] Define `Match` model (white player, black player, status, result, venue, scheduled date)
- [x] Define `EloHistory` model (tracks rating changes per match)
- [x] Define `Announcement` model (title, body, published date, author)
- [x] Generate and apply migrations
- [x] Register models in the admin site (basic)

### Phase 3 — ELO Rating Engine

> Branch: `feature/elo-engine`

- [x] Implement expectation + adaptive K-factor (`club/elo_engine.py`)
- [x] Integrate rating updates into match completion (`Match.save` + `club/services/match_elo.py`)
- [x] Create `EloHistory` rows automatically when a completed match applies ELO
- [x] Admin action + `python manage.py recalculate_club_elo` rebuild from history

### Phase 4 — Admin Panel Configuration

> Branch: `feature/admin-panel`

- [x] Customize `MemberAdmin` (list display, search)
- [x] Customize `MatchAdmin` (list display, filters, recalculate action)
- [x] Customize `EloHistoryAdmin`, `AnnouncementAdmin`, and related registrations
- [x] Optional staff TOTP enrolment (`django-otp`; see About page note)

### Phase 5 — Views & URL Routing

> Branch: `feature/views`

- [x] Home, leaderboard (DB-sorted win rate), matches, match detail
- [x] Member profiles, about + contact
- [x] `club/urls.py` + inclusion in project `urls.py`

### Phase 6 — Templates & Frontend

> Branch: `feature/templates`

- [x] Base layout (`base.html`), home, leaderboard, matches, member pages, crispy forms where needed
- [x] `static/css/style.css`, `static/js/app.js`; dashboard retains Chart.js for pipeline metrics

### Phase 7 — Sample Data & Polish

> Branch: `feature/sample-data`

- [x] `python manage.py create_sample_data` (`--purge-seed` resets bundled sample members/announcements, `--purge-demo` is a deprecated alias, `--reset-club-stats` wipes OTB tables)
- [x] Optional `fixtures/` omitted in favour of the management command
- [x] WhiteNoise static storage, `python-decouple`, `.env.example`
- [x] Operational README updates (deployment QA remains environment-specific)

### Security hygiene

Never commit `.env`, API tokens, or ad-hoc key files (`lichess_*`, etc.). For `DEBUG=False`, set a production `SECRET_KEY` and populate `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.

## Git Workflow

```
main            ← stable releases
  └── develop   ← integration branch
        ├── feature/models
        ├── feature/elo-engine
        ├── feature/admin-panel
        ├── feature/views
        ├── feature/templates
        └── feature/sample-data
```

Each feature branch is created from `develop`, worked on, and merged back into `develop` via pull request. When a set of features is stable, `develop` is merged into `main`.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Amani-ojo/-Chess-Club.git
   cd -Chess-Club
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (recommended)**  
   Copy `.env.example` to `.env` and set `SECRET_KEY` plus any Postgres or pipeline variables you need.

5. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. Open your browser and visit `http://127.0.0.1:8000/`

## AI Pipeline Integration

The project now includes a full AI analysis pipeline integrated into the same Django app:

- Lichess import tasks
- Stockfish game analysis
- Move-by-move evaluations
- Player insight generation

### Environment Variables (optional but recommended)

Set these before running:

- `LICHESS_API_TOKEN` for authenticated Lichess API usage
- `STOCKFISH_PATH` to your local Stockfish executable (defaults to the bundled binary path)
- `CELERY_BROKER_URL` (default `redis://localhost:6379/0`)

### Running Locally with Pipeline

1. Start Redis.
2. Run Django:
   - `python manage.py migrate`
   - `python manage.py runserver`
3. In another terminal, run Celery worker:
   - `celery -A chess_club worker -l info`

Use `/admin/` to add members and games, then trigger task functions from the shell or admin workflows.

### Codespaces Bootstrap (One Command)

For GitHub Codespaces, you can bootstrap all dependencies with:

```bash
chmod +x bootstrap_codespace.sh
./bootstrap_codespace.sh
```

After bootstrap, you can start all required services with one command:

```bash
chmod +x start_all_services.sh
./start_all_services.sh
```

This starts Redis, launches Celery in the background (logs in `.logs/celery.log`), and runs Django in the foreground.

Then start services in separate terminals:

```bash
source .venv/bin/activate
export STOCKFISH_PATH=/usr/games/stockfish
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
python manage.py runserver 0.0.0.0:8000
```

```bash
source .venv/bin/activate
export STOCKFISH_PATH=/usr/games/stockfish
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
celery -A chess_club worker -l info
```

## Contributors

- Amani Ojo

## License

This project is for educational purposes as part of an ISD course.
