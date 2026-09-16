import json

from groq import AsyncGroq

from app.llm.base import LLMProvider, StructuredCallError, T

# Generous on purpose: a detailed JD can extract into 70+ discrete requirements,
# which genuinely needs several thousand output tokens of JSON to hold without
# truncating mid-array (seen in practice with a long Kubernetes-heavy JD).
MAX_TOKENS = 8192


class GroqProvider(LLMProvider):
    """Groq's chat completions API is OpenAI-compatible, including tool use --
    the most standardized/well-documented tool-calling shape across providers."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if correction:
            messages.append({"role": "user", "content": correction})

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=effective_max_tokens,
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": schema.model_json_schema(),
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise StructuredCallError(
                f"Response was truncated at the {effective_max_tokens}-token limit before completing valid JSON.",
                correction_hint=(
                    f"Your previous response was cut off before completing valid JSON because it hit "
                    f"the {effective_max_tokens}-token limit. Provide a more concise answer this time -- "
                    "merge closely related or overlapping items -- so the complete JSON fits within the limit."
                ),
            )
        message = choice.message
        if not message.tool_calls:
            raise ValueError("Model response did not contain a tool call")
        arguments = json.loads(message.tool_calls[0].function.arguments)
        return schema.model_validate(arguments)

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    async def list_models(self) -> list[str]:
        response = await self._client.models.list()
        return [m.id for m in response.data]
