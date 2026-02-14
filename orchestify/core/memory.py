"""
Contextify Memory Integration with Local Fallback.

Layered memory system with support for Contextify remote storage and local JSON fallback.
Handles agent-level, epic-level, and global-level memory with pattern tracking.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


class MemoryLayer(str, Enum):
    """Memory layer enumeration for scoped storage."""

    AGENT = "agent"  # Per-agent persistent memory
    EPIC = "epic"  # Shared within an epic
    GLOBAL = "global"  # Organization-wide


@dataclass
class MemoryEntry:
    """
    Represents a single memory entry.

    Attributes:
        key: Unique key for the memory entry
        value: The stored value (can be any JSON-serializable type)
        layer: MemoryLayer indicating scope of the entry
        agent_id: Optional agent identifier for agent-level memory
        epic_id: Optional epic identifier for epic-level memory
        timestamp: ISO format timestamp of entry creation
        metadata: Additional metadata about the entry
    """

    key: str
    value: Any
    layer: MemoryLayer
    agent_id: Optional[str] = None
    epic_id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entry to dictionary for serialization.

        Returns:
            Dictionary representation of the entry
        """
        data = asdict(self)
        data["layer"] = self.layer.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """
        Create entry from dictionary.

        Args:
            data: Dictionary representation of entry

        Returns:
            MemoryEntry instance
        """
        if isinstance(data.get("layer"), str):
            data["layer"] = MemoryLayer(data["layer"])
        return cls(**data)


class MemoryClient:
    """
    Layered memory client with Contextify support and local fallback.

    Provides a unified interface for storing and recalling memories across
    different scopes (agent, epic, global) with automatic fallback to local
    JSON storage if Contextify is unavailable.

    Attributes:
        config: MemoryConfig instance
        contextify_enabled: Whether Contextify is enabled
        http_client: httpx.AsyncClient for Contextify API calls
        local_store: In-memory store for local fallback
        local_path: Path to local JSON memory files
    """

    def __init__(self, config: Any) -> None:
        """
        Initialize the memory client.

        Args:
            config: MemoryConfig instance with contextify and fallback settings

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self.contextify_enabled = config.contextify.enabled
        self.http_client: Optional[httpx.AsyncClient] = None
        self.local_store: Dict[str, List[Dict[str, Any]]] = {
            layer.value: [] for layer in MemoryLayer
        }
        self.local_path = Path(config.fallback.path)

        logger.debug(
            f"Initializing MemoryClient (contextify_enabled={self.contextify_enabled})"
        )

        if self.contextify_enabled and httpx is None:
            logger.warning(
                "Contextify enabled but httpx not installed, falling back to local storage"
            )
            self.contextify_enabled = False

        self._ensure_local_path()
        self._local_load()

    def _ensure_local_path(self) -> None:
        """Ensure local memory directory exists."""
        try:
            self.local_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured local memory path exists: {self.local_path}")
        except Exception as e:
            logger.error(f"Failed to create local memory path: {e}")

    async def _init_http_client(self) -> None:
        """Initialize async HTTP client for Contextify if needed."""
        if self.contextify_enabled and self.http_client is None:
            try:
                self.http_client = httpx.AsyncClient(
                    base_url=self.config.contextify.host, timeout=10.0
                )
                logger.debug(
                    f"Initialized HTTP client for Contextify: "
                    f"{self.config.contextify.host}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize HTTP client: {e}")
                self.contextify_enabled = False

    async def store(
        self,
        layer: MemoryLayer,
        key: str,
        value: Any,
        agent_id: Optional[str] = None,
        epic_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """
        Store a memory entry in the specified layer.

        Args:
            layer: MemoryLayer to store in
            key: Unique key for the entry
            value: Value to store (must be JSON-serializable)
            agent_id: Optional agent ID for agent-level memory
            epic_id: Optional epic ID for epic-level memory
            metadata: Optional metadata dictionary

        Returns:
            Stored MemoryEntry

        Raises:
            ValueError: If value is not JSON-serializable
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            layer=layer,
            agent_id=agent_id,
            epic_id=epic_id,
            metadata=metadata or {},
        )

        logger.debug(
            f"Storing memory: layer={layer.value}, key={key}, "
            f"agent_id={agent_id}, epic_id={epic_id}"
        )

        if self.contextify_enabled:
            await self._contextify_store(entry)
        else:
            self._local_store(entry)

        return entry

    async def recall(
        self,
        layer: MemoryLayer,
        query: str,
        agent_id: Optional[str] = None,
        epic_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Recall memories from the specified layer.

        Args:
            layer: MemoryLayer to recall from
            query: Search query string
            agent_id: Optional agent ID to filter by
            epic_id: Optional epic ID to filter by
            limit: Maximum number of results to return

        Returns:
            List of matching MemoryEntry objects
        """
        logger.debug(
            f"Recalling memory: layer={layer.value}, query={query}, "
            f"agent_id={agent_id}, epic_id={epic_id}, limit={limit}"
        )

        if self.contextify_enabled:
            return await self._contextify_recall(
                layer, query, agent_id=agent_id, epic_id=epic_id, limit=limit
            )
        else:
            return self._local_recall(
                layer, query, agent_id=agent_id, epic_id=epic_id, limit=limit
            )

    async def get_context(
        self, agent_id: str, epic_id: int
    ) -> Dict[str, List[MemoryEntry]]:
        """
        Get full context for an agent (agent + epic + global memories).

        Args:
            agent_id: Agent identifier
            epic_id: Epic identifier

        Returns:
            Dictionary with 'agent', 'epic', and 'global' keys containing
            corresponding MemoryEntry lists
        """
        logger.debug(f"Getting context: agent_id={agent_id}, epic_id={epic_id}")

        agent_memories = await self.recall(
            MemoryLayer.AGENT, "*", agent_id=agent_id, limit=100
        )
        epic_memories = await self.recall(
            MemoryLayer.EPIC, "*", epic_id=epic_id, limit=100
        )
        global_memories = await self.recall(MemoryLayer.GLOBAL, "*", limit=100)

        return {
            "agent": agent_memories,
            "epic": epic_memories,
            "global": global_memories,
        }

    async def store_recycle(
        self, epic_id: int, issue_number: int, recycle_output: Dict[str, List[str]]
    ) -> None:
        """
        Store ABD recycle output (Kept/Reused/Banned patterns).

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            recycle_output: Dictionary with 'kept', 'reused', 'banned' keys
        """
        key = f"recycle_{issue_number}"
        metadata = {"epic_id": epic_id, "issue_number": issue_number}

        logger.debug(f"Storing recycle output: {key}")

        await self.store(
            MemoryLayer.EPIC, key, recycle_output, epic_id=epic_id, metadata=metadata
        )

    async def store_scorecard(
        self, epic_id: int, issue_number: int, scorecard: Dict[str, Any]
    ) -> None:
        """
        Store ABD scorecard for tracking.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            scorecard: Scorecard dictionary
        """
        key = f"scorecard_{issue_number}"
        metadata = {"epic_id": epic_id, "issue_number": issue_number}

        logger.debug(f"Storing scorecard: {key}")

        await self.store(
            MemoryLayer.EPIC, key, scorecard, epic_id=epic_id, metadata=metadata
        )

    async def get_patterns(self, layer: MemoryLayer) -> List[MemoryEntry]:
        """
        Get all promoted patterns (Reused items from recycle).

        Args:
            layer: MemoryLayer to search in

        Returns:
            List of promoted pattern MemoryEntry objects
        """
        logger.debug(f"Getting patterns from layer: {layer.value}")

        entries = await self.recall(layer, "reused", limit=1000)
        return [e for e in entries if "reused" in e.key or e.metadata.get("promoted")]

    async def get_anti_patterns(self, layer: MemoryLayer) -> List[MemoryEntry]:
        """
        Get all banned patterns (Banned items from recycle).

        Args:
            layer: MemoryLayer to search in

        Returns:
            List of anti-pattern MemoryEntry objects
        """
        logger.debug(f"Getting anti-patterns from layer: {layer.value}")

        entries = await self.recall(layer, "banned", limit=1000)
        return [e for e in entries if "banned" in e.key or e.metadata.get("banned")]

    async def _contextify_store(self, entry: MemoryEntry) -> None:
        """
        Store entry in Contextify.

        Args:
            entry: MemoryEntry to store

        Raises:
            RuntimeError: If API call fails
        """
        if not self.contextify_enabled or not self.http_client:
            await self._init_http_client()

        if not self.contextify_enabled:
            self._local_store(entry)
            return

        try:
            payload = entry.to_dict()
            response = await self.http_client.post(
                f"/api/memory/{entry.layer.value}",
                json=payload,
            )
            response.raise_for_status()
            logger.debug(f"Stored in Contextify: {entry.key}")
        except Exception as e:
            logger.warning(f"Failed to store in Contextify, falling back to local: {e}")
            self._local_store(entry)

    async def _contextify_recall(
        self,
        layer: MemoryLayer,
        query: str,
        agent_id: Optional[str] = None,
        epic_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Recall entries from Contextify.

        Args:
            layer: MemoryLayer to recall from
            query: Search query
            agent_id: Optional agent filter
            epic_id: Optional epic filter
            limit: Result limit

        Returns:
            List of MemoryEntry objects
        """
        if not self.contextify_enabled or not self.http_client:
            await self._init_http_client()

        if not self.contextify_enabled:
            return self._local_recall(layer, query, agent_id, epic_id, limit)

        try:
            params = {
                "q": query,
                "limit": limit,
            }
            if agent_id:
                params["agent_id"] = agent_id
            if epic_id:
                params["epic_id"] = epic_id

            response = await self.http_client.get(
                f"/api/memory/{layer.value}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            return [MemoryEntry.from_dict(item) for item in data.get("results", [])]
        except Exception as e:
            logger.warning(f"Failed to recall from Contextify, falling back to local: {e}")
            return self._local_recall(layer, query, agent_id, epic_id, limit)

    def _local_store(self, entry: MemoryEntry) -> None:
        """
        Store entry in local JSON storage.

        Args:
            entry: MemoryEntry to store
        """
        layer_value = entry.layer.value
        if layer_value not in self.local_store:
            self.local_store[layer_value] = []

        self.local_store[layer_value].append(entry.to_dict())
        logger.debug(f"Stored locally: {entry.key} in {layer_value}")
        self._local_save()

    def _local_recall(
        self,
        layer: MemoryLayer,
        query: str,
        agent_id: Optional[str] = None,
        epic_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Recall entries from local JSON storage.

        Args:
            layer: MemoryLayer to recall from
            query: Search query (can be "*" for all)
            agent_id: Optional agent filter
            epic_id: Optional epic filter
            limit: Result limit

        Returns:
            List of MemoryEntry objects
        """
        layer_value = layer.value
        results = []

        if layer_value not in self.local_store:
            return results

        for item in self.local_store[layer_value]:
            # Filter by agent_id if specified
            if agent_id and item.get("agent_id") != agent_id:
                continue

            # Filter by epic_id if specified
            if epic_id and item.get("epic_id") != epic_id:
                continue

            # Filter by query if not "*"
            if query != "*":
                if (
                    query.lower() not in item.get("key", "").lower()
                    and query.lower() not in str(item.get("value", "")).lower()
                ):
                    continue

            results.append(MemoryEntry.from_dict(item))

        return results[:limit]

    def _local_save(self) -> None:
        """Persist local memory to JSON files."""
        try:
            for layer in MemoryLayer:
                file_path = self.local_path / f"{layer.value}.json"
                data = {
                    "layer": layer.value,
                    "entries": self.local_store.get(layer.value, []),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                logger.debug(f"Persisted local memory: {file_path}")
        except Exception as e:
            logger.error(f"Failed to persist local memory: {e}")

    def _local_load(self) -> None:
        """Load local memory from JSON files."""
        try:
            for layer in MemoryLayer:
                file_path = self.local_path / f"{layer.value}.json"
                if file_path.exists():
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    self.local_store[layer.value] = data.get("entries", [])
                    logger.debug(f"Loaded local memory: {file_path}")
        except Exception as e:
            logger.error(f"Failed to load local memory: {e}")

    async def close(self) -> None:
        """Cleanup resources and close HTTP client."""
        try:
            self._local_save()
            if self.http_client:
                await self.http_client.aclose()
            logger.debug("Memory client closed successfully")
        except Exception as e:
            logger.error(f"Error closing memory client: {e}")

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self._local_save()
        except Exception:
            pass
