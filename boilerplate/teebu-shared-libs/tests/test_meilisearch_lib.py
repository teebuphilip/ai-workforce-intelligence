"""
test_meilisearch_lib.py — Tests for MeiliSearch full-text search adapter
=========================================================================

Tests validate:
- MeiliSearchConfig: reads from arg, env, default host, not configured without key
- create_index: creates with primary_key, applies settings, error when unconfigured
- add_documents: posts documents, skips empty list, error when unconfigured
- search: passes query, filter, limit, offset
- update_document: upserts single document
- delete_document: deletes by id
- delete_index: deletes index
- meilisearch_health_check: disabled / enabled / error states
- load_meilisearch_lib: factory creates configured instance

All tests mock meilisearch.Client — no real MeiliSearch server required.

Run:
    pytest tests/test_meilisearch_lib.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from meilisearch_lib import MeiliSearchLib, MeiliSearchConfig, load_meilisearch_lib


# ============================================================
# HELPERS
# ============================================================

def _make_lib(api_key="fake_key", host="http://localhost:7700"):
    config = MeiliSearchConfig(api_key=api_key, host=host)
    return MeiliSearchLib(config)


def _make_mock_client():
    """Build a fully mocked meilisearch.Client."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_client.index.return_value = mock_index
    mock_client.create_index.return_value = {"taskUid": 1}
    mock_client.health.return_value = {"status": "available"}
    mock_index.add_documents.return_value = {"taskUid": 2}
    mock_index.update_documents.return_value = {"taskUid": 3}
    mock_index.delete_document.return_value = {"taskUid": 4}
    mock_index.delete.return_value = {"taskUid": 5}
    mock_index.search.return_value = {"hits": [], "estimatedTotalHits": 0}
    return mock_client, mock_index


# ============================================================
# TEST: MeiliSearchConfig
# ============================================================

class TestMeiliSearchConfig:

    def test_reads_api_key_from_arg(self):
        """Config reads API key from constructor argument."""
        config = MeiliSearchConfig(api_key="my_key")
        assert config.api_key == "my_key"
        assert config.is_configured is True

    def test_reads_api_key_from_env(self, monkeypatch):
        """Config reads API key from MEILISEARCH_API_KEY env var."""
        monkeypatch.setenv("MEILISEARCH_API_KEY", "env_key")
        config = MeiliSearchConfig()
        assert config.api_key == "env_key"
        assert config.is_configured is True

    def test_not_configured_without_key(self, monkeypatch):
        """Config reports not configured when no key is set."""
        monkeypatch.delenv("MEILISEARCH_API_KEY", raising=False)
        config = MeiliSearchConfig()
        assert config.is_configured is False

    def test_default_host(self, monkeypatch):
        """Config defaults host to localhost:7700 when MEILISEARCH_HOST not set."""
        monkeypatch.delenv("MEILISEARCH_HOST", raising=False)
        config = MeiliSearchConfig(api_key="k")
        assert config.host == "http://localhost:7700"

    def test_reads_host_from_env(self, monkeypatch):
        """Config reads host from MEILISEARCH_HOST env var."""
        monkeypatch.setenv("MEILISEARCH_HOST", "https://search.example.com")
        config = MeiliSearchConfig(api_key="k")
        assert config.host == "https://search.example.com"

    def test_arg_takes_precedence_over_env(self, monkeypatch):
        """Explicit API key takes precedence over environment variable."""
        monkeypatch.setenv("MEILISEARCH_API_KEY", "env_key")
        config = MeiliSearchConfig(api_key="explicit_key")
        assert config.api_key == "explicit_key"


# ============================================================
# TEST: create_index
# ============================================================

class TestCreateIndex:

    def test_creates_index_with_primary_key(self):
        """create_index calls client.create_index with primaryKey."""
        lib = _make_lib()
        mock_client, _ = _make_mock_client()

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.create_index("listings", primary_key="id")

        assert result["success"] is True
        mock_client.create_index.assert_called_once_with("listings", {"primaryKey": "id"})

    def test_applies_settings_when_provided(self):
        """create_index calls update_settings when settings dict is given."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()
        settings = {"filterableAttributes": ["category", "status"]}

        with patch("meilisearch.Client", return_value=mock_client):
            lib.create_index("listings", settings=settings)

        mock_index.update_settings.assert_called_once_with(settings)

    def test_returns_error_when_unconfigured(self):
        """create_index returns error dict when API key is missing."""
        lib = _make_lib(api_key=None)
        result = lib.create_index("listings")
        assert result["success"] is False
        assert "MEILISEARCH_API_KEY" in result["error"]

    def test_returns_error_on_exception(self):
        """create_index returns error dict when SDK raises."""
        lib = _make_lib()
        mock_client, _ = _make_mock_client()
        mock_client.create_index.side_effect = Exception("connection refused")

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.create_index("listings")

        assert result["success"] is False
        assert "connection refused" in result["error"]


# ============================================================
# TEST: add_documents
# ============================================================

class TestAddDocuments:

    def test_posts_documents_to_index(self):
        """add_documents calls index.add_documents with the provided list."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()
        docs = [{"id": 1, "title": "Lamp"}, {"id": 2, "title": "Chair"}]

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.add_documents("listings", docs)

        assert result["success"] is True
        mock_index.add_documents.assert_called_once_with(docs)

    def test_skips_empty_document_list(self):
        """add_documents returns success without calling SDK for empty list."""
        lib = _make_lib()
        with patch("meilisearch.Client") as mock_cls:
            result = lib.add_documents("listings", [])

        assert result["success"] is True
        mock_cls.assert_not_called()

    def test_returns_error_when_unconfigured(self):
        """add_documents returns error when API key is missing."""
        lib = _make_lib(api_key=None)
        result = lib.add_documents("listings", [{"id": 1}])
        assert result["success"] is False


# ============================================================
# TEST: search
# ============================================================

class TestSearch:

    def test_returns_search_hits(self):
        """search passes query to index.search and returns hits."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()
        mock_index.search.return_value = {
            "hits": [{"id": 1, "title": "Vintage lamp"}],
            "estimatedTotalHits": 1,
        }

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.search("listings", "lamp")

        assert result["success"] is True
        assert len(result["data"]["hits"]) == 1
        mock_index.search.assert_called_once_with("lamp", {"limit": 20, "offset": 0})

    def test_passes_filter_param(self):
        """search includes filter in opt_params when provided."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()

        with patch("meilisearch.Client", return_value=mock_client):
            lib.search("listings", "table", filters="status = 'active'")

        call_args = mock_index.search.call_args[0]
        assert call_args[1]["filter"] == "status = 'active'"

    def test_passes_limit_and_offset(self):
        """search passes custom limit and offset to SDK."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()

        with patch("meilisearch.Client", return_value=mock_client):
            lib.search("listings", "sofa", limit=5, offset=10)

        call_args = mock_index.search.call_args[0]
        assert call_args[1]["limit"] == 5
        assert call_args[1]["offset"] == 10

    def test_returns_error_when_unconfigured(self):
        """search returns error when API key is missing."""
        lib = _make_lib(api_key=None)
        result = lib.search("listings", "lamp")
        assert result["success"] is False


# ============================================================
# TEST: update_document
# ============================================================

class TestUpdateDocument:

    def test_upserts_single_document(self):
        """update_document calls index.update_documents with a one-item list."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()
        doc = {"id": 5, "title": "Updated lamp", "price_usd": 30.0}

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.update_document("listings", doc)

        assert result["success"] is True
        mock_index.update_documents.assert_called_once_with([doc])

    def test_returns_error_when_unconfigured(self):
        """update_document returns error when unconfigured."""
        lib = _make_lib(api_key=None)
        result = lib.update_document("listings", {"id": 1})
        assert result["success"] is False


# ============================================================
# TEST: delete_document
# ============================================================

class TestDeleteDocument:

    def test_deletes_document_by_id(self):
        """delete_document calls index.delete_document with the document id."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.delete_document("listings", 42)

        assert result["success"] is True
        mock_index.delete_document.assert_called_once_with(42)

    def test_returns_error_when_unconfigured(self):
        """delete_document returns error when unconfigured."""
        lib = _make_lib(api_key=None)
        result = lib.delete_document("listings", 1)
        assert result["success"] is False


# ============================================================
# TEST: delete_index
# ============================================================

class TestDeleteIndex:

    def test_deletes_index(self):
        """delete_index calls index.delete()."""
        lib = _make_lib()
        mock_client, mock_index = _make_mock_client()

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.delete_index("listings")

        assert result["success"] is True
        mock_index.delete.assert_called_once()


# ============================================================
# TEST: meilisearch_health_check
# ============================================================

class TestMeiliSearchHealthCheck:

    def test_returns_disabled_without_key(self, monkeypatch):
        """Health check reports disabled when API key is not set."""
        monkeypatch.delenv("MEILISEARCH_API_KEY", raising=False)
        lib = _make_lib(api_key=None)
        result = lib.meilisearch_health_check()
        assert result["search"] == "disabled"
        assert "fix" in result

    def test_returns_enabled_when_api_available(self):
        """Health check reports enabled when API key is set and server is reachable."""
        lib = _make_lib()
        mock_client, _ = _make_mock_client()

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.meilisearch_health_check()

        assert result["search"] == "enabled"
        assert result["api_reachable"] is True

    def test_returns_error_when_server_raises(self):
        """Health check reports error when server is unreachable."""
        lib = _make_lib()
        mock_client, _ = _make_mock_client()
        mock_client.health.side_effect = Exception("connection refused")

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.meilisearch_health_check()

        assert result["search"] == "error"
        assert result["api_reachable"] is False

    def test_returns_error_when_status_not_available(self):
        """Health check reports error when server returns non-available status."""
        lib = _make_lib()
        mock_client, _ = _make_mock_client()
        mock_client.health.return_value = {"status": "degraded"}

        with patch("meilisearch.Client", return_value=mock_client):
            result = lib.meilisearch_health_check()

        assert result["search"] == "error"
        assert result["api_reachable"] is False


# ============================================================
# TEST: load_meilisearch_lib
# ============================================================

class TestLoadMeiliSearchLib:

    def test_loads_with_api_key(self):
        """load_meilisearch_lib creates a configured instance."""
        lib = load_meilisearch_lib(api_key="test_key")
        assert lib.config.is_configured is True
        assert lib.config.api_key == "test_key"

    def test_loads_from_env(self, monkeypatch):
        """load_meilisearch_lib reads from env when no key given."""
        monkeypatch.setenv("MEILISEARCH_API_KEY", "env_key")
        lib = load_meilisearch_lib()
        assert lib.config.api_key == "env_key"

    def test_loads_with_custom_host(self):
        """load_meilisearch_lib accepts custom host."""
        lib = load_meilisearch_lib(api_key="k", host="https://search.myapp.com")
        assert lib.config.host == "https://search.myapp.com"
