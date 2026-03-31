# SaaSCostCompare

Prototype for the SaaSCostCompare service—upload SaaS expenses, get AI-powered analysis, and compare with peers.

## Prerequisites

- Python 3.9+
- Node.js & npm
- Redis (for job queue)
- Stripe account (for payments)
- Anthropic API key (for Claude AI)

## Setup

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Stripe and Anthropic keys
```

### 2. Start Redis

```bash
# macOS with Homebrew
brew install redis
redis-server

# or Docker
docker run -d -p 6379:6379 redis:latest
```

### 3. Run API Server

```bash
cd backend
python -m uvicorn main:app --reload
```

API runs on `http://localhost:8000`

### 4. Run Background Worker

In a separate terminal:

```bash
cd backend
python worker.py
```

This processes uploaded reports with AI analysis.

### 5. Frontend

```bash
cd frontend
python3 -m http.server 3000
# or: npx http-server -p 3000
```

Frontend runs on `http://localhost:3000`

## Architecture Overview

- **API** (`main.py`): Handles auth, upload, payment checkout, webhooks
- **Queue** (`queue.py`, `worker.py`): Background processing with RQ
- **AI Analysis** (`ai_analysis.py`): Claude integration for report insights
- **Payment** (`payment.py`): Stripe checkout sessions & webhooks
- **Models** (`models.py`, `database.py`): SQLite DB for users, orgs, reports

## API Endpoints

### Auth
- `POST /register` – Create user account
- `POST /login` – Get JWT token
- `GET /me` – Current user profile

### Organizations
- `POST /orgs` – Create org
- `GET /orgs/{id}` – Get org details

### Reports
- `POST /upload` – Upload SaaS report (enqueues processing)
- `GET /reports/{id}` – Get report metadata
- `GET /reports/{id}/status` – Check status + AI analysis
- `POST /payment/checkout` – Create Stripe session
- `GET /download/{id}` – Download report (after payment)

### Webhooks
- `POST /webhook/stripe` – Stripe payment confirmation

## Workflow

1. User registers + creates organization
2. Uploads SaaS expense file (CSV/JSON)
3. Backend enqueues analysis job
4. Worker processes file with Claude AI
5. Results stored; user prompted to pay
6. After payment, report downloadable

## Frontend

(placeholder)
