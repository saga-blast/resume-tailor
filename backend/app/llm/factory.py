from sqlmodel import Session, select

from app.crypto import decrypt_secret
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.groq_provider import GroqProvider
from app.models.llm_config import LLMProviderConfig


class LLMNotConfiguredError(Exception):
    pass


def build_provider(provider: str, api_key: str, model: str) -> LLMProvider:
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    if provider == "groq":
        return GroqProvider(api_key=api_key, model=model)
    raise LLMNotConfiguredError(f"Unsupported LLM provider: {provider}")


def get_llm_provider(session: Session, user_id: int) -> LLMProvider:
    config = session.exec(
        select(LLMProviderConfig).where(
            LLMProviderConfig.user_id == user_id,
            LLMProviderConfig.is_active.is_(True),
        )
    ).first()
    if not config:
        raise LLMNotConfiguredError("No active LLM provider configured for this user")

    api_key = decrypt_secret(config.encrypted_api_key)
    return build_provider(config.provider, api_key, config.model)
