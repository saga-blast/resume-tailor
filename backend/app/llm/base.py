from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

MAX_STRUCTURED_ATTEMPTS = 2


class StructuredCallError(Exception):
    """A failed tool-call attempt that knows what to tell the model on retry.

    Distinguishes failure modes that need different corrective feedback -- e.g.
    a truncated response needs "be more concise", not "match the schema
    exactly", which is what a generic exception would get from the retry loop.
    """

    def __init__(self, message: str, *, correction_hint: str) -> None:
        super().__init__(message)
        self.correction_hint = correction_hint


class LLMProvider(ABC):
    async def extract_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        tool_name: str,
        tool_description: str,
    ) -> T:
        """Run a forced tool-use call and return the validated structured result.

        Retries once with the validation error fed back to the model on failure --
        open-weight models in particular sometimes rename/omit schema fields (e.g.
        writing `dateRange` when the schema says `dates`) even under forced tool
        use, and telling the model exactly what it got wrong reliably self-corrects.
        """
        correction: str | None = None
        last_error: Exception | None = None
        for _ in range(MAX_STRUCTURED_ATTEMPTS):
            try:
                return await self._attempt_tool_call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    tool_name=tool_name,
                    tool_description=tool_description,
                    correction=correction,
                )
            except Exception as exc:  # noqa: BLE001 -- deliberately broad: any failure triggers a retry
                last_error = exc
                hint = getattr(exc, "correction_hint", None)
                correction = hint or (
                    f"Your previous attempt failed validation: {exc}. Call the tool again, using "
                    "exactly the property names defined in its schema -- do not rename, add, or "
                    "omit any fields."
                )
        assert last_error is not None
        raise last_error

    @abstractmethod
    async def _attempt_tool_call(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        tool_name: str,
        tool_description: str,
        correction: str | None,
    ) -> T:
        """A single forced tool-use attempt. `correction`, if set, is fed back as
        an extra message describing why the previous attempt was rejected."""

    @abstractmethod
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Run a freeform completion (e.g. for generating LaTeX source)."""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List model IDs this API key actually has access to right now.

        Model lineups shift over time and a hardcoded default can go stale --
        this lets onboarding show real, current options instead of guessing.
        """
