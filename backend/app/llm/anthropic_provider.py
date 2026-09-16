from anthropic import AsyncAnthropic

from app.llm.base import LLMProvider, StructuredCallError, T

# Generous on purpose: a detailed JD can extract into 70+ discrete requirements,
# which genuinely needs several thousand output tokens of JSON to hold without
# truncating mid-array (seen in practice with a long Kubernetes-heavy JD).
MAX_TOKENS = 8192


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def _attempt_tool_call(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        tool_name: str,
        tool_description: str,
        correction: str | None,
        max_tokens: int | None,
    ) -> T:
        effective_max_tokens = max_tokens or MAX_TOKENS
        messages = [{"role": "user", "content": user_prompt}]
        if correction:
            messages.append({"role": "user", "content": correction})

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=effective_max_tokens,
            system=system_prompt,
            messages=messages,
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": schema.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
        if response.stop_reason == "max_tokens":
            raise StructuredCallError(
                f"Response was truncated at the {effective_max_tokens}-token limit before completing valid JSON.",
                correction_hint=(
                    f"Your previous response was cut off before completing valid JSON because it hit "
                    f"the {effective_max_tokens}-token limit. Provide a more concise answer this time -- "
                    "merge closely related or overlapping items -- so the complete JSON fits within the limit."
                ),
            )
        for block in response.content:
            if block.type == "tool_use":
                return schema.model_validate(block.input)
        raise ValueError("Model response did not contain a tool_use block")

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    async def list_models(self) -> list[str]:
        response = await self._client.models.list()
        return [m.id for m in response.data]
