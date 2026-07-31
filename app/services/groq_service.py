"""
Groq AI Service: Streaming chat, completions, code assistance, and agent tools.

Sole AI provider for CodeMentor. Uses the official Groq Python SDK.

Supported models (configurable via GROQ_MODEL):
  - llama-3.3-70b-versatile
  - deepseek-r1-distill-llama-70b
  - qwen/qwen3-32b
  - mixtral-8x7b-32768
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncGenerator, Optional

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

# ─── Supported models ─────────────────────────────────────────────────────────
SUPPORTED_MODELS: dict[str, str] = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B Versatile",
    "deepseek-r1-distill-llama-70b": "DeepSeek R1 Distill 70B",
    "qwen/qwen3-32b": "Qwen3 32B",
    "mixtral-8x7b-32768": "Mixtral 8x7B",
}

MODEL_DESCRIPTIONS: dict[str, str] = {
    "llama-3.3-70b-versatile": "Most capable, versatile model for complex tasks",
    "deepseek-r1-distill-llama-70b": "Excellent reasoning and problem-solving",
    "qwen/qwen3-32b": "Strong multilingual coding and analysis",
    "mixtral-8x7b-32768": "Fast and efficient for everyday tasks",
}

SYSTEM_PROMPT = """You are CodeMentor AI, an expert coding assistant and system design mentor.
You help developers with:
- Writing, debugging, and refactoring code
- Explaining complex technical concepts
- System design and architecture
- Code review and optimization
- Generating tests, documentation, and SQL queries
- Creating flowcharts and diagrams (use mermaid syntax)
- Regex, APIs, unit tests, complexity analysis, and best practices

Always format your responses in well-structured Markdown.
Use syntax-highlighted code blocks with the correct language identifier.
When creating diagrams, use mermaid code blocks.
Be concise but thorough. Provide actionable, production-ready advice."""

# Shared async client (connection reuse)
_client = None
_client_lock = asyncio.Lock()


class GroqServiceError(Exception):
    """Base error for Groq service failures."""

    def __init__(self, message: str, *, user_message: str | None = None, status_code: int = 502):
        super().__init__(message)
        self.user_message = user_message or message
        self.status_code = status_code


def is_groq_configured() -> bool:
    """Return True when a usable Groq API key is present."""
    key = (settings.GROQ_API_KEY or "").strip()
    return bool(key) and key not in {"your-groq-api-key", "your_api_key", "gsk_xxx"}


def resolve_model(model: str | None = None) -> str:
    """Pick a valid model id, falling back to the configured default."""
    candidate = (model or settings.groq_model or "").strip()
    if candidate in SUPPORTED_MODELS:
        return candidate
    # Allow any non-empty model string Groq may support, else default
    if candidate:
        logger.warning(f"Model '{candidate}' not in known list; using as-is")
        return candidate
    return "llama-3.3-70b-versatile"


def list_models() -> list[dict[str, str]]:
    """Return model metadata for the API/UI."""
    return [
        {
            "id": model_id,
            "name": name,
            "description": MODEL_DESCRIPTIONS.get(model_id, "General purpose model"),
        }
        for model_id, name in SUPPORTED_MODELS.items()
    ]


async def _get_client():
    """Lazily create a shared AsyncGroq client."""
    global _client
    if _client is not None:
        return _client

    async with _client_lock:
        if _client is not None:
            return _client
        if not is_groq_configured():
            raise GroqServiceError(
                "GROQ_API_KEY is not configured",
                user_message="AI is not configured. Set GROQ_API_KEY on the server.",
                status_code=503,
            )
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise GroqServiceError(
                "groq package is not installed",
                user_message="AI service is unavailable (missing dependency).",
                status_code=503,
            ) from exc

        _client = AsyncGroq(api_key=settings.GROQ_API_KEY.strip())
        logger.info("Groq async client initialized")
        return _client


def _build_messages(
    message: str,
    *,
    history: list | None = None,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Assemble chat messages with system prompt and truncated history."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT}
    ]

    if history:
        for msg in history[-20:]:
            role = (msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)) or ""
            content = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)) or ""
            if role in ("user", "assistant") and str(content).strip():
                messages.append({"role": role, "content": str(content)})

    messages.append({"role": "user", "content": message})
    return messages


def _friendly_error(exc: Exception) -> str:
    """Map provider exceptions to user-friendly messages."""
    text = str(exc).lower()
    if "invalid api key" in text or "unauthorized" in text or "401" in text:
        return "Invalid Groq API key. Please check server configuration."
    if "rate limit" in text or "429" in text:
        return "AI rate limit reached. Please wait a moment and try again."
    if "timeout" in text or "timed out" in text:
        return "The AI request timed out. Please try again."
    if "model" in text and ("not found" in text or "does not exist" in text or "decommissioned" in text):
        return "The selected model is unavailable. Try another model."
    if "connection" in text or "network" in text:
        return "Network error while contacting the AI service."
    return "Something went wrong while generating a response. Please try again."


def _sse(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload)}\n\n"


def _token_chunk(content: str) -> str:
    return _sse({"choices": [{"delta": {"content": content}}]})


async def stream_chat(
    message: str,
    model: str | None = None,
    history: list | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response as Server-Sent Events.

    Yields lines like: data: {"choices":[{"delta":{"content":"..."}}]}
    Ends with: data: [DONE]
    """
    model_id = resolve_model(model)
    messages = _build_messages(message, history=history, system_prompt=system_prompt)

    if not is_groq_configured():
        logger.warning("Groq API key not configured. Using mock streaming response.")
        mock = _generate_mock_response(message)
        # Stream word-by-word for realistic UX
        for word in mock.split(" "):
            yield _token_chunk(word + " ")
            await asyncio.sleep(0.01)
        yield _sse("[DONE]")
        return

    try:
        client = await _get_client()
        stream = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta if chunk.choices else None
                content = getattr(delta, "content", None) if delta else None
                if content:
                    yield _token_chunk(content)
            except (IndexError, AttributeError):
                continue

        yield _sse("[DONE]")

    except asyncio.CancelledError:
        logger.info("Groq stream cancelled by client")
        raise
    except Exception as exc:
        logger.error(f"Groq streaming error: {exc}")
        yield _token_chunk(f"\n\n⚠️ {_friendly_error(exc)}")
        yield _sse("[DONE]")


@retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def chat_completion(
    message: str,
    model: str | None = None,
    history: list | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_json: bool = False,
) -> str:
    """
    Non-streaming chat completion.
    When response_json=True, asks the model to return JSON only.
    """
    model_id = resolve_model(model)
    messages = _build_messages(message, history=history, system_prompt=system_prompt)

    if not is_groq_configured():
        return _generate_mock_response(message)

    try:
        client = await _get_client()
        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if response_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise GroqServiceError(
                "Empty response from Groq",
                user_message="The AI returned an empty response. Please try again.",
            )
        return content

    except GroqServiceError:
        raise
    except Exception as exc:
        logger.error(f"Groq completion error: {exc}")
        raise GroqServiceError(str(exc), user_message=_friendly_error(exc)) from exc


async def chat_completion_with_usage(
    message: str,
    model: str | None = None,
    history: list | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Completion that also returns token usage metadata."""
    model_id = resolve_model(model)
    messages = _build_messages(message, history=history, system_prompt=system_prompt)

    if not is_groq_configured():
        text = _generate_mock_response(message)
        return {
            "content": text,
            "model": model_id,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    try:
        client = await _get_client()
        response = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        content = response.choices[0].message.content if response.choices else ""
        usage = getattr(response, "usage", None)
        return {
            "content": content or "",
            "model": model_id,
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        }
    except Exception as exc:
        logger.error(f"Groq completion+usage error: {exc}")
        raise GroqServiceError(str(exc), user_message=_friendly_error(exc)) from exc


async def agent_analyze(
    query: str,
    files: list | None = None,
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Repository-aware agent streaming analysis."""
    agent_system = """You are CodeMentor Agent, an advanced AI coding assistant.
You have access to the user's codebase and can:
- Understand repository structure and architecture
- Read and analyze multiple files
- Suggest edits and improvements
- Generate components, APIs, and SQL
- Fix bugs and detect vulnerabilities
- Improve performance
- Review code and generate git commit messages
- Create PR summaries

When analyzing code, be specific about file paths and line numbers.
Format responses in well-structured Markdown with syntax-highlighted code blocks."""

    file_context = ""
    if files:
        file_context = "\n\n## Repository Context\n\n"
        for f in files[:20]:
            path = f.get("path", "unknown") if isinstance(f, dict) else "unknown"
            content = f.get("content", "") if isinstance(f, dict) else ""
            if len(content) > 5000:
                content = content[:5000] + "\n... (truncated)"
            file_context += f"### {path}\n```\n{content}\n```\n\n"

    async for chunk in stream_chat(
        message=f"{query}{file_context}",
        model=model,
        system_prompt=agent_system,
        temperature=0.3,
        max_tokens=8192,
    ):
        yield chunk


async def json_completion(
    prompt: str,
    *,
    system_prompt: str,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 3000,
) -> dict:
    """
    Request a JSON object response and parse it.
    Falls back to extracting a JSON object from free text if needed.
    """
    raw = await chat_completion(
        message=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_json=True,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
        raise GroqServiceError(
            "Failed to parse JSON from model response",
            user_message="AI returned an unexpected format. Please try again.",
        )


def _generate_mock_response(message: str) -> str:
    """Mock response used when GROQ_API_KEY is missing (local/dev)."""
    msg_lower = (message or "").lower()

    if "hello" in msg_lower or "hi" in msg_lower:
        return """Hello! I'm **CodeMentor AI**, your coding assistant.

I can help you with:
- **Writing code** in Python, JavaScript, TypeScript, Java, C++, and more
- **Debugging** and fixing errors
- **Refactoring** for better readability
- **System design** and architecture
- **Code review** and optimization

> **Note:** The Groq API key is not configured. Set `GROQ_API_KEY` in your backend `.env` file to enable full AI capabilities.

What would you like to work on today?"""

    if "explain" in msg_lower:
        return """I'd be happy to explain! However, the Groq API key is not configured yet.

To enable full AI responses:

1. Get a free API key from [console.groq.com](https://console.groq.com)
2. Add it to your backend `.env` file:
   ```
   GROQ_API_KEY=your-api-key-here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
3. Restart the backend server

Once configured, I'll provide detailed explanations, code analysis, and more."""

    return f"""I received your message: "{(message or '')[:100]}"

> **Note:** The Groq API key is not configured. To enable full AI capabilities:
> 1. Get a free API key from [console.groq.com](https://console.groq.com)
> 2. Add `GROQ_API_KEY=your-key` to the backend `.env` file
> 3. Restart the backend

I'm ready to help with coding, debugging, system design, and more once configured!"""
