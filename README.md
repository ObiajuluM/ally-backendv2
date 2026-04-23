# Ally

A Django-based emergency response platform that connects users to first responders. It provides a REST API for discovering nearby responders, real-time live location sharing over WebSockets, Google OAuth sign-in, and an AI assistant powered by Gemini.

## Features

- **First Responder Directory** — Browse and filter responders by type (medical, law enforcement, disaster relief, abuse & violence) and tags
- **Geolocation** — Responder addresses are reverse-geocoded automatically from lat/long coordinates
- **Live Location Sharing** — Real-time WebSocket streams let a publisher broadcast their location to any number of viewers
- **Google Authentication** — Sign in with a Google ID token; JWT access/refresh tokens are issued in return
- **Gemini AI Assistant** — `/api/geminid/` endpoint for AI-powered interactions
- **User Profiles** — Each user has a `MyInformation` record storing personal details and location

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 + Django REST Framework |
| Real-time | Django Channels 4 + Daphne (ASGI) |
| Channel layer | Redis |
| Database | PostgreSQL (production) / SQLite (dev) |
| Auth | Google OAuth 2.0 + JWT (SimpleJWT) |
| Geocoding | geopy (Nominatim) |
| AI | Google Gemini |
| Containerisation | Docker + Docker Compose |
| Static files | WhiteNoise |

## Requirements

- Docker & Docker Compose **or** Python 3.11+ with PostgreSQL and Redis

## Getting Started

### 1. Clone and configure

```bash
git clone <repo-url>
cd ally2
cp .env.example .env   # fill in the values below
```

Required `.env` variables:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

# PostgreSQL (used when DEBUG=False or via Docker)
DB_NAME=db name goes here
DB_USER=username goes here
DB_PASSWORD=your password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id

# Gemini
GEMINI_API_KEY=your-gemini-api-key
```

### 2. Run with Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### 3. Run locally (without Docker)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Database Seeding

```bash
# Default — 10 users, 100 responders
docker compose exec web python manage.py seed

# Custom counts
docker compose exec web python manage.py seed --users 20 --responders 50

# Cluster responders around a specific location
docker compose exec web python manage.py seed --cluster-lat 4.8948 --cluster-lng 6.9719

# Repeatable/deterministic data
docker compose exec web python manage.py seed --seed 42
```

## Create a Superuser

```bash
docker compose exec web python manage.py createsuperuser
```

Admin UI is available at `http://localhost:8000/admin/`.

## Makefile Shortcuts (local dev)

```bash
make serve    # run dev server on 192.168.1.61:8000
make migrate  # makemigrations + migrate
make seed     # seed the database
make flush    # flush the database
```

## API Endpoints

All endpoints are prefixed with `/api/`.

| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| `POST` | `auth/google/` | Exchange a Google ID token for JWT tokens | No |
| `GET/PUT/DELETE` | `user/` | Retrieve or update the authenticated user | Yes |
| `GET/PUT/DELETE` | `my-information/` | Retrieve or update the user's profile | Yes |
| `GET/POST` | `first-responders/` | List or create first responders | Yes |
| `POST` | `geminid/` | Send a prompt to the Gemini AI assistant | Yes |

### WebSocket

```
ws://<host>/ws/live/<user-id>/
```

Connect to subscribe to a user's live location stream. The room owner can publish location updates; all connected clients receive them.

**Publish payload:**

```json
{
  "lat": 4.8948,
  "long": 6.9719,
  "accuracy": 10.0,
  "alt": 50.0,
  "alt_accuracy": 5.0,
  "time": 1714000000000
}
```

## Project Structure

```
ally/           # main Django app (models, views, serializers, consumers)
config/         # Django project settings, root URL conf, ASGI/WSGI
static/         # project static files
manage.py
docker-compose.yml
Dockerfile
requirements.txt
```

