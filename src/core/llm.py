"""
Multi-provider LLM Client untuk ScholarScout.
Mendukung: Gemini (gratis), Groq (gratis), OpenRouter, Ollama (lokal), OpenAI.
"""
import urllib.request
import urllib.error
import json
import time
import os
from typing import Optional, Callable

from src.core.config import Config


# ─── Provider Registry ──────────────────────────────────────────────────────────
PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "default_model": "gemini-2.0-flash",
        "free": True,
        "key_env": "GEMINI_API_KEY",
        "docs": "https://aistudio.google.com/app/apikey",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "llama-3.3-70b-versatile",
        "free": True,
        "key_env": "GROQ_API_KEY",
        "docs": "https://console.groq.com/keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "deepseek/deepseek-chat",
        "free": False,
        "key_env": "OPENROUTER_API_KEY",
        "docs": "https://openrouter.ai/keys",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "free": False,
        "key_env": "OPENAI_API_KEY",
        "docs": "https://platform.openai.com/api-keys",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1/chat/completions",
        "default_model": "llama3.2",
        "free": True,
        "key_env": None,
        "docs": "https://ollama.com/download",
    },
    "custom": {
        "name": "Custom OpenAI-Compatible",
        "base_url": "",
        "default_model": "",
        "free": False,
        "key_env": None,
        "docs": "",
    },
}

# ─── Token budget presets per task type ──────────────────────────────────────────
TOKEN_BUDGETS = {
    "ping": 10,
    "trend_analysis": 600,
    "idea_generation": 3000,
    "deep_dive": 2000,
    "default": 1500,
}


class LLMClient:
    """
    Multi-provider LLM client.
    Supports Gemini, Groq, OpenRouter, OpenAI, Ollama, and custom endpoints.
    """

    def __init__(self, emit_fn: Optional[Callable] = None):
        self.emit_fn = emit_fn
        self.provider = Config.LLM_PROVIDER
        self.api_key = Config.LLM_API_KEY
        self.model = Config.LLM_MODEL
        self.base_url = Config.LLM_BASE_URL
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0

    def _emit(self, event, **kwargs):
        if self.emit_fn:
            try:
                self.emit_fn(event, **kwargs)
            except Exception:
                pass

    def get_token_stats(self) -> dict:
        """Return token usage statistics."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_calls": self.total_calls,
        }

    def call(self, prompt: str, retries: int = 3, task_type: str = "default") -> Optional[str]:
        """
        Memanggil LLM dengan adaptive max_tokens berdasarkan task type.
        
        Args:
            prompt: Teks prompt
            retries: Jumlah retry
            task_type: Tipe task untuk menentukan max_tokens budget
        """
        if self.provider == "gemini":
            return self._call_gemini(prompt, retries, task_type)
        else:
            return self._call_openai_compatible(prompt, retries, task_type)

    def _call_gemini(self, prompt: str, retries: int, task_type: str) -> Optional[str]:
        """Call Google Gemini API (different format from OpenAI)."""
        if not self.api_key:
            self._emit("llm_error", msg="Gemini API Key not found! Get one at https://aistudio.google.com/app/apikey")
            return None

        max_tokens = TOKEN_BUDGETS.get(task_type, TOKEN_BUDGETS["default"])
        url = self.base_url.format(model=self.model) + f"?key={self.api_key}"
        
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": max_tokens,
            }
        }).encode("utf-8")

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, data=payload, headers={
                    "Content-Type": "application/json"
                }, method="POST")
                
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    # Track tokens
                    usage = data.get("usageMetadata", {})
                    self.total_input_tokens += usage.get("promptTokenCount", 0)
                    self.total_output_tokens += usage.get("candidatesTokenCount", 0)
                    self.total_calls += 1
                    return text

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    wait = 15 * (attempt + 1)
                    self._emit("llm_wait", msg=f"Gemini rate limit — waiting {wait}s (attempt {attempt+1}/{retries})")
                    time.sleep(wait)
                elif e.code == 400 and "API_KEY" in body:
                    self._emit("llm_error", msg="Gemini API Key invalid. Get a new one at https://aistudio.google.com/app/apikey")
                    return None
                else:
                    self._emit("llm_error", msg=f"Gemini HTTP {e.code}: {body[:120]}")
                    if attempt >= retries:
                        return None
                    time.sleep(5)
            except Exception as e:
                self._emit("llm_error", msg=f"Gemini attempt {attempt+1}: {str(e)[:80]}")
                time.sleep(4)

        self._emit("llm_error", msg=f"Gemini call failed after {retries+1} attempts")
        return None

    def _call_openai_compatible(self, prompt: str, retries: int, task_type: str) -> Optional[str]:
        """Call OpenAI-compatible API (OpenRouter, Groq, OpenAI, Ollama, Custom)."""
        # Custom endpoints may not need a key (local proxy, LM Studio, etc.)
        no_key_needed = self.provider in ("ollama", "custom")
        if not self.api_key and not no_key_needed:
            provider_info = PROVIDERS.get(self.provider, {})
            docs = provider_info.get("docs", "")
            self._emit("llm_error", msg=f"API Key not found! Get one at {docs}")
            return None

        if not self.base_url:
            self._emit("llm_error", msg="Base URL is empty. Set it in Settings or the setup wizard.")
            return None

        max_tokens = TOKEN_BUDGETS.get(task_type, TOKEN_BUDGETS["default"])
        
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://scholarscout.app"
            headers["X-Title"] = "ScholarScout"

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(
                    self.base_url, data=payload, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")

                text = self._parse_response(raw)

                # Track tokens from JSON response if available
                try:
                    if not raw.lstrip().startswith("data:"):
                        usage = json.loads(raw).get("usage", {})
                        self.total_input_tokens  += usage.get("prompt_tokens", 0)
                        self.total_output_tokens += usage.get("completion_tokens", 0)
                except Exception:
                    pass

                if text:
                    self.total_calls += 1
                    return text

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    wait = 20 * (attempt + 1)
                    self._emit("llm_wait", msg=f"Rate limit (429) — waiting {wait}s (attempt {attempt+1}/{retries})")
                    time.sleep(wait)
                elif e.code in (500, 502, 503):
                    self._emit("llm_warn", msg=f"Server error {e.code} — retry {attempt+1}/{retries}")
                    time.sleep(6)
                elif e.code == 401:
                    self._emit("llm_error", msg=f"API Key invalid (401). Periksa config.yaml")
                    return None
                else:
                    self._emit("llm_error", msg=f"HTTP {e.code}: {body[:120]}")
                    return None
            except Exception as e:
                self._emit("llm_error", msg=f"Attempt {attempt+1}/{retries}: {str(e)[:80]}")
                time.sleep(4)

        self._emit("llm_error", msg=f"LLM call failed after {retries+1} attempts")
        return None

    def _parse_sse(self, raw: str) -> str:
        """
        Parse SSE (Server-Sent Events) streaming response into plain text.
        Handles providers that stream even when stream=False is requested.

        Format:
            data: {"choices":[{"delta":{"content":"Hello"}}]}\n
            data: {"choices":[{"delta":{"content":" world"}}]}\n
            data: [DONE]\n
        """
        parts = []
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj = json.loads(chunk)
                choice = obj.get("choices", [{}])[0]
                # streaming delta
                content = choice.get("delta", {}).get("content", "")
                # or non-streaming message (some providers mix formats)
                if not content:
                    content = choice.get("message", {}).get("content", "")
                if content:
                    parts.append(content)
            except (json.JSONDecodeError, IndexError, KeyError):
                continue
        return "".join(parts).strip()

    def _parse_response(self, raw: str) -> str:
        """
        Parse LLM response — handles three formats:
        1. Pure SSE stream  (starts with 'data:')
        2. JSON + SSE tail  (valid JSON body followed by 'data: [DONE]')
        3. Plain JSON       (standard non-streaming response)
        """
        stripped = raw.strip()

        # Pure SSE stream
        if stripped.startswith("data:"):
            return self._parse_sse(stripped)

        # JSON body possibly followed by SSE trailer (e.g. '\ndata: [DONE]')
        # Split on first newline sequence that starts a 'data:' line
        json_part = stripped
        for i, line in enumerate(stripped.splitlines()):
            if line.strip().startswith("data:"):
                json_part = "\n".join(stripped.splitlines()[:i]).strip()
                break

        if json_part:
            try:
                data = json.loads(json_part)
                # Standard OpenAI-compatible response
                content = data["choices"][0]["message"]["content"].strip()
                return content
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        # Last resort: try full SSE parse on the whole thing
        return self._parse_sse(stripped)

    def ping(self) -> tuple:
        """
        Validates the LLM API is reachable.

        Returns:
            (ok: bool, error_msg: str)  — error_msg is empty string on success.
        """
        no_key_needed = self.provider in ("ollama", "custom")
        if not self.api_key and not no_key_needed:
            provider_info = PROVIDERS.get(self.provider, {})
            msg = f"API Key is empty. Get one at {provider_info.get('docs', 'Settings tab')}"
            self._emit("fatal_error", msg=msg)
            return False, msg

        if self.provider != "gemini" and not self.base_url:
            msg = "Base URL is empty. Set it in Settings (e.g. http://localhost:11434/v1)"
            self._emit("fatal_error", msg=msg)
            return False, msg

        self._emit("ping_start", msg=f"Pinging {self.provider}/{self.model}...")

        # Capture the last error emitted during call attempts
        last_error = ""
        _orig_emit = self.emit_fn

        def _capture_emit(event, **kwargs):
            nonlocal last_error
            if event in ("llm_error", "fatal_error"):
                last_error = kwargs.get("msg", "")
            if _orig_emit:
                try:
                    _orig_emit(event, **kwargs)
                except Exception:
                    pass

        self.emit_fn = _capture_emit

        # For local/custom endpoints respond in <1s — use short timeout, no retry delay
        is_local = self.provider in ("ollama", "custom") or (
            self.base_url and ("localhost" in self.base_url or "127.0.0.1" in self.base_url)
        )
        ping_timeout  = 10 if is_local else 30   # seconds per attempt
        ping_retries  = 1 if is_local else 3      # attempts total
        retry_wait    = 0 if is_local else 8      # seconds between retries

        try:
            for attempt in range(ping_retries):
                result = self._call_with_timeout(
                    "Reply with exactly: OK",
                    task_type="ping",
                    timeout=ping_timeout,
                )
                if result:
                    self._emit("ping_ok", msg=f"LLM OK ({self.provider}/{self.model})")
                    return True, ""

                if attempt < ping_retries - 1 and retry_wait > 0:
                    self._emit("ping_wait", msg=f"Ping retry {attempt+1}/{ping_retries} — waiting {retry_wait}s")
                    time.sleep(retry_wait)
        finally:
            self.emit_fn = _orig_emit

        msg = last_error or f"LLM unreachable. Provider: {self.provider}, Model: {self.model}"
        self._emit("fatal_error", msg=msg)
        return False, msg

    def _call_with_timeout(self, prompt: str, task_type: str, timeout: int) -> Optional[str]:
        """
        Single-shot LLM call with a custom timeout (no retry).
        Used by ping() to avoid the default 180s timeout.
        """
        if self.provider == "gemini":
            return self._call_gemini_once(prompt, task_type, timeout)
        return self._call_openai_once(prompt, task_type, timeout)

    def _call_gemini_once(self, prompt: str, task_type: str, timeout: int) -> Optional[str]:
        if not self.api_key:
            return None
        max_tokens = TOKEN_BUDGETS.get(task_type, TOKEN_BUDGETS["default"])
        url = self.base_url.format(model=self.model) + f"?key={self.api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens},
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            self._emit("llm_error", msg=f"Gemini HTTP {e.code}: {body[:120]}")
            return None
        except Exception as e:
            self._emit("llm_error", msg=f"Gemini ping error: {str(e)[:100]}")
            return None

    def _call_openai_once(self, prompt: str, task_type: str, timeout: int) -> Optional[str]:
        if not self.base_url:
            self._emit("llm_error", msg="Base URL is empty.")
            return None
        max_tokens = TOKEN_BUDGETS.get(task_type, TOKEN_BUDGETS["default"])
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://scholarscout.app"
            headers["X-Title"] = "ScholarScout"
        try:
            req = urllib.request.Request(self.base_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")

            result = self._parse_response(raw)
            return result if result else None

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            self._emit("llm_error", msg=f"HTTP {e.code}: {body[:200]}")
            return None
        except Exception as e:
            self._emit("llm_error", msg=f"Ping error: {str(e)[:100]}")
            return None
