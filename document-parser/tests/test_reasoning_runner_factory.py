"""`build_reasoning_runner`: Ollama only, any other provider keeps Ask off."""

from __future__ import annotations

import logging
from dataclasses import replace
from unittest.mock import patch

import pytest

from bootstrap import factories
from domain.app_config import ReasoningConfig
from infra.settings import settings

_CONFIG = ReasoningConfig(
    enabled=True, ollama_host="http://ollama:11434", model_id="m", max_iterations=3
)


@pytest.fixture
def usable_deps():
    with patch.object(factories, "has_usable_deps", return_value=True):
        yield


def _build_with_provider(monkeypatch, provider_type: str):
    monkeypatch.setattr(factories, "settings", replace(settings, llm_provider_type=provider_type))
    return factories.build_reasoning_runner(_CONFIG)


def test_a_provider_other_than_ollama_disables_the_runner(monkeypatch, usable_deps, caplog):
    with caplog.at_level(logging.WARNING, logger=factories.__name__):
        runner = _build_with_provider(monkeypatch, "openai")

    assert runner is None
    assert "Unsupported LLM_PROVIDER_TYPE=openai" in caplog.text


def test_ollama_builds_a_runner_on_the_configured_host(monkeypatch, usable_deps):
    with patch.object(factories, "DoclingAgentReasoningRunner") as runner_class:
        runner = _build_with_provider(monkeypatch, "ollama")

    assert runner is runner_class.return_value
    provider = runner_class.call_args.kwargs["provider"]
    assert (provider.host, provider.default_model_id) == ("http://ollama:11434", "m")
