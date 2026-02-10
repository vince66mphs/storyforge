"""Unit test fixtures — mock session, mock ollama client."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_session():
    """A mock AsyncSession for unit tests that don't need a real DB."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_ollama_client():
    """A mock ollama AsyncClient."""
    client = AsyncMock()
    # Default chat response
    response = MagicMock()
    response.message.content = "Generated text content"
    client.chat.return_value = response

    # Default embed response
    embed_response = MagicMock()
    embed_response.embeddings = [[0.1] * 768]
    client.embed.return_value = embed_response

    return client
