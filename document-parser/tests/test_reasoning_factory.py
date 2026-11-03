"""`build_reasoning_runner` — the composition root's reasoning wiring.

#audit-04: Ollama is the only backend, so the factory no longer reads a
provider knob (`LLM_PROVIDER_TYPE`): an enabled config with its deps present
always gets a runner over an `OllamaProvider`.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from bootstrap.factories import build_reasoning_runner
from domain.app_config import ReasoningConfig
from infra.llm.ollama_provider import OllamaProvider

_ENABLED = ReasoningConfig(
    enabled=True, ollama_host="http://ollama:11434/", model_id="m:7b", max_iterations=4
)


def test_an_enabled_config_gets_an_ollama_runner(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_TYPE", "openai")  # ignored now
    with patch("bootstrap.factories.deps_present", return_value=True):
        runner = build_reasoning_runner(_ENABLED)
    assert runner is not None
    assert isinstance(runner._provider, OllamaProvider)
    assert runner._provider.host == "http://ollama:11434"
    assert runner._provider.default_model_id == "m:7b"


def test_a_disabled_config_gets_none():
    assert build_reasoning_runner(replace(_ENABLED, enabled=False)) is None


def test_missing_deps_get_none():
    with patch("bootstrap.factories.deps_present", return_value=False):
        assert build_reasoning_runner(_ENABLED) is None
