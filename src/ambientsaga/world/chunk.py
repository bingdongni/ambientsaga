"""
Chunk-based spatial management for large worlds.

Divides the world into fixed-size chunks for:
- Level-of-detail (LOD) rendering
- Parallel processing
- Spatial indexing
- Lazy loading of distant regions
- Efficient neighbor queries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ambientsaga.world.state import World


@dataclass
class Chunk:
    """
    A spatial chunk of the world (e.g., 16x16 tiles).
    Chunks are the unit of LOD processing and parallelization.
    """

    chunk_x: int
    chunk_y: int
    size: int
    terrain: np.ndarray  # [size, size] terrain type indices
    elevation: np.ndarray  # [size, size] elevation in meters
    temperature: np.ndarray  # [size, size] temperature in Celsius
    humidity: np.ndarray  # [size, size] humidity 0-1
    precipitation: np.ndarray  # [size, size] annual precipitation in mm
    soil_type: np.ndarray  # [size, size] soil type indices
    aquifer_storage: np.ndarray  # [size, size] groundwater level 0-1
    vegetation_cover: np.ndarray  # [size, size] vegetation density 0-1
    active_signals: list = field(default_factory=list)
    agent_count: int = 0
    last_updated_tick: int = -1
    is_loaded: bool = True  # False = swapped to disk

    @property
    def bounding_box(self) -> tuple[int, int, int, int]:
        """Get world-space bounding box (min_x, min_y, max_x, max_y)."""
        return (
            self.chunk_x * self.size,
            self.chunk_y * self.size,
            (self.chunk_x + 1) * self.size - 1,
            (self.chunk_y + 1) * self.size - 1,
        )

    def contains(self, world_x: int, world_y: int) -> bool:
        """Check if a world coordinate is in this chunk."""
        return (
            self.chunk_x * self.size <= world_x < (self.chunk_x + 1) * self.size
            and self.chunk_y * self.size <= world_y < (self.chunk_y + 1) * self.size
        )

    def local_to_world(self, local_x: int, local_y: int) -> tuple[int, int]:
        """Convert local chunk coordinates to world coordinates."""
        return (
            self.chunk_x * self.size + local_x,
            self.chunk_y * self.size + local_y,
        )

    def world_to_local(self, world_x: int, world_y: int) -> tuple[int, int]:
        """Convert world coordinates to local chunk coordinates."""
        return (
            world_x - self.chunk_x * self.size,
            world_y - self.chunk_y * self.size,
        )

    def summary(self) -> dict:
        """Get a summary of chunk statistics."""
        return {
            "chunk": (self.chunk_x, self.chunk_y),
            "agent_count": self.agent_count,
            "avg_temperature": float(np.mean(self.temperature)),
            "avg_humidity": float(np.mean(self.humidity)),
            "avg_vegetation": float(np.mean(self.vegetation_cover)),
            "active_signals": len(self.active_signals),
            "last_updated": self.last_updated_tick,
        }


class ChunkManager:
    """
    Manages spatial chunks for efficient world operations.

    Responsibilities:
    - Create and store chunks
    - Provide fast spatial queries
    - Manage LOD levels
    - Handle chunk loading/unloading
    """

    def __init__(
        self,
        world_width: int,
        world_height: int,
        chunk_size: int,
        world: World | None = None,
    ) -> None:
        if chunk_size <= 0 or (chunk_size & (chunk_size - 1)) != 0:
            raise ValueError(f"chunk_size must be a positive power of 2, got {chunk_size}")

        self.world_width = world_width
        self.world_height = world_height
        self.chunk_size = chunk_size

        # Number of chunks in each dimension
        self.num_chunks_x = (world_width + chunk_size - 1) // chunk_size
        self.num_chunks_y = (world_height + chunk_size - 1) // chunk_size

        # Chunk storage: key = (chunk_x, chunk_y)
        self._chunks: dict[tuple[int, int], Chunk] = {}

        # Spatial index for fast agent lookup: entity_id -> chunk_coords
        self._agent_locations: dict[str, tuple[int, int]] = {}

        # Per-chunk agent ID lists for fast spatial queries (avoids O(n) scan)
        self._chunk_agents: dict[tuple[int, int], list[str]] = {}

        # Active chunks (for LOD priority)
        self._active_chunks: set[tuple[int, int]] = set()

        # Reference to world for fast position lookups (avoid redundant dict lookup)
        self._world = world

    def get_chunk_coords(self, world_x: int, world_y: int) -> tuple[int, int]:
        """Get chunk coordinates for a world position."""
        return (world_x // self.chunk_size, world_y // self.chunk_size)

    def get_chunk(self, world_x: int, world_y: int) -> Chunk | None:
        """Get the chunk containing a world position."""
        key = self.get_chunk_coords(world_x, world_y)
        return self._chunks.get(key)

    def get_or_create_chunk(self, chunk_x: int, chunk_y: int) -> Chunk:
        """Get existing chunk or create a new one."""
        key = (chunk_x, chunk_y)
        if key not in self._chunks:
            self._chunks[key] = Chunk(
                chunk_x=chunk_x,
                chunk_y=chunk_y,
                size=self.chunk_size,
                terrain=np.full((self.chunk_size, self.chunk_size), 0, dtype=np.int32),
                elevation=np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64),
                temperature=np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64),
                humidity=np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64),
                precipitation=np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64),
                soil_type=np.zeros((self.chunk_size, self.chunk_size), dtype=np.int32),
                aquifer_storage=np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64),
                vegetation_cover=np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64),
            )
        return self._chunks[key]

    def register_agent(self, entity_id: str, world_x: int, world_y: int) -> None:
        """Register an agent's position in the spatial index."""
        old_key = self._agent_locations.get(entity_id)
        new_key = self.get_chunk_coords(world_x, world_y)

        if old_key is not None:
            old_chunk = self._chunks.get(old_key)
            if old_chunk is not None:
                old_chunk.agent_count = max(0, old_chunk.agent_count - 1)
            # Remove from old chunk index
            if old_key in self._chunk_agents:
                try:
                    self._chunk_agents[old_key].remove(entity_id)
                except ValueError:
                    pass

        self._agent_locations[entity_id] = new_key

        # Add to new chunk index
        if new_key not in self._chunk_agents:
            self._chunk_agents[new_key] = []
        if entity_id not in self._chunk_agents[new_key]:
            self._chunk_agents[new_key].append(entity_id)

        new_chunk = self.get_or_create_chunk(*new_key)
        new_chunk.agent_count += 1
        self._active_chunks.add(new_key)

    def unregister_agent(self, entity_id: str) -> None:
        """Remove an agent from the spatial index."""
        old_key = self._agent_locations.pop(entity_id, None)
        if old_key is not None:
            old_chunk = self._chunks.get(old_key)
            if old_chunk is not None:
                old_chunk.agent_count = max(0, old_chunk.agent_count - 1)
            # Remove from chunk index
            if old_key in self._chunk_agents:
                try:
                    self._chunk_agents[old_key].remove(entity_id)
                except ValueError:
                    pass

    def move_agent(self, entity_id: str, old_x: int, old_y: int, new_x: int, new_y: int) -> None:
        """Update an agent's position in the spatial index."""
        old_key = self.get_chunk_coords(old_x, old_y)
        new_key = self.get_chunk_coords(new_x, new_y)

        if old_key == new_key:
            return  # Same chunk, no update needed

        # Update old chunk
        old_chunk = self._chunks.get(old_key)
        if old_chunk is not None:
            old_chunk.agent_count = max(0, old_chunk.agent_count - 1)
        # Remove from old chunk index
        if old_key in self._chunk_agents:
            try:
                self._chunk_agents[old_key].remove(entity_id)
            except ValueError:
                pass

        # Update new chunk
        new_chunk = self.get_or_create_chunk(*new_key)
        new_chunk.agent_count += 1
        # Add to new chunk index
        if new_key not in self._chunk_agents:
            self._chunk_agents[new_key] = []
        if entity_id not in self._chunk_agents[new_key]:
            self._chunk_agents[new_key].append(entity_id)

        self._agent_locations[entity_id] = new_key

    def get_agents_in_radius(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> list[tuple[str, int, int]]:
        """
        Get all agent IDs within a radius of a center point.

        Returns list of (entity_id, world_x, world_y).
        Uses per-chunk index for O(1) lookup per chunk instead of O(n) scan.
        Vectorized implementation for better performance.
        """
        # Early exit for zero/negative radius
        if radius <= 0:
            return []

        chunk_size = self.chunk_size
        radius_sq = radius * radius

        # Determine chunk range to search
        min_cx = max(0, int((center_x - radius) // chunk_size))
        max_cx = min(self.num_chunks_x - 1, int((center_x + radius) // chunk_size))
        min_cy = max(0, int((center_y - radius) // chunk_size))
        max_cy = min(self.num_chunks_y - 1, int((center_y + radius) // chunk_size))

        # For small radii (within 1-2 chunks), use simple approach
        if max_cx - min_cx <= 1 and max_cy - min_cy <= 1:
            return self._get_agents_in_radius_small(center_x, center_y, radius, radius_sq,
                                                    min_cx, max_cx, min_cy, max_cy)

        # Collect agent positions using numpy for larger searches
        agent_positions = []  # [(entity_id, x, y), ...]

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                chunk_agents = self._chunk_agents.get((cx, cy), [])
                for entity_id in chunk_agents:
                    pos = self._world._agent_positions.get(entity_id)
                    if pos is not None:
                        # Quick distance check (squared distance in chunk space)
                        agent_positions.append((entity_id, pos.x, pos.y))

        if not agent_positions:
            return []

        # Vectorized distance calculation using numpy
        pos_x_arr = np.array([p[1] for p in agent_positions], dtype=np.float64)
        pos_y_arr = np.array([p[2] for p in agent_positions], dtype=np.float64)
        dx = pos_x_arr - center_x
        dy = pos_y_arr - center_y
        dist_sq = dx * dx + dy * dy

        # Get indices where distance <= radius (using squared distance comparison)
        valid_indices = np.nonzero(dist_sq <= radius_sq)[0]

        # Build result list from valid indices
        result = []
        entity_ids = [p[0] for p in agent_positions]
        for i in valid_indices:
            result.append((entity_ids[i], int(pos_x_arr[i]), int(pos_y_arr[i])))

        return result

    def _get_agents_in_radius_small(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        radius_sq: float,
        min_cx: int,
        max_cx: int,
        min_cy: int,
        max_cy: int,
    ) -> list[tuple[str, int, int]]:
        """
        Fast path for small-radius queries (within 1-3 chunks).
        Avoids numpy overhead for common small-radius checks.
        """
        results = []

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                chunk_agents = self._chunk_agents.get((cx, cy), [])
                for entity_id in chunk_agents:
                    pos = self._world._agent_positions.get(entity_id)
                    if pos is not None:
                        dx = pos.x - center_x
                        dy = pos.y - center_y
                        if dx * dx + dy * dy <= radius_sq:
                            results.append((entity_id, int(pos.x), int(pos.y)))

        return results

    def get_chunk_population(self, chunk_x: int, chunk_y: int) -> int:
        """Get agent count in a specific chunk."""
        chunk = self._chunks.get((chunk_x, chunk_y))
        return chunk.agent_count if chunk else 0

    def get_hotspot_chunks(self, threshold: int = 10) -> list[tuple[int, int]]:
        """Get chunks with high agent density (hotspots)."""
        hotspots: list[tuple[int, int]] = []
        for key, chunk in self._chunks.items():
            if chunk.agent_count >= threshold:
                hotspots.append(key)
        hotspots.sort(key=lambda k: self._chunks[k].agent_count, reverse=True)
        return hotspots

    def get_adjacent_chunks(self, chunk_x: int, chunk_y: int) -> list[Chunk]:
        """Get all chunks adjacent to a given chunk (including diagonals)."""
        adjacent: list[Chunk] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                chunk = self._chunks.get((chunk_x + dx, chunk_y + dy))
                if chunk is not None:
                    adjacent.append(chunk)
        return adjacent

    def get_tile_terrain(self, world_x: int, world_y: int) -> int:
        """Get terrain type at a world position."""
        chunk = self.get_chunk(world_x, world_y)
        if chunk is None:
            return 0
        lx, ly = chunk.world_to_local(world_x, world_y)
        return int(chunk.terrain[ly, lx])

    def set_tile_terrain(
        self, world_x: int, world_y: int, terrain_type: int
    ) -> None:
        """Set terrain type at a world position."""
        chunk = self.get_or_create_chunk(
            *self.get_chunk_coords(world_x, world_y)
        )
        lx, ly = chunk.world_to_local(world_x, world_y)
        chunk.terrain[ly, lx] = terrain_type

    def get_tile_elevation(self, world_x: int, world_y: int) -> float:
        """Get elevation at a world position."""
        chunk = self.get_chunk(world_x, world_y)
        if chunk is None:
            return 0.0
        lx, ly = chunk.world_to_local(world_x, world_y)
        return float(chunk.elevation[ly, lx])

    def get_tile_climate(self, world_x: int, world_y: int) -> tuple[float, float, float]:
        """Get (temperature, humidity, precipitation) at a world position."""
        chunk = self.get_chunk(world_x, world_y)
        if chunk is None:
            return (15.0, 0.5, 1000.0)
        lx, ly = chunk.world_to_local(world_x, world_y)
        return (
            float(chunk.temperature[ly, lx]),
            float(chunk.humidity[ly, lx]),
            float(chunk.precipitation[ly, lx]),
        )

    def get_stats(self) -> dict:
        """Get global chunk statistics."""
        total_chunks = len(self._chunks)
        total_agents = sum(c.agent_count for c in self._chunks.values())
        active_signals = sum(len(c.active_signals) for c in self._chunks.values())

        return {
            "total_chunks": total_chunks,
            "active_chunks": len(self._active_chunks),
            "total_agents": total_agents,
            "avg_agents_per_chunk": (
                total_agents / total_chunks if total_chunks > 0 else 0
            ),
            "total_active_signals": active_signals,
        }

    def __len__(self) -> int:
        return len(self._chunks)

    def __repr__(self) -> str:
        return f"ChunkManager({self.num_chunks_x}x{self.num_chunks_y} chunks, {len(self._chunks)} loaded)"
