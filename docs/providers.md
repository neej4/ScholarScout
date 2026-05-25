# LLM providers

ScholarScout works with 6 LLM providers. You only need one.

## Gemini (recommended)

- Cost: Free (15 requests/minute)
- Speed: Fast
- Get key: https://aistudio.google.com/app/apikey
- Model: `gemini-2.0-flash`

Best for most users. Free tier is generous enough for daily use.

## Groq

- Cost: Free tier available
- Speed: Very fast (specialized inference hardware)
- Get key: https://console.groq.com/keys
- Model: `llama-3.3-70b-versatile`

Good alternative if Gemini is rate-limited.

## Ollama (local)

- Cost: Free (runs on your machine)
- Speed: Depends on your GPU
- Setup: https://ollama.com/download
- Model: `llama3.2`

No internet needed after model download. Full privacy.

## OpenRouter

- Cost: Pay per token
- Speed: Varies by model
- Get key: https://openrouter.ai/keys
- Model: `deepseek/deepseek-chat`

Access to 100+ models through one API.

## OpenAI

- Cost: Pay per token
- Speed: Fast
- Get key: https://platform.openai.com/api-keys
- Model: `gpt-4o-mini`

## Custom endpoint

Any OpenAI-compatible API. Works with local proxies (9router, LM Studio, vLLM, etc).

- Base URL: your endpoint (e.g., `http://localhost:20128/v1`)
- Model: whatever your proxy serves
- API key: optional for local endpoints

ScholarScout handles streaming responses even when `stream: false` is sent — compatible with proxies that always stream.
