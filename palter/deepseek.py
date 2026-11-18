"""Small DeepSeek adapter with immutable instructions and measured usage."""

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shlex
import time
import urllib.error
import urllib.request

from .storage import canonical, fingerprint, observation_context

ROOT = Path(__file__).resolve().parent.parent
RATE_CARD = "deepseek-usd-2026-11-04-peak-upper"
RATES = {"deepseek-flash": (0.006, 0.30, 1.20), "deepseek-v4-pro": (0.044, 1.32, 3.96)}
MAX_OUTPUT_TOKENS = 192
MAX_INPUT_BYTES = 12000


def dotenv_values(path):
    """Parse assignments as data; never source shell code or print credentials."""
    result = {}
    if not Path(path).is_file():
        return result
    for line in Path(path).read_text().splitlines():
        line = line.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        if key.strip() not in {"DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"}:
            continue
        try:
            value = shlex.split(raw, comments=True)
        except ValueError:
            raise ValueError("Invalid quoted assignment in .env") from None
        result[key.strip()] = " ".join(value)
    return result


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = "deepseek-flash"
    timeout: float = 25

    @classmethod
    def load(cls, path=ROOT / ".env"):
        values = dotenv_values(path)
        model = os.environ.get("DEEPSEEK_MODEL", values.get("DEEPSEEK_MODEL", "deepseek-flash"))
        if model not in RATES:
            raise ValueError("DEEPSEEK_MODEL must be deepseek-flash or deepseek-v4-pro")
        return cls(api_key=os.environ.get("DEEPSEEK_API_KEY", values.get("DEEPSEEK_API_KEY", "")), model=model)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DeepSeek:
    def __init__(self, settings, transport=None):
        self.settings = settings
        directory = Path(__file__).parent / "prefixes"
        self._prefix = (directory / "review-v1.txt").read_text()
        manifest = json.loads((directory / "manifest.json").read_text())
        self.source_hash = hashlib.sha256(self._prefix.encode()).hexdigest()
        if self.source_hash != manifest["review-v1.txt"]:
            raise ValueError("Published prefix changed; publish a new version before continuing")
        self.prefix_hash = fingerprint({"version": "review-v1", "source_sha256": self.source_hash,
                                        "model": settings.model, "response_format": "json_object",
                                        "thinking": "disabled", "temperature": 0, "max_tokens": MAX_OUTPUT_TOKENS})
        self.transport = transport or self._send

    @property
    def configured(self):
        return bool(self.settings.api_key)

    def payload(self, view):
        payload = {"model": self.settings.model,
                   "messages": [{"role": "system", "content": self._prefix},
                                {"role": "user", "content": canonical(observation_context(view))}],
                   "thinking": {"type": "disabled"}, "temperature": 0,
                   "max_tokens": MAX_OUTPUT_TOKENS, "response_format": {"type": "json_object"}, "stream": False}
        if len(canonical(payload).encode()) > MAX_INPUT_BYTES:
            raise ValueError("Authorized input exceeds the demo input budget")
        return payload

    def _send(self, payload):
        request = urllib.request.Request("https://api.deepseek.com/chat/completions",
                  data=canonical(payload).encode(), method="POST",
                  headers={"Authorization": "Bearer " + self.settings.api_key,
                           "Content-Type": "application/json", "User-Agent": "PALTER-demo/0.1"})
        opener = urllib.request.build_opener(NoRedirect())
        thinking=payload.get('thinking',{}).get('type')=='enabled'
        timeout=max(self.settings.timeout,90) if thinking or payload.get("max_tokens",0)>=3000 else self.settings.timeout
        limit=512000 if payload.get("max_tokens",0)>4000 else 128000
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(limit+1)
        if len(raw) > limit:
            raise ValueError("Provider response exceeded size limit")
        return json.loads(raw)

    def review(self, view):
        start = time.monotonic()
        result = {"status": "failed", "usage": None, "selected": [], "cost_upper_usd": None,
                  "error_code": None, "returned_model": None}
        try:
            if not self.configured:
                result["error_code"] = "not_configured"
                return result
            response = self.transport(self.payload(view))
            if not isinstance(response, dict):
                raise ValueError("Unexpected provider response")
            usage = response.get("usage")
            if isinstance(usage, dict):
                keys = ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
                result["usage"] = {k: usage[k] if type(usage.get(k)) is int and usage[k] >= 0 else None for k in keys}
                u = result["usage"]
                if all(u[k] is not None for k in keys) and u["prompt_cache_hit_tokens"] + u["prompt_cache_miss_tokens"] == u["prompt_tokens"]:
                    hit, miss, output = RATES[self.settings.model]
                    result["cost_upper_usd"] = (u["prompt_cache_hit_tokens"] * hit + u["prompt_cache_miss_tokens"] * miss + u["completion_tokens"] * output) / 1_000_000
            returned_model = response.get("model")
            result["returned_model"] = returned_model[:120] if isinstance(returned_model, str) else None
            choice = response["choices"][0]
            if not isinstance(choice, dict):
                raise ValueError("Unexpected choice")
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete provider output")
            selection = json.loads(choice["message"]["content"])
            if not isinstance(selection, dict) or set(selection) != {"observation_ids"}:
                raise ValueError("Unexpected output shape")
            ids = selection["observation_ids"]
            known = {o["id"] for o in view["observations"]}
            if (not isinstance(ids, list) or len(ids) > 4 or any(not isinstance(i, str) or i not in known for i in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("Unknown or duplicate observation id")
            result.update(status="completed", selected=ids)
        except urllib.error.HTTPError as exc:
            result["error_code"] = f"http_{exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError):
            result["error_code"] = "connection_failed"
        except (ValueError, KeyError, IndexError, TypeError):
            result["error_code"] = "invalid_response"
        finally:
            result["latency_ms"] = round((time.monotonic() - start) * 1000)
        return result
