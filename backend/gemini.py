from __future__ import annotations

import os
import google.generativeai as genai


def phrase_answer(query: str, draft_answer: str, supporting_data: dict) -> str:
    """Use Gemini to phrase an already-computed answer without inventing numbers."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return draft_answer

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    prompt = f"""
You are an operations assistant for a sales inbox router.
Rewrite the draft answer in a concise, helpful way.
Rules:
- Use only the supporting_data JSON and draft answer.
- Do not add, infer, or change any numbers.
- If supporting_data says a metric is not tracked, say that plainly.
- Do not claim to take actions such as sending emails.

User question: {query}
Draft answer: {draft_answer}
Supporting data: {supporting_data}
""".strip()
    try:
        response = model.generate_content(prompt)
        text = getattr(response, "text", "").strip()
        return text or draft_answer
    except Exception:
        return draft_answer
