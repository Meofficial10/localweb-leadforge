"""Real Ollama provider - generates a JSON object (optionally validated by a schema)."""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.config import settings
from app.llm.base import LLMProvider, LLMSchemaError, LLMUnavailable


class OllamaLLM(LLMProvider):
    name = "ollama"

    def __init__(self, base_url="", model="", timeout=120, client=None):
        self.base_url = (base_url or settings.ollama_base_url or "http://localhost:11434").rstrip("/")
        self.model = model or settings.llm_model or "qwen2.5:3b"
        self.timeout = timeout
        self.client = client or httpx.Client(timeout=timeout)
        self.last_payload = {}

    def installed_models(self):
        import httpx as _hx
        try:
            r = _hx.get(self.base_url + "/api/tags", timeout=30)
            r.raise_for_status()
            return [m.get("name") or m.get("model") for m in r.json().get("models", [])]
        except Exception:
            return []

    def generate(self, prompt, schema=None):
        self.last_payload = {"latency_ms": None, "ok": False, "error": None}
        if not self.installed_models():
            self.last_payload["error"] = "Ollama not reachable or no models installed"
            raise LLMUnavailable(self.last_payload["error"])
        instruction = ""
        if schema is not None:
            instruction = " Return ONLY a single JSON object matching this schema: " + json.dumps(schema)
        messages = [{"role": "user", "content": prompt + instruction}]
        body = {"model": self.model, "messages": messages, "stream": False}
        if schema is not None:
            body["format"] = "json"
        t0 = time.monotonic()
        latency = 0
        try:
            r = self.client.post(self.base_url + "/api/chat", json=body,
                                 headers={"Content-Type": "application/json"})
            latency = int((time.monotonic() - t0) * 1000)
            self.last_payload["latency_ms"] = latency
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and data.get("error") and not data.get("message"):
                self.last_payload["error"] = str(data.get("error"))
                raise LLMUnavailable(str(data.get("error")))
            text = (data.get("message") or {}).get("content") or ""
            if not text:
                self.last_payload["error"] = "empty model response"
                raise LLMUnavailable("empty model response")
            self.last_payload["tokens"] = {"prompt": data.get("prompt_eval_count"),
                                            "completion": data.get("eval_count"),
                                            "total": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)}
            if schema is not None:
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    cleaned = text.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("```", 2)[1].lstrip("json").strip()
                    obj = json.loads(cleaned)
            else:
                obj = {"content": text}
            self.last_payload["ok"] = True
            self.last_payload["response"] = text
            return obj
        except httpx.HTTPStatusError as exc:
            self.last_payload["error"] = "HTTP " + str(exc.response.status_code) + ": " + exc.response.text[:200]
            self.last_payload["latency_ms"] = latency
            raise LLMUnavailable(self.last_payload["error"]) from exc
        except Exception as exc:
            self.last_payload["error"] = str(exc)
            self.last_payload["latency_ms"] = latency
            raise LLMUnavailable(str(exc)) from exc
