"""
Piston execution provider.

This adapter sends code to the Piston API instead of invoking local shells.
"""

import asyncio
import json
import time
from urllib import error, request

from app.compiler.providers.base import ExecutionProvider, ExecutionResult


PISTON_ENDPOINT = "https://emkc.org/api/v2/piston/execute"

RUNTIME_MAP = {
    "python": ("python", "3.10.0", "main.py"),
    "c": ("c", "10.2.0", "main.c"),
    "cpp": ("c++", "10.2.0", "main.cpp"),
    "java": ("java", "15.0.2", "Main.java"),
    "javascript": ("javascript", "18.15.0", "main.js"),
}


class PistonExecutionProvider(ExecutionProvider):
    def __init__(self, endpoint: str = PISTON_ENDPOINT, timeout_seconds: int = 15):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    async def execute(self, language: str, code: str, stdin: str = "") -> ExecutionResult:
        if language not in RUNTIME_MAP:
            return ExecutionResult("", "Unsupported language.", 0, None, None, "unsupported_language")

        return await asyncio.to_thread(self._execute_sync, language, code, stdin)

    def _execute_sync(self, language: str, code: str, stdin: str) -> ExecutionResult:
        runtime, version, filename = RUNTIME_MAP[language]
        payload = {
            "language": runtime,
            "version": version,
            "files": [{"name": filename, "content": code}],
            "stdin": stdin,
        }

        started = time.perf_counter()
        req = request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            message = "The execution provider rejected this request."
            try:
                body = json.loads(exc.read().decode("utf-8"))
                message = body.get("message", message)
            except Exception:
                pass
            return ExecutionResult("", message, self._elapsed(started), None, None, "provider_error")
        except Exception:
            return ExecutionResult("", "Execution provider is unavailable.", self._elapsed(started), None, None, "network_error")

        run = data.get("run", {})
        compile_step = data.get("compile") or {}
        stdout = run.get("stdout") or ""
        stderr = "\n".join(part for part in [compile_step.get("stderr") or "", run.get("stderr") or ""] if part)
        exit_code = run.get("code")
        status = "success" if exit_code == 0 and not stderr else "error"

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            execution_time=self._elapsed(started),
            memory=None,
            exit_code=exit_code,
            status=status,
        )

    @staticmethod
    def _elapsed(started: float) -> float:
        return round(time.perf_counter() - started, 3)

