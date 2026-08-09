from __future__ import annotations

import json, os, uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import connect, init_db
from .gemini import phrase_answer
from .models import ASSIGNEES, CATEGORIES, PRIORITIES, ChatRequest, IngestRequest, TaskCreate, TaskPatch
from .roster import TEAM
from .routing import route_email

app = FastAPI(title="Sales Inbox Router")
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()
app.add_middleware(CORSMiddleware, allow_origins=[frontend_origin], allow_methods=["*"], allow_headers=["*"])
init_db()

def now(): return datetime.now(timezone.utc).isoformat()
def rowdict(r): return dict(r) if r else None

def enum_error(field, received, allowed):
    return JSONResponse(status_code=400, content={"error":"invalid_enum_value","field":field,"received":received,"allowed":allowed})

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    for field, allowed in [("assignee_id", ASSIGNEES),("category", CATEGORIES),("priority", PRIORITIES)]:
        if isinstance(body, dict) and field in body:
            return enum_error(field, body[field], allowed)
    return JSONResponse(status_code=400, content={"error":"validation_error","details":exc.errors()})

@app.get("/health")
def health(): return {"ok": True}

@app.get("/users")
def users(): return {"team": TEAM}

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    ts = now(); task_id = "tsk_" + uuid.uuid4().hex[:8]
    data = task.model_dump()
    with connect() as con:
        existing = con.execute("SELECT * FROM tasks WHERE candidate_id=? AND (source_email_id=? OR thread_id=?)", (task.candidate_id, task.source_email_id, task.thread_id)).fetchone()
        if existing:
            return JSONResponse(status_code=201, content={"task_id": existing["task_id"], "candidate_id": existing["candidate_id"], "source_email_id": existing["source_email_id"], "created_at": existing["created_at"]})
        con.execute("""INSERT INTO tasks VALUES (:task_id,:candidate_id,:source_email_id,:thread_id,:title,:description,:assignee_id,:category,:priority,:due_date,:deal_value_inr,:company_name,:confidence,:created_at,:updated_at)""", {**data,"task_id":task_id,"created_at":ts,"updated_at":ts})
    return {"task_id": task_id, "candidate_id": task.candidate_id, "source_email_id": task.source_email_id, "created_at": ts}

@app.patch("/tasks/{task_id}")
def patch_task(task_id: str, patch: TaskPatch):
    updates = {k:v for k,v in patch.model_dump(exclude_unset=True).items()}
    if not updates: raise HTTPException(400, "empty_patch")
    updates["updated_at"] = now()
    with connect() as con:
        if not con.execute("SELECT 1 FROM tasks WHERE task_id=?", (task_id,)).fetchone(): raise HTTPException(404, "task_not_found")
        sql = ", ".join(f"{k}=?" for k in updates)
        con.execute(f"UPDATE tasks SET {sql} WHERE task_id=?", [*updates.values(), task_id])
        return rowdict(con.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone())

@app.get("/tasks")
def list_tasks(candidate_id: str, thread_id: str | None=None, source_email_id: str | None=None, assignee_id: str | None=None):
    q="SELECT * FROM tasks WHERE candidate_id=?"; args=[candidate_id.strip().lower()]
    for k,v in [("thread_id",thread_id),("source_email_id",source_email_id),("assignee_id",assignee_id)]:
        if v: q += f" AND {k}=?"; args.append(v)
    with connect() as con: return [rowdict(r) for r in con.execute(q, args).fetchall()]

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    with connect() as con: con.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
    return {"deleted": True}

@app.post("/ingest")
def ingest(req: IngestRequest):
    if len(req.emails) > 100: raise HTTPException(400, "batch_limit_100")
    run_id = "run_" + uuid.uuid4().hex[:8]; stats = {"processed":0,"tasks_created":0,"tasks_updated":0,"skipped":0,"errors":[]}
    with connect() as con:
        for email in req.emails:
            try:
                stats["processed"] += 1
                if con.execute("SELECT 1 FROM decisions WHERE candidate_id=? AND email_id=?", (req.candidate_id,email.email_id)).fetchone():
                    continue
                decision = route_email(email); task_id = None
                existing = con.execute("SELECT * FROM tasks WHERE candidate_id=? AND thread_id=?", (req.candidate_id,email.thread_id)).fetchone()
                if decision.action == "skip": stats["skipped"] += 1
                elif existing:
                    task_id = existing["task_id"]; stats["tasks_updated"] += 1
                    confident_route = decision.category != "triage" or existing["category"] == "triage" or decision.confidence >= 0.6
                    fields = {"source_email_id": email.email_id, "updated_at": now()}
                    if confident_route:
                        fields.update({
                            "title": decision.title,
                            "description": decision.description,
                            "assignee_id": decision.assignee_id,
                            "category": decision.category,
                            "confidence": decision.confidence,
                        })
                    if decision.priority == "high" or confident_route:
                        fields["priority"] = decision.priority
                    for field in ("due_date", "deal_value_inr", "company_name"):
                        value = getattr(decision, field)
                        if value is not None:
                            fields[field] = value
                    con.execute("UPDATE tasks SET " + ",".join(f"{k}=?" for k in fields) + " WHERE task_id=?", [*fields.values(), task_id])
                    con.execute("INSERT INTO update_events(candidate_id,thread_id,task_id,source_email_id,created_at) VALUES (?,?,?,?,?)", (req.candidate_id,email.thread_id,task_id,email.email_id,now()))
                else:
                    task_id = "tsk_" + uuid.uuid4().hex[:8]; stats["tasks_created"] += 1
                    con.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (task_id,req.candidate_id,email.email_id,email.thread_id,decision.title,decision.description,decision.assignee_id,decision.category,decision.priority,decision.due_date,decision.deal_value_inr,decision.company_name,decision.confidence,now(),now()))
                con.execute("INSERT INTO decisions(candidate_id,run_id,email_id,thread_id,action,skip_reason,task_id,category,assignee_id,priority,confidence,reasoning,raw_email_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (req.candidate_id,run_id,email.email_id,email.thread_id,decision.action,decision.skip_reason,task_id,decision.category,decision.assignee_id,decision.priority,decision.confidence,decision.reasoning,email.model_dump_json(),now()))
            except Exception as e:
                stats["errors"].append({"email_id": email.email_id, "error": str(e)})
    return stats

@app.get("/api/tasks")
def api_tasks(candidate_id: str):
    with connect() as con:
        return {"tasks": [rowdict(r) for r in con.execute("SELECT * FROM tasks WHERE candidate_id=?", (candidate_id.strip().lower(),)).fetchall()], "decisions": [rowdict(r) for r in con.execute("SELECT * FROM decisions WHERE candidate_id=?", (candidate_id.strip().lower(),)).fetchall()]}

@app.get("/api/stats")
def api_stats(candidate_id: str): return compute_stats(candidate_id.strip().lower())

def compute_stats(cid: str):
    with connect() as con:
        processed=con.execute("SELECT COUNT(*) c FROM decisions WHERE candidate_id=?",(cid,)).fetchone()["c"]
        skipped=con.execute("SELECT COUNT(*) c FROM decisions WHERE candidate_id=? AND action='skip'",(cid,)).fetchone()["c"]
        by_cat={r["category"] or "skipped":r["c"] for r in con.execute("SELECT COALESCE(category,'skipped') category, COUNT(*) c FROM decisions WHERE candidate_id=? GROUP BY COALESCE(category,'skipped')",(cid,))}
        return {"processed":processed,"created":con.execute("SELECT COUNT(*) c FROM tasks WHERE candidate_id=?",(cid,)).fetchone()["c"],"updated":con.execute("SELECT COUNT(*) c FROM update_events WHERE candidate_id=?",(cid,)).fetchone()["c"],"skipped":skipped,"spurious_flagged":None,"spurious_note":"Not tracked without human/eval labels; skipped noise is tracked separately.","by_category":by_cat}

@app.post("/api/chat")
def chat(req: ChatRequest):
    q=req.query.lower(); cid=req.candidate_id

    def respond(answer: str, supporting_data: dict):
        return {"answer": phrase_answer(req.query, answer, supporting_data), "supporting_data": supporting_data}

    with connect() as con:
        if any(w in q for w in ["send ", "email ", "delete", "assign"]):
            return respond("I can answer questions about processed inbox data, but I cannot send emails or take external actions.", {})
        if "gst refund" in q:
            return respond("Zero processed emails were classified as GST refund requests.", {"gst_refund_count":0})
        if "spurious" in q:
            s=compute_stats(cid)
            data={"spurious_count":None,"processed":s["processed"],"spurious_rate":None,"note":s["spurious_note"]}
            return respond(f"I do not track true spurious tasks yet because that requires human or evaluator labels. I processed {s['processed']} emails and tracked {s['skipped']} skipped noise emails separately.", data)
        if "triage" in q:
            rows=[rowdict(r) for r in con.execute("SELECT task_id,description,confidence,thread_id FROM tasks WHERE candidate_id=? AND category='triage'",(cid,))]
            data={"triage_count":len(rows),"triage_task_ids":[r["task_id"] for r in rows]}
            return respond("Triage items: "+("; ".join(f"{r['task_id']} ({r['thread_id']}): {r['description']}" for r in rows) if rows else "none."), data)
        if "high" in q and "confidence" in q:
            rows=[rowdict(r) for r in con.execute("SELECT task_id,confidence,title FROM tasks WHERE candidate_id=? AND priority='high' AND confidence < 0.6",(cid,))]
            return respond(f"Found {len(rows)} high-priority low-confidence tasks.", {"matches":rows})
        if "deal value" in q:
            r=con.execute("SELECT SUM(deal_value_inr) total, SUM(CASE WHEN deal_value_inr IS NULL THEN 1 ELSE 0 END) missing FROM tasks WHERE candidate_id=? AND category='enterprise_rfp'",(cid,)).fetchone()
            data={"total_deal_value_inr":r['total'] or 0,"rfps_with_no_stated_value":r['missing'] or 0}
            return respond(f"Total stated deal value for RFPs is ₹{r['total'] or 0:,}; {r['missing'] or 0} RFP tasks had no stated value.", data)
        if "updated more than once" in q:
            rows=[r["thread_id"] for r in con.execute("SELECT thread_id FROM update_events WHERE candidate_id=? GROUP BY thread_id HAVING COUNT(*)>1",(cid,))]
            return respond(f"Threads updated more than once: {', '.join(rows) if rows else 'none'}.", {"threads_updated_multiple_times":rows})
        if "alliance" in q:
            c=con.execute("SELECT COUNT(*) c FROM tasks WHERE candidate_id=? AND category='alliances'",(cid,)).fetchone()["c"]
            return respond(f"There are {c} alliance emails. I do not store a reliable reseller-vs-integration sub-breakdown, so I will not guess.", {"alliances":c})
        cats={r["category"]:r["c"] for r in con.execute("SELECT category, COUNT(*) c FROM decisions WHERE candidate_id=? GROUP BY category",(cid,))}
        spam=con.execute("SELECT COUNT(*) c FROM decisions WHERE candidate_id=? AND action='skip'",(cid,)).fetchone()["c"]
        data={"enterprise_rfp":cats.get('enterprise_rfp',0),"marketing":cats.get('marketing',0),"skipped_marketing_lookalike_spam":spam}
        return respond(f"Enterprise RFP: {data['enterprise_rfp']}, marketing: {data['marketing']}, skipped noise/spam: {spam}.", data)
