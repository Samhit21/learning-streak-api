# Learning Streak API

A backend API to track daily study sessions, focus tags, streaks, and heatmap-style consistency analytics.

## Overview
This project helps users stay consistent with learning goals by logging study sessions and visualizing progress over time.
It supports authentication, tag-based session tracking, streak calculation, and heatmap analytics.

## Tech Stack
- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Uvicorn
- python-jose for JWT auth
- passlib[bcrypt] for password hashing
- Docker + Docker Compose

## Features
- User registration and login with JWT
- Protected endpoints using Bearer token auth
- Create/list focus tags
- Create/list/update/delete study sessions
- Current and longest streak calculation
- Heatmap analytics (minutes per day)
- Swagger docs at /docs

## Project Structure
learning-streak-api/
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env.example
  README.md
  app/
    __init__.py
    main.py
    db.py
    models.py
    schemas.py
    security.py
    deps.py

## Environment Variables
Create .env from .env.example:

DATABASE_URL=postgresql+psycopg2://app:app@db:5432/learning_streak
JWT_SECRET=change-me
JWT_ALG=HS256
ACCESS_TOKEN_MINUTES=60

## Setup and Run
cp .env.example .env
docker compose down -v
docker compose up --build

## URLs
API Docs: http://localhost:8000/docs
OpenAPI JSON: http://localhost:8000/openapi.json
Health Check: http://localhost:8000/health

## Authentication
Register endpoint: POST /auth/register
Login endpoint: POST /auth/login

Register request body:
{
  "email": "you@example.com",
  "password": "strongpass123"
}

Login request body:
{
  "email": "you@example.com",
  "password": "strongpass123"
}

Both return:
{
  "accessToken": "..."
}

Authorize in Swagger:
1. Register or login and copy accessToken
2. Click Authorize in /docs
3. Enter: Bearer <accessToken>

## API Endpoints
Public:
- GET /health
- POST /auth/register
- POST /auth/login

Protected:
- POST /tags
- GET /tags
- POST /sessions
- GET /sessions
- PATCH /sessions/{session_id}
- DELETE /sessions/{session_id}
- GET /streak
- GET /analytics/heatmap?range=90d

## Data Models
users:
- id (uuid, pk)
- email (unique, indexed)
- password_hash
- created_at

tags:
- id (uuid, pk)
- user_id (fk users, indexed)
- name (unique per user)
- color (nullable)
- created_at

sessions:
- id (uuid, pk)
- user_id (fk users, indexed)
- tag_id (fk tags, nullable)
- session_date (date, indexed)
- duration_min (int)
- notes (nullable)
- created_at

## Sample Requests
Create tag body:
{
  "name": "DSA",
  "color": "blue"
}

Create session body:
{
  "tagId": "ce320dea-fb09-4ce7-98d5-cbbd04450424",
  "sessionDate": "2026-02-21",
  "durationMin": 90,
  "notes": "Solved arrays and strings"
}

Streak response example:
{
  "currentStreak": 1,
  "longestStreak": 1
}

Heatmap response example:
{
  "range": "30d",
  "dailyMinutes": [
    { "day": "2026-02-21", "minutes": 90 }
  ]
}

## Validation Rules
- Password minimum length: 6
- durationMin range: 1..1440
- Heatmap range format: Nd (example: 7d, 30d, 90d)
- Allowed heatmap day range: 1..365
- Tag names are unique per user

## Common Issue
If hashing fails due to bcrypt/passlib compatibility, pin this in requirements.txt:
bcrypt==4.0.1

Then rebuild:
docker compose down
docker compose up --build

## Future Improvements
- Add automated tests
- Add refresh tokens and rotation
- Add pagination metadata
- Add export endpoints
- Add CI pipeline
- Deploy API
