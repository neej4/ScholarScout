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
    "idea_generation": 1500,
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
            self._emit("llm_error", msg="Gemini API Key tidak ditemukan! Dapatkan di https://aistudio.google.com/app/apikey")
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
                    self._emit("llm_error", msg="Gemini API Key invalid. Dapatkan di https://aistudio.google.com/app/apikey")
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
        if not self.api_key and self.provider != "ollama":
            provider_info = PROVIDERS.get(self.provider, {})
            docs = provider_info.get("docs", "")
            self._emit("llm_error", msg=f"API Key tidak ditemukan! Dapatkan di {docs}")
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
                    data = json.loads(resp.read())
                    text = data["choices"][0]["message"]["content"].strip()
                    
                    # Track tokens
                    usage = data.get("usage", {})
                    self.total_input_tokens += usage.get("prompt_tokens", 0)
                    self.total_output_tokens += usage.get("completion_tokens", 0)
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

    def ping(self) -> bool:
        """Validates the LLM API is reachable."""
        if not self.api_key and self.provider != "ollama":
            provider_info = PROVIDERS.get(self.provider, {})
            self._emit("fatal_error", msg=f"API Key kosong! Dapatkan di {provider_info.get('docs', 'config.yaml')}")
            return False

        self._emit("ping_start", msg=f"Pinging {self.provider}/{self.model}...")

        for attempt in range(3):
            try:
                result = self.call("Reply with exactly: OK", retries=0, task_type="ping")
                if result:
                    self._emit("ping_ok", msg=f"LLM OK ({self.provider}/{self.model})")
                    return True
            except Exception:
                pass
            
            if attempt < 2:
                wait = 8 * (attempt + 1)
                self._emit("ping_wait", msg=f"Ping retry {attempt+1}/3 — waiting {wait}s")
                time.sleep(wait)

        self._emit("fatal_error", msg=f"LLM unreachable. Provider: {self.provider}, Model: {self.model}")
        return False
