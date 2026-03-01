"""
meilisearch_lib.py - MeiliSearch Full-Text Search Adapter
==========================================================

WHY: Platform Rule #2 — every capability needs a single adapter.
     This is the search adapter. All MeiliSearch calls go through here.

SELF-HOSTED SETUP (Railway):
    1. Add a MeiliSearch service to Railway from the template catalog.
    2. Set MEILISEARCH_HOST and MEILISEARCH_API_KEY in your .env
       (Railway auto-injects these for linked services).
    3. Index listings at creation/update time via add_documents().

USAGE:
    from meilisearch_lib import MeiliSearchLib, MeiliSearchConfig, load_meilisearch_lib

    lib = load_meilisearch_lib()

    # Index a listing
    lib.add_documents("listings", [{"id": 1, "title": "Vintage lamp", "price_usd": 25.0}])

    # Full-text search
    results = lib.search("listings", "vintage", filters="status = 'active'", limit=20)
    # results["data"]["hits"] → list of matching documents

ENV VARS:
    MEILISEARCH_HOST     — e.g. https://my-ms.railway.app (default: http://localhost:7700)
    MEILISEARCH_API_KEY  — master key or search API key from MeiliSearch dashboard
"""

import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

class MeiliSearchConfig:
    """
    Configuration for MeiliSearch connection.

    Priority: constructor argument > environment variable > default.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("MEILISEARCH_API_KEY")
        self.host = host or os.environ.get("MEILISEARCH_HOST", "http://localhost:7700")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


# ============================================================
# ADAPTER
# ============================================================

class MeiliSearchLib:
    """
    Adapter for MeiliSearch full-text search.

    All methods return {"success": bool, "data": ..., "error": ...}.
    When unconfigured (no API key), methods return an error dict immediately
    without making any network calls.
    """

    def __init__(self, config: MeiliSearchConfig):
        self.config = config

    def _client(self):
        """
        Return a meilisearch.Client instance, or None if unconfigured.
        Lazily created per call (stateless — MeiliSearch client is cheap).
        """
        if not self.config.is_configured:
            return None
        try:
            import meilisearch
            return meilisearch.Client(self.config.host, self.config.api_key)
        except ImportError:
            logger.error("meilisearch package not installed. Run: pip install meilisearch")
            return None

    def _not_configured(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "MEILISEARCH_API_KEY not configured. Set it in .env or pass to MeiliSearchConfig.",
        }

    # ----------------------------------------------------------
    # INDEX MANAGEMENT
    # ----------------------------------------------------------

    def create_index(
        self,
        uid: str,
        primary_key: str = "id",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a MeiliSearch index.

        Args:
            uid: Index name (e.g. "listings")
            primary_key: Document primary key field (default "id")
            settings: Optional settings dict (searchable_attributes, filterable_attributes, etc.)

        Returns:
            {"success": True, "data": task_dict}
        """
        if not self.config.is_configured:
            return self._not_configured()

        client = self._client()
        if client is None:
            return {"success": False, "error": "meilisearch package not installed"}

        try:
            task = client.create_index(uid, {"primaryKey": primary_key})
            if settings:
                client.index(uid).update_settings(settings)
            logger.debug(f"MeiliSearch create_index: uid={uid} primary_key={primary_key}")
            return {"success": True, "data": task}
        except Exception as exc:
            logger.warning(f"MeiliSearch create_index failed: {exc}")
            return {"success": False, "error": str(exc)}

    def delete_index(self, uid: str) -> Dict[str, Any]:
        """Delete an index and all its documents."""
        if not self.config.is_configured:
            return self._not_configured()

        client = self._client()
        if client is None:
            return {"success": False, "error": "meilisearch package not installed"}

        try:
            task = client.index(uid).delete()
            return {"success": True, "data": task}
        except Exception as exc:
            logger.warning(f"MeiliSearch delete_index failed: {exc}")
            return {"success": False, "error": str(exc)}

    # ----------------------------------------------------------
    # DOCUMENT OPERATIONS
    # ----------------------------------------------------------

    def add_documents(
        self,
        index_uid: str,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Add or replace documents in an index (upsert by primary key).

        Args:
            index_uid: Target index name
            documents: List of dicts. Each must contain the primary key field.

        Returns:
            {"success": True, "data": task_dict}
        """
        if not self.config.is_configured:
            return self._not_configured()

        if not documents:
            return {"success": True, "data": {"message": "No documents to index"}}

        client = self._client()
        if client is None:
            return {"success": False, "error": "meilisearch package not installed"}

        try:
            task = client.index(index_uid).add_documents(documents)
            logger.debug(f"MeiliSearch add_documents: index={index_uid} count={len(documents)}")
            return {"success": True, "data": task}
        except Exception as exc:
            logger.warning(f"MeiliSearch add_documents failed: {exc}")
            return {"success": False, "error": str(exc)}

    def update_document(
        self,
        index_uid: str,
        document: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update (upsert) a single document by primary key.

        Args:
            index_uid: Target index name
            document: Document dict containing the primary key field

        Returns:
            {"success": True, "data": task_dict}
        """
        if not self.config.is_configured:
            return self._not_configured()

        client = self._client()
        if client is None:
            return {"success": False, "error": "meilisearch package not installed"}

        try:
            task = client.index(index_uid).update_documents([document])
            return {"success": True, "data": task}
        except Exception as exc:
            logger.warning(f"MeiliSearch update_document failed: {exc}")
            return {"success": False, "error": str(exc)}

    def delete_document(
        self,
        index_uid: str,
        document_id,
    ) -> Dict[str, Any]:
        """
        Delete a single document by its primary key value.

        Args:
            index_uid: Target index name
            document_id: Primary key value of the document to delete

        Returns:
            {"success": True, "data": task_dict}
        """
        if not self.config.is_configured:
            return self._not_configured()

        client = self._client()
        if client is None:
            return {"success": False, "error": "meilisearch package not installed"}

        try:
            task = client.index(index_uid).delete_document(document_id)
            return {"success": True, "data": task}
        except Exception as exc:
            logger.warning(f"MeiliSearch delete_document failed: {exc}")
            return {"success": False, "error": str(exc)}

    # ----------------------------------------------------------
    # SEARCH
    # ----------------------------------------------------------

    def search(
        self,
        index_uid: str,
        query: str,
        filters: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Full-text search an index.

        Args:
            index_uid: Index to search
            query: Search string
            filters: MeiliSearch filter expression (e.g. "status = 'active'")
            limit: Max results to return (default 20)
            offset: Pagination offset (default 0)

        Returns:
            {"success": True, "data": {"hits": [...], "estimatedTotalHits": int, ...}}
        """
        if not self.config.is_configured:
            return self._not_configured()

        client = self._client()
        if client is None:
            return {"success": False, "error": "meilisearch package not installed"}

        try:
            opt_params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if filters:
                opt_params["filter"] = filters

            results = client.index(index_uid).search(query, opt_params)
            return {"success": True, "data": results}
        except Exception as exc:
            logger.warning(f"MeiliSearch search failed: {exc}")
            return {"success": False, "error": str(exc)}

    # ----------------------------------------------------------
    # HEALTH CHECK
    # ----------------------------------------------------------

    def meilisearch_health_check(self) -> Dict[str, Any]:
        """
        Returns a status dict suitable for inclusion in /health responses.

        Returns:
            {"search": "disabled" | "enabled" | "error", ...}
        """
        if not self.config.is_configured:
            return {
                "search": "disabled",
                "fix": "Set MEILISEARCH_HOST and MEILISEARCH_API_KEY in .env",
            }

        client = self._client()
        if client is None:
            return {"search": "error", "error": "meilisearch package not installed"}

        try:
            health = client.health()
            status = health.get("status", "")
            if status == "available":
                return {
                    "search": "enabled",
                    "host": self.config.host,
                    "api_reachable": True,
                }
            return {
                "search": "error",
                "api_reachable": False,
                "raw": health,
            }
        except Exception as exc:
            logger.warning(f"MeiliSearch health check failed: {exc}")
            return {
                "search": "error",
                "api_reachable": False,
                "error": str(exc),
            }


# ============================================================
# FACTORY
# ============================================================

def load_meilisearch_lib(
    host: Optional[str] = None,
    api_key: Optional[str] = None,
) -> MeiliSearchLib:
    """
    Factory function. Reads config from env vars if not provided.

    Args:
        host: MeiliSearch host URL (overrides MEILISEARCH_HOST env var)
        api_key: API key (overrides MEILISEARCH_API_KEY env var)

    Returns:
        Configured MeiliSearchLib instance
    """
    config = MeiliSearchConfig(api_key=api_key, host=host)
    return MeiliSearchLib(config)
