# SaaSCostCompare — Architecture Document

**Version:** 1.0
**Date:** March 2026
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Technology Components](#3-technology-components)
4. [Data Flow — Core User Journey](#4-data-flow--core-user-journey)
5. [Database Design](#5-database-design)
6. [API Design](#6-api-design)
7. [Security Architecture](#7-security-architecture)
8. [Scalability Design](#8-scalability-design)
9. [Production Readiness](#9-production-readiness)
10. [Environment Strategy](#10-environment-strategy)

---

## 1. Overview

SaaSCostCompare is a SaaS analytics platform that enables organisations to upload their SaaS vendor spend data, receive AI-powered cost analysis, benchmark their spend against peer organisations, and download a professional PDF report.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **CSV Ingestion** | Upload vendor spend data in a structured CSV format |
| **AI Analysis** | Automated cost insights powered by Claude AI (Anthropic) |
| **Peer Benchmarking** | Compare spend against similar organisations by revenue and size |
| **Payment Gate** | Stripe-powered checkout to unlock full reports |
| **PDF Reports** | Professional, branded PDF output for stakeholder distribution |
| **Multi-Tenant** | Organisation-scoped data isolation with user authentication |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            USER BROWSER                                 │
│                    React 18 + Vite + Tailwind CSS                       │
│                         (Port 3000 / HTTPS)                             │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ HTTPS REST (JWT Bearer Token)
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BACKEND API                                     │
│                    FastAPI (Python) — Uvicorn                           │
│                         (Port 8000 / HTTPS)                             │
│                                                                         │
│   /register  /login  /upload  /reports  /payment  /download  /webhook  │
└────────┬──────────────────┬───────────────────────┬─────────────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌────────────────┐  ┌───────────────┐   ┌──────────────────────┐
│  PostgreSQL    │  │     Redis     │   │   External Services  │
│  (Database)   │  │  (Job Queue)  │   │                      │
│               │  │               │   │  ┌────────────────┐  │
│  - users      │  │  report jobs  │   │  │ Anthropic API  │  │
│  - orgs       │  │               │   │  │ (Claude AI)    │  │
│  - reports    │  └───────┬───────┘   │  └────────────────┘  │
│  - benchmarks │          │           │                      │
└────────────────┘          ▼           │  ┌────────────────┐  │
                   ┌────────────────┐   │  │ Stripe API     │  │
                   │  RQ Worker     │───┘  │ (Payments)     │  │
                   │  (Background   │      └────────────────┘  │
                   │   Processor)   │      └──────────────────────┘
                   └────────────────┘
```

---

## 3. Technology Components

### 3.1 Frontend — React 18 + Vite

**What it is:** A component-based JavaScript UI framework served via Vite's optimised build tooling.

**Why it was chosen:**
- React's component model maps well to the dashboard-heavy UI (reports table, upload wizard, benchmark cards)
- Vite provides extremely fast hot-module reload in development and optimised production bundles
- Large ecosystem — any UI library, chart library, or utility integrates easily
- Widely known — easy to hire for or find help online

**Key libraries:**

| Library | Version | Purpose |
|---------|---------|---------|
| React | 18.2 | UI rendering and state |
| React Router | v6 | Client-side page routing |
| Axios | latest | HTTP client with interceptors |
| Tailwind CSS | v3 | Utility-first styling, no custom CSS overhead |

**How it connects:** Axios sends REST API calls to the FastAPI backend. A request interceptor automatically attaches the JWT token from `localStorage` to every request header, so no manual token management is needed per-call.

---

### 3.2 Backend API — FastAPI (Python)

**What it is:** A modern Python web framework for building REST APIs, running on Uvicorn (async ASGI server).

**Why it was chosen:**
- **Performance:** FastAPI is one of the fastest Python frameworks available — benchmarks comparably to NodeJS
- **Auto-generated docs:** Swagger UI is built-in at `/docs`, making API testing and sharing with future developers effortless
- **Type safety:** Python type hints + Pydantic models validate all incoming request data automatically, reducing bugs
- **Async support:** Non-blocking I/O for database and external API calls
- **Python ecosystem:** Access to the best AI, data, and cloud libraries available in any language

**Key responsibilities:**
- User registration, login, and JWT token issuance
- CSV upload, validation, and job enqueueing
- Report status tracking and retrieval
- Stripe payment session creation and webhook handling
- PDF report generation and download
- Benchmark peer matching logic

---

### 3.3 Database — PostgreSQL 16

**What it is:** The world's most advanced open-source relational database.

**Why it was chosen:**
- **Reliability:** ACID-compliant transactions ensure payment and report status updates are consistent and never partially saved
- **JSON support:** PostgreSQL's `JSONB` column type stores Claude AI analysis results as structured JSON without needing a separate document store
- **Multi-tenancy ready:** Foreign key relationships enforce that each organisation only accesses its own reports
- **Scalability:** Handles millions of rows; read replicas can be added as traffic grows
- **Managed hosting:** Available as a managed service on Railway, Supabase, AWS RDS, and others — no DBA required

**Why not SQLite (used in early dev):**
SQLite is a file-based database — fine for local development but not suitable for production because it cannot handle concurrent writes from multiple API workers or Docker containers.

---

### 3.4 ORM — SQLAlchemy

**What it is:** Python's most widely used Object-Relational Mapper (ORM).

**Why it was chosen:**
- Write Python classes instead of raw SQL — less error-prone and more readable
- Database migrations are manageable via Alembic (SQLAlchemy's migration tool) when schema changes are needed
- `DATABASE_URL` environment variable means switching from SQLite (dev) to PostgreSQL (prod) requires zero code changes
- Dependency injection (`get_db()`) cleanly manages database session lifecycle per API request

---

### 3.5 Background Job Queue — Redis + RQ (Redis Queue)

**What it is:** Redis is an in-memory data store used here as a job broker. RQ (Redis Queue) is a lightweight Python library that pushes jobs into Redis and processes them in separate worker processes.

**Why it was chosen:**
- **Non-blocking uploads:** AI analysis via the Claude API can take 10–30 seconds. Without a queue, the HTTP request would time out or leave the user waiting. With RQ, the upload endpoint returns immediately (< 1 second) and processing happens asynchronously in the background
- **Resilience:** If the worker crashes mid-job, the job remains in Redis and can be retried
- **Worker scaling:** You can run multiple worker processes in parallel to process more reports simultaneously
- **Lightweight:** RQ requires minimal configuration vs heavier alternatives like Celery

**Fallback design:** If Redis is unavailable, the system automatically falls back to Python background threads. This means the application continues to function even without Redis — just with reduced resilience.

---

### 3.6 AI Analysis — Anthropic Claude API (claude-3-5-sonnet-20241022)

**What it is:** Anthropic's large language model, accessed via API, used to generate cost insights and benchmark reports.

**Why it was chosen:**
- **Analytical reasoning:** Claude excels at interpreting structured financial data (CSV rows of vendor spend) and producing actionable recommendations
- **Long context window:** Can process entire SaaS spend datasets and peer comparison data in a single prompt
- **Consistent output format:** Produces structured markdown reports (Executive Summary, Recommendations, etc.) reliably
- **Safety:** Anthropic's safety focus reduces risk of hallucinated financial advice in sensitive business reports

**Two AI use cases in this system:**

| Use Case | Prompt Input | Output |
|----------|-------------|--------|
| **Cost Analysis** | Organisation's CSV data + org profile | Insights on spend anomalies, contract risks, top SKUs, recommendations |
| **Benchmark Report** | Target org data + peer org data | Comparative analysis, percentile ranking, spend per employee, % of revenue |

---

### 3.7 Payment Processing — Stripe

**What it is:** The industry-standard payment platform for SaaS businesses.

**Why it was chosen:**
- **No PCI compliance burden:** Card details never touch the server — Stripe hosts the checkout page
- **Webhook-driven:** Stripe sends a signed event to `/webhook/stripe` when payment completes, keeping the system decoupled from the payment flow
- **Test/Live mode:** Stripe provides separate test keys and a card simulator, making it safe to test payments without real money
- **Trusted by users:** Stripe's checkout UX is familiar to business buyers, reducing drop-off

**Payment flow:** User clicks Pay → Stripe-hosted checkout → User pays → Stripe webhooks the server → Report unlocked. The server never sees card numbers.

---

### 3.8 PDF Generation — ReportLab

**What it is:** A Python library for programmatic PDF creation.

**Why it was chosen:**
- Generates professional, branded PDFs entirely server-side — no headless browser required
- Full control over layout, colours (navy/blue/gold scheme), tables, and pagination
- PDF is generated on-demand at download time, not stored — saves disk space
- Outputs a file the user can share with their CFO or procurement team without needing a login

---

### 3.9 Authentication — JWT (JSON Web Tokens)

**What it is:** A stateless token-based authentication standard.

**Why it was chosen:**
- **Stateless:** The server does not need to store session data in the database — every token is self-contained and cryptographically signed
- **Horizontally scalable:** Any backend instance can verify any token — no sticky sessions or shared session store needed
- **Standard:** Works with any future mobile app, third-party integration, or API consumer without changes

**Implementation:** Tokens are signed with `SECRET_KEY` using HS256 algorithm and expire after 24 hours. The `verify_token()` dependency is injected into any protected route.

---

### 3.10 Containerisation — Docker + Docker Compose

**What it is:** Docker packages the application into portable containers. Docker Compose orchestrates multiple containers together.

**Why it was chosen:**
- **Consistency:** The app runs identically on any machine — no "works on my laptop" issues
- **Isolation:** Each service (backend, worker, postgres, redis) runs in its own container with no dependency conflicts
- **Deployment simplicity:** One command (`docker-compose up`) starts the entire stack
- **Cloud ready:** Docker images deploy to any cloud provider — Railway, Fly.io, AWS ECS, Google Cloud Run

---

## 4. Data Flow — Core User Journey

```
STEP 1 — REGISTER & LOGIN
  User → POST /register → bcrypt password hash → store in PostgreSQL
  User → POST /login → verify hash → issue JWT → store in localStorage

STEP 2 — UPLOAD CSV
  User selects category + uploads file
  → POST /upload
  → Backend validates CSV columns
  → Saves file to /uploads/{UUID}_{filename}
  → Creates Report record (status: "uploaded")
  → Enqueues job in Redis
  → Returns immediately to user (< 1 second)

STEP 3 — BACKGROUND AI ANALYSIS
  RQ Worker picks up job from Redis
  → Reads CSV file
  → Fetches org profile (revenue, size)
  → Sends data to Claude API
  → Claude returns cost analysis (markdown)
  → Saves result to report.comparison_result (JSON)
  → Updates report status: "completed"

STEP 4 — FRONTEND POLLING
  Frontend polls GET /reports/{id}/status every few seconds
  → When status = "completed", shows "Pay to Unlock" button

STEP 5 — PAYMENT
  User clicks Pay
  → POST /payment/checkout → Stripe creates hosted checkout session
  → User redirected to Stripe checkout page
  → User pays with card (Stripe handles all card data)
  → Stripe sends webhook: POST /webhook/stripe
  → Backend verifies Stripe signature
  → Updates report.payment_status = "completed"
  → User redirected back to dashboard

STEP 6 — BENCHMARK GENERATION
  User clicks Generate Benchmark
  → POST /reports/{id}/benchmark
  → Backend finds peer orgs (similar revenue: 0.4x–2.5x, similar size: 0.4x–2.5x)
  → Sends target + peer data to Claude API
  → Claude generates comparative benchmark report (markdown)
  → Stored in BenchmarkReport table

STEP 7 — DOWNLOAD PDF REPORT
  User clicks Download Full Report
  → GET /download/{id}/full-report
  → Backend verifies payment_status = "completed"
  → ReportLab generates multi-page PDF on the fly:
       Cover Page → Key Metrics → Benchmark Analysis → AI Insights → Disclaimer
  → Browser downloads PDF
```

---

## 5. Database Design

### Entity Relationship

```
Organization (1) ──── (many) User
Organization (1) ──── (many) Report
User          (1) ──── (many) Report
Report        (1) ──── (0..1) BenchmarkReport
```

### Tables

**organizations**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| name | String | Company name |
| domain | String | Email domain |
| revenue | Float | Annual revenue (USD) — used for peer matching |
| size | Integer | Number of employees — used for peer matching |

**users**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| email | String (unique) | Login identifier |
| hashed_password | String | bcrypt hash — plain password never stored |
| full_name | String | Display name |
| org_id | FK → organizations | Organisation membership |

**reports**
| Column | Type | Description |
|--------|------|-------------|
| id | String (UUID) | Unique report identifier |
| org_id | FK → organizations | Owner organisation |
| owner_id | FK → users | Uploading user |
| filename | String | Original uploaded filename |
| file_path | String | Server path to CSV file |
| category | String | Vendor category (AWS / Microsoft / Google etc.) |
| status | String | uploaded → processing → completed / failed |
| comparison_result | JSON | Claude AI analysis output |
| payment_status | String | pending → completed |
| created_at | DateTime | Upload timestamp |

**benchmark_reports**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| report_id | FK → reports (unique) | One benchmark per report |
| result | JSON | Claude benchmark markdown report |
| peer_count | Integer | Number of peer organisations compared |
| created_at | DateTime | Generation timestamp |

---

## 6. API Design

The API follows REST conventions. All protected routes require `Authorization: Bearer {JWT}` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | No | Create user account |
| POST | `/login` | No | Login, returns JWT |
| GET | `/me` | Yes | Current user profile |
| POST | `/orgs` | Yes | Create organisation |
| GET | `/orgs/{id}` | Yes | Get organisation details |
| POST | `/upload` | Yes | Upload CSV, enqueue analysis |
| GET | `/reports` | Yes | List all reports for org |
| GET | `/reports/{id}` | Yes | Get single report |
| GET | `/reports/{id}/status` | Yes | Poll report processing status |
| POST | `/reports/{id}/benchmark` | Yes | Generate benchmark report |
| GET | `/reports/{id}/benchmark` | Yes | Get benchmark results |
| POST | `/payment/checkout` | Yes | Create Stripe payment session |
| POST | `/webhook/stripe` | No* | Stripe webhook (Stripe-signed) |
| GET | `/download/{id}` | Yes | Download raw CSV analysis |
| GET | `/download/{id}/full-report` | Yes | Download full PDF report |
| GET | `/health` | No | Health check |

*Stripe webhooks are verified by signature, not JWT.

**Interactive API docs available at:** `http://localhost:8000/docs` (development)

---

## 7. Security Architecture

| Layer | Mechanism | Detail |
|-------|-----------|--------|
| **Authentication** | JWT (HS256) | 24-hour expiry, signed with `SECRET_KEY` |
| **Passwords** | bcrypt | Industry-standard hashing, salted automatically |
| **Payment data** | Stripe-hosted | Card details never touch the application server |
| **Webhook integrity** | Stripe signature | `STRIPE_WEBHOOK_SECRET` verifies every incoming webhook |
| **Data isolation** | Org-scoped queries | Every DB query filters by `org_id` — users cannot access other organisations' data |
| **Secrets management** | Environment variables | No secrets in source code; `.env` files excluded from git |
| **CORS** | FastAPI CORS middleware | Only `ALLOWED_ORIGINS` can make cross-origin requests |
| **File validation** | Column whitelist | CSV uploads validated for required columns before processing |

---

## 8. Scalability Design

The system is designed to scale at each layer independently.

### 8.1 Stateless API (Horizontal Scaling)

Because JWT authentication is stateless (no server-side sessions), multiple API server instances can run behind a load balancer with no coordination required. Each instance reads the same database — no sticky sessions needed.

```
Load Balancer
    ├── Backend Instance 1 (Docker)
    ├── Backend Instance 2 (Docker)
    └── Backend Instance 3 (Docker)
         └── All read/write same PostgreSQL
```

### 8.2 Worker Scaling (Queue-Based)

AI analysis is decoupled from the API via Redis Queue. To handle more reports concurrently, simply run more worker containers — each will pull jobs from the same Redis queue independently.

```
Redis Queue (shared job broker)
    ├── Worker 1 — processing report A
    ├── Worker 2 — processing report B
    └── Worker 3 — processing report C
```

### 8.3 Database Scaling

PostgreSQL scales via:
- **Vertical scaling:** Increase CPU/RAM on the database server (fastest for most traffic levels)
- **Read replicas:** Route read-heavy queries (list reports, get benchmark) to replicas, writes to primary
- **Connection pooling:** Add PgBouncer in front of PostgreSQL to handle thousands of short-lived connections

### 8.4 File Storage Scaling

Current: Files stored in a Docker volume (`/uploads`).
At scale: Replace the volume mount with S3 (AWS) or GCS (Google) object storage. Only the file save/read paths in `main.py` and `ai_analysis.py` need updating — the rest of the system is unaffected.

### 8.5 AI Cost Scaling

Claude API calls are the primary cost driver. At scale:
- Add rate limiting per organisation to prevent runaway API spend
- Cache benchmark results — if two orgs in the same peer group both run benchmarks, the peer data is already available
- Queue priority levels — paid users get faster processing

### 8.6 Resilience Patterns Already in Place

| Pattern | Implementation |
|---------|---------------|
| **Circuit breaker** | `_try_enqueue()` falls back from Redis to threads if queue is unavailable |
| **Health checks** | `/health` endpoint + Docker Compose health checks on Postgres and Redis |
| **Retry-safe webhooks** | Stripe retries webhooks; system handles duplicate `checkout.session.completed` events gracefully |
| **Graceful failure** | Failed AI jobs set `status = "failed"` with error detail stored in JSON — never leaves the user with no response |
| **Persistent volumes** | Uploaded files and database data survive container restarts via Docker named volumes |

---

## 9. Production Readiness

### What is already production-ready

| Concern | Status | Detail |
|---------|--------|--------|
| Database | Ready | PostgreSQL with persistent volume |
| Authentication | Ready | JWT with bcrypt, no plain-text passwords |
| Payment processing | Ready | Stripe with webhook signature verification |
| Background processing | Ready | RQ + Redis with thread fallback |
| Environment separation | Ready | `.env` / `.env.production` split, gitignored |
| Docker deployment | Ready | `docker-compose.prod.yml` for server deployment |
| CORS | Ready | Origin whitelist via `ALLOWED_ORIGINS` env var |
| Health checks | Ready | `/health` endpoint + Docker-level health checks |

### Recommended additions before high-traffic production

| Concern | Recommendation |
|---------|---------------|
| **File storage** | Move from local volume to AWS S3 / Google Cloud Storage |
| **API rate limiting** | Add `slowapi` middleware to FastAPI (per-IP or per-org limits) |
| **Logging** | Structured JSON logging (replace `print()` with Python `logging`) |
| **Monitoring** | Add Sentry (error tracking) + Grafana/Datadog (metrics) |
| **Database migrations** | Add Alembic for schema versioning instead of `create_all()` |
| **HTTPS** | Terminate SSL at a reverse proxy (Nginx or cloud load balancer) |
| **Secrets manager** | AWS Secrets Manager or HashiCorp Vault for production secrets (instead of `.env` files on disk) |
| **Backups** | Automated daily PostgreSQL backups (most managed DB services do this automatically) |

---

## 10. Environment Strategy

| Environment | Purpose | Database | Redis | Stripe Keys | AI Keys |
|-------------|---------|----------|-------|-------------|---------|
| **Development** | Local coding & testing | Local Docker Postgres | Local Docker Redis | Test keys | Real (low cost) |
| **Production** | Live users | Managed Postgres (Railway/Supabase/RDS) | Managed Redis | Live keys | Real |

### Running each environment

**Development:**
```bash
docker-compose up -d        # Start Postgres + Redis locally
./start.sh                  # Start backend + frontend
```

**Production (on server):**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

**Frontend build (production):**
```bash
cd frontend && npm run build   # Vite auto-uses .env.production
```

### Key environment files

| File | Committed to Git | Purpose |
|------|-----------------|---------|
| `backend/.env` | No | Dev secrets (local use only) |
| `backend/.env.production` | No | Prod secrets (server only) |
| `frontend/.env.development` | Yes (no secrets) | Dev API URL |
| `frontend/.env.production` | No | Prod API URL |
| `docker-compose.yml` | Yes | Dev infrastructure |
| `docker-compose.prod.yml` | Yes | Prod deployment config |

---

*Document maintained by the SaaSCostCompare engineering team.*
