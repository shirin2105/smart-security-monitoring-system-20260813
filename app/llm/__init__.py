"""LLM enrichment adapters (OpenAI-compatible endpoints)."""

from app.llm.adapter import LLMAdapter, create_llm_adapter

__all__ = ["LLMAdapter", "create_llm_adapter"]
