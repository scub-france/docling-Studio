"""Tests for the embedding microservice API."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

import main

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _mock_model() -> Iterator[None]:
    """Inject a mock SentenceTransformer model for all tests."""
    mock = MagicMock()
    mock.get_sentence_embedding_dimension.return_value = 3
    mock.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    main.model = mock
    yield
    main.model = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


class TestEmbed:
    def test_embed_returns_vectors(self, client: TestClient) -> None:
        resp = client.post("/embed", json={"texts": ["hello", "world"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["embeddings"]) == 2
        assert data["dimension"] == 3
        assert data["model"] == main.MODEL_NAME

    def test_embed_empty_texts_rejected(self, client: TestClient) -> None:
        resp = client.post("/embed", json={"texts": []})
        assert resp.status_code == 422

    def test_embed_missing_texts(self, client: TestClient) -> None:
        resp = client.post("/embed", json={})
        assert resp.status_code == 422

    def test_embed_model_not_loaded(self, client: TestClient) -> None:
        main.model = None
        resp = client.post("/embed", json={"texts": ["test"]})
        assert resp.status_code == 503


class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["dimension"] == 3

    def test_health_model_not_loaded(self, client: TestClient) -> None:
        main.model = None
        resp = client.get("/health")
        assert resp.status_code == 503
