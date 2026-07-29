"""
Execution provider contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    execution_time: float
    memory: int | None
    exit_code: int | None
    status: str


class ExecutionProvider(ABC):
    @abstractmethod
    async def execute(self, language: str, code: str, stdin: str = "") -> ExecutionResult:
        """Run source code through an isolated execution provider."""

