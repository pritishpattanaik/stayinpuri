# PuriGuide

Puri, Odisha travel guide and local services booking platform.

## Tech Stack

- **Frontend:** Plain HTML + CSS + Vanilla JavaScript
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Infrastructure:** Docker, Nginx

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker (optional)

### Without Docker

1. **Set up PostgreSQL:**
   ```sql
   CREATE DATABASE puriguide;
   CREATE USER puriguide WITH PASSWORD 'puriguide123';
   GRANT ALL PRIVILEGES ON DATABASE puriguide TO puriguide;
   ```

2. **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   python -m app.seed        # seed the database
   uvicorn app.main:app --reload --port 8000
   ```

3. **Frontend:**
   Open `frontend/index.html` in any browser or use Live Server in VS Code.

### With Docker

```bash
docker compose up -d
docker compose exec backend python -m app.seed
```

- Frontend: http://localhost
- Backend API: http://localhost/api/health
- API Docs: http://localhost/docs

## Project Structure

```
puriguide/
├── frontend/          # Static HTML/CSS/JS
├── backend/           # FastAPI Python app
├── nginx/             # Nginx reverse proxy config
├── docker-compose.yml
└── .github/           # CI/CD workflows
```

## Configuration

- **Backend config:** `backend/.env`
- **Frontend config:** `frontend/js/config.js`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/site-config` | Site configuration |
| GET | `/api/properties/` | List all properties |
| GET | `/api/properties/{slug}` | Get property by slug |
| GET | `/api/services/` | List all services |
| POST | `/api/bookings/` | Create booking |
| GET | `/api/bookings/{ref}` | Get booking by ref |
