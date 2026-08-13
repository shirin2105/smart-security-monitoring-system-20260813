from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

root_dir = Path(__file__).resolve().parents[1]
backend_dir = root_dir / "back-end"
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

try:
    import app
    backend_app = backend_dir / "app"
    if hasattr(app, "__path__") and str(backend_app) not in app.__path__:
        app.__path__.append(str(backend_app))
    for sub in ("api", "services", "db"):
        sub_backend = str(backend_app / sub)
        try:
            mod = __import__(f"app.{sub}", fromlist=[sub])
            if hasattr(mod, "__path__") and sub_backend not in mod.__path__:
                mod.__path__.append(sub_backend)
        except ImportError:
            pass
except ImportError:
    pass



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
