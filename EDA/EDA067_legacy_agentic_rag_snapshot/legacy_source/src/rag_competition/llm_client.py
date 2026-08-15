from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import assert_formal_input_allowed, now_iso, sha1_text, write_json
from .schemas import PROMPT_VERSION


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class LlmResult:
    success: bool
    parsed_json: dict[str, Any]
    raw_response_path: str
    prompt_hash: str
    model: str
    provider: str
    finish_reason: str
    retry_count: int
    purpose: str = ""
    api_called: bool = False
    cache_hit: bool = False
    parse_success: bool = False
    error: str = ""
    http_status: int | None = None


class OpenRouterClient:
    def __init__(
        self,
        project_root: Path,
        output_dir: Path,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
        timeout_sec: int = 120,
        max_retries: int = 1,
        use_cache: bool = True,
    ) -> None:
        self.project_root = project_root
        self.output_dir = output_dir
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.use_cache = use_cache
        self.api_call_count = 0
        self.calls: list[dict[str, Any]] = []

    def read_api_key(self) -> str:
        key_path = self.project_root / ".apikey"
        assert_formal_input_allowed(key_path, self.project_root)
        if not key_path.exists():
            return ""
        for raw in key_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip().lower() in {"openrouter", "openrouter_api_key"}:
                return value.strip().strip("\"'")
        return ""

    def parse_json_or_empty(self, content: str) -> dict[str, Any]:
        if not isinstance(content, str):
            return {}
        text = content.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fenced:
            text = fenced.group(1)
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def log_call(self, row: dict[str, Any]) -> None:
        self.calls.append(row)

    def call_json(self, purpose: str, prompt: str, max_tokens: int = 1200, model: str | None = None) -> LlmResult:
        """OpenRouterへJSON応答を依頼し、raw responseと解析結果を保存する。"""
        api_key = self.read_api_key()
        prompt_hash = sha1_text(prompt)
        model_name = model or self.model
        model_hash = sha1_text(model_name)[:8]
        raw_dir = self.output_dir / "llm_raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        if not api_key:
            result = LlmResult(False, {}, "", prompt_hash, model_name, "", "", 0, purpose=purpose, error="OpenRouter API key not found")
            self.log_call(
                {
                    "purpose": purpose,
                    "model": model_name,
                    "prompt_hash": prompt_hash,
                    "api_called": False,
                    "cache_hit": False,
                    "parse_success": False,
                    "fallback_used": True,
                    "fallback_reason": result.error,
                }
            )
            return result

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Return JSON only. Do not include markdown fences."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        error = ""
        raw_path = raw_dir / f"{purpose}_{model_hash}_{prompt_hash[:16]}.json"
        parsed_path = raw_dir / f"{purpose}_{model_hash}_{prompt_hash[:16]}_parsed.json"
        if self.use_cache and raw_path.exists() and parsed_path.exists():
            parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
            parse_success = bool(parsed)
            result = LlmResult(
                parse_success,
                parsed if isinstance(parsed, dict) else {},
                raw_path.as_posix(),
                prompt_hash,
                model_name,
                "openrouter",
                "cached",
                0,
                purpose=purpose,
                api_called=False,
                cache_hit=True,
                parse_success=parse_success,
                error="" if parse_success else "cached JSON parse result is empty",
            )
            self.log_call(
                {
                    "purpose": purpose,
                    "model": model_name,
                    "prompt_hash": prompt_hash,
                    "api_called": False,
                    "cache_hit": True,
                    "parse_success": parse_success,
                    "fallback_used": not parse_success,
                    "fallback_reason": result.error,
                    "raw_response_path": raw_path.as_posix(),
                }
            )
            return result

        for retry in range(self.max_retries + 1):
            request = urllib.request.Request(
                OPENROUTER_URL,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            self.api_call_count += 1
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                    http_status = int(getattr(response, "status", 200))
                    body = response.read().decode("utf-8", errors="replace")
                    obj = json.loads(body)
                    content = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
                    finish_reason = obj.get("choices", [{}])[0].get("finish_reason", "")
                    parsed = self.parse_json_or_empty(content)
                    parse_success = bool(parsed)
                    write_json(
                        raw_path,
                        {
                            "timestamp": now_iso(),
                            "purpose": purpose,
                            "prompt_hash": prompt_hash,
                            "prompt_version": PROMPT_VERSION,
                            "model": model_name,
                            "temperature": self.temperature,
                            "seed": self.seed,
                            "retry": retry,
                            "finish_reason": finish_reason,
                            "response": obj,
                        },
                    )
                    write_json(parsed_path, parsed)
                    actual_model = str(obj.get("model") or model_name)
                    result = LlmResult(
                        parse_success,
                        parsed,
                        raw_path.as_posix(),
                        prompt_hash,
                        actual_model,
                        "openrouter",
                        finish_reason,
                        retry,
                        purpose=purpose,
                        api_called=True,
                        cache_hit=False,
                        parse_success=parse_success,
                        error="" if parse_success else "JSON parse result is empty",
                        http_status=http_status,
                    )
                    self.log_call(
                        {
                            "purpose": purpose,
                            "model": model_name,
                            "actual_model": actual_model,
                            "http_status": http_status,
                            "prompt_hash": prompt_hash,
                            "api_called": True,
                            "cache_hit": False,
                            "parse_success": parse_success,
                            "fallback_used": not parse_success,
                            "fallback_reason": result.error,
                            "finish_reason": finish_reason,
                            "retry_count": retry,
                            "raw_response_path": raw_path.as_posix(),
                        }
                    )
                    return result
            except urllib.error.HTTPError as exc:
                error = f"HTTPError {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            if retry < self.max_retries:
                time.sleep(1 + retry)

        write_json(
            raw_path,
            {
                "timestamp": now_iso(),
                "purpose": purpose,
                "prompt_hash": prompt_hash,
                "prompt_version": PROMPT_VERSION,
                "model": model_name,
                "temperature": self.temperature,
                "seed": self.seed,
                "error": error,
            },
        )
        self.log_call(
            {
                "purpose": purpose,
                "model": model_name,
                "prompt_hash": prompt_hash,
                "api_called": True,
                "cache_hit": False,
                "parse_success": False,
                "fallback_used": True,
                "fallback_reason": error,
                "retry_count": self.max_retries,
                "raw_response_path": raw_path.as_posix(),
            }
        )
        return LlmResult(
            False,
            {},
            raw_path.as_posix(),
            prompt_hash,
            model_name,
            "openrouter",
            "",
            self.max_retries,
            purpose=purpose,
            api_called=True,
            cache_hit=False,
            parse_success=False,
            error=error,
        )
