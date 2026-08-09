from __future__ import annotations

import json, re
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from .models import Email

@dataclass
class Decision:
    action: str
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None
    category: str | None = None
    priority: str | None = None
    due_date: str | None = None
    deal_value_inr: int | None = None
    company_name: str | None = None
    confidence: float = 0.0
    skip_reason: str | None = None
    reasoning: str = ""

SPAM = ["seo", "page 1", "free audit", "organic traffic", "unsubscribe", "newsletter", "issue #", "growth weekly", "out of office", "auto-reply", "automatic reply", "limited access to email", "circling back", "guest post"]
RFP = ["rfp", "rfi", "tender", "proposal", "bid submission", "invites bids", "procurement"]
PSU = ["bhel", "bharat heavy", "psu", "government", "govt", "ministry", "public sector", "municipal", "railways", "state electricity"]
MARKETING = ["webinar", "sponsorship", "conference", "summit", "event", "media", "content collaboration", "co-host", "public relations"]
ALLIANCE = ["reseller", "channel partner", "partner", "integration", "technology integration", "alliances", "partnership"]
FINANCE = ["invoice", "gst", "gstin", "po-", "purchase order", "payment", "overdue", "vendor billing"]
SMB = ["demo", "product enquiry", "trial", "pricing", "can we get", "quick call", "evaluate your platform", "product chahiye"]


def clean_text(email: Email) -> str:
    body = re.split(r"\n\s*(On .+ wrote:|From: .+|-----Original Message-----)", email.body, flags=re.I)[0]
    return f"{email.subject}\n{body}".lower()

def parse_money(text: str, finance_context=False) -> int | None:
    if finance_context and re.search(r"invoice|payment|gst|po-|purchase order", text, re.I):
        return None
    money_pattern = re.compile(r"(?P<currency>rs\.?|₹|inr)?\s*(?P<amount>[0-9][0-9,]*(?:\.\d+)?)\s*(?P<unit>cr|crore|crores|lakh|lakhs|lac|lacs|k)?", re.I)
    for m in money_pattern.finditer(text):
        unit = (m.group("unit") or "").lower()
        has_currency = bool(m.group("currency"))
        if not has_currency and not unit:
            continue
        n = float(m.group("amount").replace(",", ""))
        if unit in {"cr", "crore", "crores"}: n *= 10000000
        elif unit in {"lakh", "lakhs", "lac", "lacs"}: n *= 100000
        elif unit == "k": n *= 1000
        return int(n)
    return None

def parse_due(text: str, received_at: str) -> str | None:
    base = dateparser.parse(received_at)
    if re.search(r"tomorrow", text, re.I): return (base + timedelta(days=1)).date().isoformat()
    m = re.search(r"(?:by|before|deadline|last date|due|review|submission).*?(\d{1,2}(?:st|nd|rd|th)?(?:[-/ ](?:aug(?:ust)?|\d{1,2})(?:[-/ ]\d{2,4})?)?)", text, re.I)
    if not m: return None
    raw = re.sub(r"(st|nd|rd|th)", "", m.group(1), flags=re.I)
    try:
        dt = dateparser.parse(raw, default=base.replace(day=1), dayfirst=True)
        if dt.year < base.year: dt = dt.replace(year=base.year)
        return dt.date().isoformat()
    except Exception:
        return None

def company(email: Email, text: str) -> str | None:
    sig = re.search(r"[—-]\s*[^,\n]+,\s*(?:Founder|VP|Lead|Manager|Director|Procurement|Strategy),\s*([^\n]+)", email.body, re.I)
    if sig: return sig.group(1).strip().strip(".")
    for pat in [r"for the ([A-Z][A-Za-z0-9 &.-]+?(?:Summit|Conference))", r"([A-Z][A-Za-z &]+ Limited) invites", r"([A-Z][A-Za-z &]+) invites proposals"]:
        m = re.search(pat, email.body)
        if m: return m.group(1).strip()
    return None

def priority(text: str, received_at: str, due: str | None) -> str:
    if re.search(r"overdue|urgent|asap", text, re.I): return "high"
    if due:
        try:
            hours = (dateparser.parse(due) - dateparser.parse(received_at).replace(tzinfo=None)).total_seconds()/3600
            if 0 <= hours <= 72: return "high"
        except Exception: pass
    if re.search(r"nothing urgent|sometime next week", text, re.I): return "low"
    return "medium"

def has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)

def has_marketing_signal(raw: str, text: str) -> bool:
    if has_any(text, MARKETING):
        return True
    # Keep PR/public-relations support without matching the substring inside
    # enterprise, proposal, process, product, approximate, etc.
    return bool(re.search(r"(?<![A-Za-z])PR(?![A-Za-z])", raw))

def route_email(email: Email) -> Decision:
    text = clean_text(email); raw = f"{email.subject}\n{email.body}"
    spam_hit = any(s in text for s in SPAM)
    if spam_hit and not any(k in text for k in ["invoice", "rfp", "tender"]):
        reason = "Skipped as newsletter/OOO/vendor spam based on auto-reply, unsubscribe, SEO, or unsolicited outreach signals."
        return Decision(action="skip", skip_reason="noise", confidence=0.93, reasoning=reason)
    due = parse_due(raw, email.received_at); fin = any(k in text for k in FINANCE)
    value = parse_money(raw, finance_context=fin); comp = company(email, text)
    signals = {"rfp": has_any(text, RFP), "marketing": has_marketing_signal(raw, text), "alliances": has_any(text, ALLIANCE), "finance": fin, "smb": has_any(text, SMB)}
    if sum(signals.values()) > 1 and not signals["finance"] and "invoice" not in text:
        return Decision("task", "Ambiguous inbound request", "Multiple ownership signals detected; human review needed.", "u_triage", "triage", priority(text,email.received_at,due), due, value, comp, 0.42, reasoning=json.dumps(signals))
    if signals["finance"]:
        return Decision("task", "Finance follow-up", "Invoice, PO, GST, or payment-related message for Finance.", "u_divya", "finance", priority(text,email.received_at,due), due, None, comp, 0.88, reasoning="finance keywords")
    if signals["marketing"]:
        return Decision("task", "Marketing opportunity", "Event/webinar/sponsorship/content/media request.", "u_meera", "marketing", priority(text,email.received_at,due), due, value, comp, 0.84, reasoning="marketing intent")
    if signals["alliances"]:
        return Decision("task", "Partnership or integration proposal", "Reseller/channel/technology integration request.", "u_karan", "alliances", priority(text,email.received_at,due), due, None, comp, 0.82, reasoning="alliance intent")
    if signals["rfp"] or any(k in text for k in PSU) or (value and value > 1000000):
        assignee = "u_aarti" if any(k in text for k in PSU) or (value and value > 1000000) or signals["rfp"] else "u_rohit"
        return Decision("task", "Enterprise RFP or tender", "RFP/RFI/tender or high-value inbound deal.", assignee, "enterprise_rfp", priority(text,email.received_at,due), due, value, comp, 0.86, reasoning="enterprise/tender/value signals")
    if signals["smb"] or (value is not None and value <= 1000000):
        return Decision("task", "SMB product enquiry", "Demo, pricing, trial, or lower-value product enquiry.", "u_rohit", "smb_enquiry", priority(text,email.received_at,due), due, value, comp, 0.78, reasoning="smb/demo signals")
    return Decision("task", "Needs triage", "No clean business route matched; ops review required.", "u_triage", "triage", priority(text,email.received_at,due), due, value, comp, 0.35, reasoning="fallback triage")
