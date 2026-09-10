"""Optionaler Gemini-Assistent fuer Projekt und Prioritaet."""

from __future__ import annotations

import asyncio
import logging
import re

from .priority import PRIORITIES

logger = logging.getLogger(__name__)

PROMPT = """Du klassifizierst eine private Todo/Notiz fuer TaskBuddy.

Text:
{text}

Item-Typ: {item_type}

Bekannte Projekte (id|name|kind):
{projects}

Regeln:
- Waehle genau EIN project_id aus der Liste, oder NONE wenn unklar.
- Nur bei Tasks: waehle Prioritaet A, B, C oder D:
  A = Wichtig & Dringend
  B = Dringend & Unwichtig
  C = Wichtig & Undringend
  D = Unwichtig & Undringend
- Bei Notizen: priority = NONE
- Sei konservativ: lieber NONE als raten.

Antworte exakt in einer Zeile:
project=<id|NONE>; priority=<A|B|C|D|NONE>; confidence=<0.0-1.0>
"""


class GeminiClassifier:
    def __init__(self, api_key: str, model: str, *, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def classify(
        self,
        *,
        text: str,
        item_type: str,
        projects: list[tuple[int, str, str]],
    ) -> dict[str, object]:
        """Liefert project_id, priority, confidence – oder leeres dict bei Fehler."""
        if not projects:
            return {}
        project_lines = "\n".join(f"{pid}|{name}|{kind}" for pid, name, kind in projects)
        prompt = PROMPT.format(
            text=text,
            item_type=item_type,
            projects=project_lines,
        )
        try:
            from google.genai import types

            client = self._ensure_client()
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.0),
                ),
                timeout=self._timeout,
            )
            raw = (getattr(response, "text", None) or "").strip()
            return _parse_response(raw, item_type=item_type, valid_ids={p[0] for p in projects})
        except Exception:
            logger.exception("Gemini-Klassifikation fehlgeschlagen")
            return {}


def _parse_response(
    raw: str, *, item_type: str, valid_ids: set[int]
) -> dict[str, object]:
    match = re.search(
        r"project\s*=\s*(\d+|NONE)\s*;\s*priority\s*=\s*([ABCD]|NONE)\s*;\s*confidence\s*=\s*([01](?:\.\d+)?)",
        raw,
        re.IGNORECASE,
    )
    if not match:
        return {}
    proj_raw, prio_raw, conf_raw = match.groups()
    project_id: int | None
    if proj_raw.upper() == "NONE":
        project_id = None
    else:
        project_id = int(proj_raw)
        if project_id not in valid_ids:
            project_id = None
    priority = None if prio_raw.upper() == "NONE" else prio_raw.upper()
    if item_type != "task":
        priority = None
    elif priority not in PRIORITIES:
        priority = None
    try:
        confidence = float(conf_raw)
    except ValueError:
        confidence = 0.0
    return {
        "project_id": project_id,
        "priority": priority,
        "confidence": max(0.0, min(1.0, confidence)),
    }
