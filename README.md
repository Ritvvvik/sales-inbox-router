# Sales Inbox → Task Router

**candidate_id:** `priya.sharma@gmail.com`  
**Backend URL:** `https://your-backend.example.com`  
**Frontend URL:** `https://your-frontend.example.com`  
**Public GitHub repo:** `https://github.com/your-user/sales-inbox-router`

## Setup (3 commands)

```bash
cp .env.example .env
pip install -r requirements-dev.txt
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend && npm install && VITE_BACKEND_URL=http://localhost:8000 npm run dev
```

## What ships

- FastAPI backend with `/ingest`, raw Task API `/tasks`, `/users`, and frontend wrappers `/api/tasks`, `/api/stats`, `/api/chat`.
- SQLite persistence by default via `DATABASE_URL=sqlite:///./router.db`.
- React/Vite frontend that pastes or generates emails, renders the raw table before routing, submits to `/ingest`, and asks grounded chat questions.

## Environment

See `.env.example`. `GEMINI_API_KEY` is optional for this baseline because routing and chat numbers are deterministic and grounded in the database; it is never exposed to browser JavaScript.
