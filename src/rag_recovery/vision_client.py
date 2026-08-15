from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VisionAnswer:
    answer: str
    confidence: float
    source: str
    locator: str
    evidence: str


class OpenAICompatibleVisionClient:
    """Small OpenAI-compatible vision client with no provider-specific dependency."""

    def __init__(self, *, model: str, base_url: str | None = None, api_key: str | None = None, timeout: int = 120):
        self.model = model
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("Vision model was configured but no API key was supplied")

    def answer(self, question: str, images: list[tuple[Path, str, str]], context: str = "") -> VisionAnswer:
        content: list[dict[str, Any]] = [{
            "type": "text",
            "text": (
                "You are a document QA verifier. Answer only from the supplied rendered pages. "
                "Return one JSON object with keys answer, confidence, source, locator, evidence. "
                "confidence must be 0..1. If not uniquely answerable, set answer to わからない and confidence below 0.5.\n"
                f"Question: {question}\nAvailable pages:\n{context[:12000]}"
            ),
        }]
        for path, source, locator in images:
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            content.append({"type": "text", "text": f"SOURCE={source} LOCATOR={locator}"})
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Vision API HTTP {exc.code}: {detail[:1000]}") from exc
        text = data["choices"][0]["message"]["content"]
        obj = self._parse_object(text)
        return VisionAnswer(
            answer=str(obj.get("answer", "わからない")).strip(),
            confidence=float(obj.get("confidence", 0.0)),
            source=str(obj.get("source", "")).strip(),
            locator=str(obj.get("locator", "")).strip(),
            evidence=str(obj.get("evidence", "")).strip(),
        )

    @staticmethod
    def _parse_object(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                raise ValueError("Vision response did not contain a JSON object")
            return json.loads(match.group())
