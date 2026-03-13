# Eschen Chess Club

A web application for the Eschen Chess Club (Liechtenstein) built with Django. It manages club members, tracks matches, calculates ELO ratings, and publishes announcements.

## Features

- **Member Profiles** — Each member has a profile with avatar, ELO rating, win/loss/draw record, and an interactive ELO history chart.
- **ELO Rating System** — Automatic ELO calculation using the standard FIDE formula with adaptive K-factors (K=40 for new players, K=10 for 2400+ rated players, K=20 otherwise).
- **Match Management** — Schedule matches, record results (white wins, black wins, draw), and browse upcoming fixtures or past results.
- **Leaderboard** — Rank members by ELO rating or win percentage with sortable columns.
- **Announcements** — Club news published by administrators and displayed on the home page.
- **Contact Form** — Visitors can reach out to the club through the About page.
- **Admin Panel** — Full Django Admin interface for managing members, matches, announcements, and a one-click ELO recalculation action.
- **Responsive Design** — Bootstrap 5 with custom styling, mobile-friendly navigation, and clean typography.

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3, Django 5                  |
| Frontend    | Bootstrap 5, Chart.js, Bootstrap Icons |
| Database    | SQLite (development)                |
| Forms       | django-crispy-forms + crispy-bootstrap5 |
| Images      | Pillow                              |
| Static Files| WhiteNoise                          |

## Project Structure

```
chess_club/
├── chess_club/          # Django project settings, URLs, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── club/                # Main application
│   ├── models.py        # Member, Match, EloHistory, Announcement
│   ├── views.py         # Home, Leaderboard, Matches, Profile, About
│   ├── admin.py         # Admin config with ELO recalculation action
│   ├── forms.py         # Contact form
│   ├── utils.py         # ELO calculation (FIDE formula)
│   ├── urls.py          # App URL routes
│   ├── templates/club/  # HTML templates
│   └── static/club/     # CSS and JavaScript
├── fixtures/            # Sample data fixtures
├── media/               # User-uploaded files (avatars)
├── create_sample_data.py# Script to populate the database with sample data
├── manage.py
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:Amani-ojo/-Chess-Club.git
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

4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** (for the admin panel)
   ```bash
   python manage.py createsuperuser
   ```

6. **Load sample data** (optional)
   ```bash
   python create_sample_data.py
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. Open your browser and visit `http://127.0.0.1:8000/`

## Pages

| URL              | Page            | Description                                  |
|------------------|-----------------|----------------------------------------------|
| `/`              | Home            | Welcome banner, top 5 players, upcoming matches, announcements |
| `/leaderboard/`  | Leaderboard     | All members ranked by ELO or win %           |
| `/matches/`      | Matches         | Upcoming fixtures and completed results      |
| `/matches/<id>/` | Match Detail    | Full details of a single match               |
| `/members/<id>/` | Member Profile  | Stats, ELO chart, and recent match history   |
| `/about/`        | About           | Club information and contact form            |
| `/admin/`        | Admin Panel     | Django admin for managing all data           |

## ELO Rating Formula

The application uses the standard FIDE ELO calculation:

```
Expected Score:  E = 1 / (1 + 10^((Rb - Ra) / 400))
New Rating:      Ra_new = Ra + K * (S - E)
```

Where `S` is the actual score (1 for win, 0.5 for draw, 0 for loss) and `K` is the adaptive K-factor.

## Contributors

- Amani Ojo

## License

This project is for educational purposes as part of an ISD course.
