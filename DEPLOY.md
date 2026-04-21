# Deployment — Fly.io

This branch adds Docker + Fly.io deployment for the ChessMate skeleton.
SQLite is stored on a persistent volume; Postgres migration is planned for
the Apr 27 – May 3 window.

## One-time setup

1. Install `flyctl`: https://fly.io/docs/hands-on/install-flyctl/
2. `fly auth login`
3. From the project root:
   ```bash
   fly launch --no-deploy --copy-config
   ```
   - When prompted for an app name, pick something globally unique (update
     `app = ...`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`
     in `fly.toml` to match).
   - Decline Postgres and Redis for now.
4. Create the data volume (1 GB, free tier):
   ```bash
   fly volumes create chessmate_data --region fra --size 1
   ```
5. Set the production secret key:
   ```bash
   fly secrets set DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
   ```

## Deploy

```bash
fly deploy
```

Migrations run automatically via the `release_command` in `fly.toml`.

## Create an admin user

```bash
fly ssh console -C "python manage.py createsuperuser"
```

## Environment variables

| Variable                       | Purpose                                        |
|--------------------------------|------------------------------------------------|
| `DJANGO_SECRET_KEY`            | Production secret key (set via `fly secrets`). |
| `DJANGO_DEBUG`                 | `False` in prod.                               |
| `DJANGO_ALLOWED_HOSTS`         | Comma-separated host list.                     |
| `DJANGO_CSRF_TRUSTED_ORIGINS`  | Comma-separated origins (https://...).         |
| `DJANGO_DATABASE_PATH`         | SQLite path (on the volume at `/data`).        |
| `DJANGO_MEDIA_ROOT`            | Media uploads path (on the volume).            |

Local dev requires none of these — sensible defaults keep `runserver` working.
