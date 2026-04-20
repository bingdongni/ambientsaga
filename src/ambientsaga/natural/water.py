"""
Hydrological (water) simulation system.

Models the complete water cycle:
- Evaporation from water bodies and vegetation
- Precipitation collection
- Surface runoff and river flow
- Groundwater infiltration and flow
- Snowmelt
- Water quality
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ambientsaga.config import HydrologyConfig
from ambientsaga.types import TerrainType

if TYPE_CHECKING:
    pass


class HydrologySystem:
    """
    Hydrological simulation.

    Tracks water movement through the world:
    - Rivers as flow networks
    - Lakes as storage reservoirs
    - Aquifers as underground storage
    - Water flux between all reservoirs
    """

    def __init__(
        self, config: HydrologyConfig, width: int, height: int, seed: int = 42
    ) -> None:
        self.config = config
        self.width = width
        self.height = height
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Water storage arrays
        self._surface_water: np.ndarray | None = None  # mm water depth
        self._groundwater: np.ndarray | None = None  # aquifer level 0-1
        self._river_flow: np.ndarray | None = None  # m³/s river discharge
        self._snowpack: np.ndarray | None = None  # mm snow water equivalent
        self._water_quality: np.ndarray | None = None  # 0-1 quality index

        # River network
        self._river_network: list[list[tuple[int, int]]] = []

        # Statistics
        self._total_evaporation = 0.0
        self._total_precipitation = 0.0
        self._total_runoff = 0.0

    def initialize(
        self,
        terrain: np.ndarray,
        elevation: np.ndarray,
        precipitation: np.ndarray,
        rivers: list[list[tuple[int, int]]] | None = None,
    ) -> None:
        """Initialize hydrological system from terrain."""
        H, W = terrain.shape
        self._surface_water = np.zeros((H, W), dtype=np.float64)
        self._groundwater = np.full(
            (H, W), 0.5, dtype=np.float64
        )  # 50% aquifer fill
        self._river_flow = np.zeros((H, W), dtype=np.float64)
        self._snowpack = np.zeros((H, W), dtype=np.float64)
        self._water_quality = np.ones((H, W), dtype=np.float64)

        if rivers:
            self._river_network = rivers

        # Initialize lakes (tiles surrounded by land but water-accessible)
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                if terrain[y, x] == TerrainType.SHALLOW_WATER.value:
                    # Check if it's surrounded by land
                    neighbors_land = sum(
                        1
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                        if terrain[y + dy, x + dx] != TerrainType.DEEP_OCEAN.value
                        and terrain[y + dy, x + dx] != TerrainType.OCEAN.value
                    )
                    if neighbors_land >= 3:
                        # It's a lake
                        self._surface_water[y, x] = self._rng.uniform(100, 500)

        # Mark river tiles
        if rivers:
            for river in rivers:
                for x, y in river:
                    if 0 <= x < W and 0 <= y < H:
                        self._surface_water[y, x] = max(
                            self._surface_water[y, x], 50.0
                        )

    def update(
        self,
        tick: int,
        terrain: np.ndarray,
        elevation: np.ndarray,
        temperature: np.ndarray,
        precipitation: np.ndarray,
    ) -> None:
        """
        Update hydrology for one tick.

        Process:
        1. Add precipitation to surface water
        2. Evaporate surface water (if temperature > 0)
        3. Infiltrate water into ground
        4. Flow groundwater
        5. Flow rivers downstream
        6. Update snowpack
        """
        H, W = terrain.shape

        # Temperature for snow/rain distinction and evaporation
        float(np.mean(temperature))

        for y in range(H):
            for x in range(W):
                if not terrain[y, x].is_land and not terrain[y, x].is_water:
                    continue

                # 1. Precipitation
                precip_mm = precipitation[y, x] / 365.0  # Daily
                self._surface_water[y, x] += precip_mm * 0.7  # 70% to surface
                self._groundwater[y, x] += (
                    precip_mm * 0.3 * self.config.aquifer_recharge_rate
                )
                self._total_precipitation += precip_mm

                # 2. Evaporation (only if warm enough and water available)
                if temperature[y, x] > 0 and self._surface_water[y, x] > 0:
                    evap_rate = self.config.lake_evaporation_rate * (
                        temperature[y, x] / 20.0
                    )  # Warmer = more evaporation
                    evap = min(self._surface_water[y, x], evap_rate)
                    self._surface_water[y, x] -= evap
                    self._total_evaporation += evap

                    # Evapotranspiration from vegetation
                    if terrain[y, x].is_forest:
                        evap += self._surface_water[y, x] * 0.01
                        self._surface_water[y, x] = max(0, self._surface_water[y, x] - evap)

                # 3. Snowmelt (if warm enough)
                if temperature[y, x] > 2 and self._snowpack[y, x] > 0:
                    melt = min(
                        self._snowpack[y, x],
                        max(0, (temperature[y, x] - 2) * 2.0),
                    )
                    self._snowpack[y, x] -= melt
                    self._surface_water[y, x] += melt

                # 4. Snow accumulation (if cold enough)
                if temperature[y, x] < -1:
                    # Snow precip
                    if precipitation[y, x] > 0:
                        self._snowpack[y, x] += precipitation[y, x] / 365.0 * 0.3

                # 5. Groundwater flow (slow, diffusion-like)
                self._flow_groundwater(x, y, terrain)

                # 6. Runoff (surface water flows downhill)
                self._flow_surface_water(x, y, terrain, elevation)

                # 7. Lake evaporation (special case)
                if terrain[y, x] == TerrainType.SHALLOW_WATER.value:
                    if self._surface_water[y, x] < 20:  # Shallow lake drying
                        pass  # Could convert to marsh or land

    def _flow_groundwater(self, x: int, y: int, terrain: np.ndarray) -> None:
        """Flow groundwater to adjacent tiles."""
        H, W = terrain.shape
        flow_rate = 0.001  # Very slow

        current = self._groundwater[y, x]
        if current <= 0:
            return

        neighbors: list[tuple[int, int, float]] = []  # (nx, ny, slope)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                slope = max(0, current - self._groundwater[ny, nx])
                if slope > 0:
                    neighbors.append((nx, ny, slope))

        if not neighbors:
            return

        total_slope = sum(n[2] for n in neighbors)
        for nx, ny, slope in neighbors:
            flow = current * flow_rate * (slope / total_slope if total_slope > 0 else 0)
            self._groundwater[y, x] -= flow
            self._groundwater[ny, nx] += flow

    def _flow_surface_water(
        self, x: int, y: int, terrain: np.ndarray, elevation: np.ndarray
    ) -> None:
        """Flow surface water to lower tiles (river simulation)."""
        H, W = terrain.shape
        flow_rate = 0.1  # Faster than groundwater

        current = self._surface_water[y, x]
        if current < 1:  # Minimum water for flow
            return

        # Find lowest neighbor
        min_elev = elevation[y, x]
        neighbors: list[tuple[int, int]] = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                if elevation[ny, nx] < min_elev and terrain[ny, nx].is_water:
                    neighbors.append((nx, ny))

        if neighbors:
            flow = current * flow_rate
            per_neighbor = flow / len(neighbors)
            for nx, ny in neighbors:
                self._surface_water[y, x] -= per_neighbor
                self._surface_water[ny, nx] += per_neighbor
                self._total_runoff += per_neighbor

        # Prevent negative water
        self._surface_water[y, x] = max(0, self._surface_water[y, x])

    def get_surface_water(self, x: int, y: int) -> float:
        """Get surface water depth at a position (mm)."""
        if self._surface_water is None:
            return 0.0
        return float(self._surface_water[y, x])

    def get_groundwater_level(self, x: int, y: int) -> float:
        """Get groundwater level at a position (0-1)."""
        if self._groundwater is None:
            return 0.5
        return float(self._groundwater[y, x])

    def get_water_quality(self, x: int, y: int) -> float:
        """Get water quality at a position (0-1)."""
        if self._water_quality is None:
            return 1.0
        return float(self._water_quality[y, x])

    def is_flooding(self, x: int, y: int, terrain: np.ndarray) -> bool:
        """Check if a tile is experiencing flooding."""
        if self._surface_water is None:
            return False
        water = self._surface_water[y, x]
        return water > 200  # Threshold for flooding

    def get_streamflow(self, x: int, y: int) -> float:
        """Get river/stream flow at a position (m³/s equivalent)."""
        if self._river_flow is None:
            return 0.0
        return float(self._river_flow[y, x])

    def get_stats(self) -> dict:
        """Get hydrology statistics."""
        if self._surface_water is None:
            return {}
        return {
            "total_surface_water_mm": float(np.sum(self._surface_water)),
            "avg_groundwater_level": float(np.mean(self._groundwater)),
            "total_snowpack_mm": float(np.sum(self._snowpack)),
            "avg_water_quality": float(np.mean(self._water_quality)),
            "total_evaporation_mm": self._total_evaporation,
            "total_precipitation_mm": self._total_precipitation,
            "total_runoff_mm": self._total_runoff,
            "water_balance_mm": self._total_precipitation - self._total_evaporation - self._total_runoff,
        }
