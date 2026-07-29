"""
Local execution provider.

Runs source code directly on the server using subprocesses with
timeouts and resource limits. Replaces the Piston API for environments
where the public Piston endpoint is unavailable.
"""

import asyncio
import os
import platform
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from app.compiler.providers.base import ExecutionProvider, ExecutionResult


# ── language → (command, extension, compile_command) ──────────────────────
# compile_command may be None if no compilation step is needed.
LANGUAGE_CONFIG: dict[str, tuple[str, str, str | None]] = {
    "python":     ("python",     ".py",  None),
    "javascript": ("node",       ".js",  None),
    "c":          (None,         ".c",   "gcc {source} -o {binary} -Wall -O2 -lm"),
    "cpp":        (None,         ".cpp", "g++ {source} -o {binary} -Wall -O2 -lm"),
    "java":       (None,         ".java", "javac {source}"),
}

# On Windows the executable names differ
if platform.system() == "Windows":
    LANGUAGE_CONFIG["python"] = ("python", ".py", None)
else:
    LANGUAGE_CONFIG["python"] = ("python3", ".py", None)


class LocalExecutionProvider(ExecutionProvider):
    """
    Executes code by writing it to a temporary file and running it in a
    subprocess.  Compiles C/C++/Java before running.
    """

    def __init__(
        self,
        timeout_seconds: int = 10,
        max_output_bytes: int = 1_048_576,  # 1 MiB
        work_dir: str | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.work_dir = work_dir or tempfile.gettempdir()

    async def execute(self, language: str, code: str, stdin: str = "") -> ExecutionResult:
        if language not in LANGUAGE_CONFIG:
            return ExecutionResult("", f"Unsupported language '{language}'.", 0, None, None, "unsupported_language")

        return await asyncio.to_thread(self._execute_sync, language, code, stdin)

    # ------------------------------------------------------------------
    # Synchronous helper (runs in thread pool to avoid blocking the event loop)
    # ------------------------------------------------------------------
    def _execute_sync(self, language: str, code: str, stdin: str) -> ExecutionResult:
        runtime_cmd, extension, compile_template = LANGUAGE_CONFIG[language]
        is_windows = platform.system() == "Windows"
        session_id = uuid.uuid4().hex[:12]
        work_dir = Path(self.work_dir) / f"cm_exec_{session_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()

        def _quote(p: Path) -> str:
            """Quote a path for the current platform."""
            s = str(p)
            if is_windows:
                # Windows cmd.exe uses double quotes
                return f'"{s}"'
            return shlex.quote(s)

        try:
            # ── Write source file ────────────────────────────────────────
            if language == "java":
                # Java requires the filename to match the public class
                source_name = self._infer_java_class(code) or "Main"
                source_path = work_dir / f"{source_name}{extension}"
            else:
                source_path = work_dir / f"main{extension}"

            source_path.write_text(code, encoding="utf-8")

            # ── Compile (if needed) ──────────────────────────────────────
            binary_path = work_dir / "a.out"
            if compile_template:
                compile_cmd = compile_template.format(
                    source=_quote(source_path),
                    binary=_quote(binary_path),
                )
                try:
                    proc = subprocess.run(
                        compile_cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        cwd=str(work_dir),
                        shell=True,  # always use shell for compile (gcc/g++/javac)
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        "", "Compilation timed out.",
                        self._elapsed(started), None, None, "timeout",
                    )

                if proc.returncode != 0:
                    return ExecutionResult(
                        "", proc.stderr or "Compilation failed.",
                        self._elapsed(started), None, proc.returncode, "error",
                    )

            # ── Determine run command ────────────────────────────────────
            if language == "java":
                # java <classname>  (no .class extension)
                class_name = source_path.stem  # filename without .java
                run_cmd = f"java -cp {_quote(work_dir)} {class_name}"
            elif language in ("c", "cpp"):
                run_cmd = _quote(binary_path)
            else:
                # python / javascript – runtime_cmd is set
                run_cmd = f"{runtime_cmd} {_quote(source_path)}"

            # ── Execute ──────────────────────────────────────────────────
            try:
                proc = subprocess.run(
                    run_cmd,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=str(work_dir),
                    shell=True,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    "", f"Execution timed out after {self.timeout_seconds}s.",
                    self._elapsed(started), None, None, "timeout",
                )

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            exit_code = proc.returncode
            status = "success" if exit_code == 0 and not stderr else "error"

            # Truncate output if too large
            if len(stdout) > self.max_output_bytes:
                stdout = stdout[: self.max_output_bytes] + "\n... (truncated)"
            if len(stderr) > self.max_output_bytes:
                stderr = stderr[: self.max_output_bytes] + "\n... (truncated)"

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                execution_time=self._elapsed(started),
                memory=None,
                exit_code=exit_code,
                status=status,
            )

        except FileNotFoundError:
            return ExecutionResult(
                "", f"Runtime '{runtime_cmd}' not found. Is it installed?",
                self._elapsed(started), None, None, "runtime_missing",
            )
        except Exception as exc:
            return ExecutionResult(
                "", f"Execution error: {exc}",
                self._elapsed(started), None, None, "internal_error",
            )
        finally:
            # Cleanup temp files
            self._cleanup(work_dir)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _infer_java_class(code: str) -> str | None:
        """Extract the public class name from Java source."""
        import re
        match = re.search(r'\bpublic\s+class\s+(\w+)', code)
        return match.group(1) if match else None

    @staticmethod
    def _elapsed(started: float) -> float:
        return round(time.perf_counter() - started, 3)

    @staticmethod
    def _cleanup(path: Path) -> None:
        """Remove temporary directory."""
        try:
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass