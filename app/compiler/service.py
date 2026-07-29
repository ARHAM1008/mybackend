"""
Compiler orchestration service.

Selects the execution provider based on the COMPILER_PROVIDER environment
variable.  Set to "piston" to use the (now whitelist-only) Piston API, or
leave unset / set to "local" to run code directly on the server.
"""

from app.compiler.providers.base import ExecutionProvider, ExecutionResult
from app.compiler.providers.local import LocalExecutionProvider
from app.compiler.providers.piston import PistonExecutionProvider
from app.core.config import settings

SUPPORTED_LANGUAGES = {"python", "c", "cpp", "java", "javascript"}


def _default_provider() -> ExecutionProvider:
    provider_name = settings.COMPILER_PROVIDER.strip().lower()
    if provider_name == "piston":
        return PistonExecutionProvider()
    return LocalExecutionProvider()


class CompilerService:
    def __init__(self, provider: ExecutionProvider | None = None):
        self.provider = provider or _default_provider()

    async def run(self, language: str, code: str, stdin: str = "") -> ExecutionResult:
        if language not in SUPPORTED_LANGUAGES:
            return ExecutionResult("", "Unsupported language.", 0, None, None, "unsupported_language")
        return await self.provider.execute(language=language, code=code, stdin=stdin)

