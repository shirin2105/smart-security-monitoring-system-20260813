from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def empty_detector():
    """Deterministic detector for worker tests that do not exercise model loading."""
    return SimpleNamespace(detect=lambda _frame: ([], 0.0))


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
