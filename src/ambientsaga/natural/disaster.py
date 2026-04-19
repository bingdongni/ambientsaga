"""
Natural disaster simulation system.

Models:
- Earthquakes (seismic activity, magnitude, effects)
- Volcanic eruptions (location, magnitude, environmental impact)
- Floods (river flooding, coastal flooding)
- Droughts (meteorological, agricultural, hydrological)
- Wildfires (fire behavior, spread, ecosystem impact)
- Plagues (disease outbreaks, transmission, mortality)
- Cascading disasters (earthquake -> tsunami -> plague)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from ambientsaga.config import DisasterConfig
from ambientsaga.types import EventPriority, Pos2D, SignalType, TerrainType

if TYPE_CHECKING:
    from ambientsaga.world.state import World


# ---------------------------------------------------------------------------
# Disaster Types
# ---------------------------------------------------------------------------


@dataclass
class Disaster:
    """A natural disaster event."""

    disaster_id: str
    disaster_type: str  # "earthquake", "volcano", "flood", etc.
    tick: int
    position: Pos2D
    magnitude: float  # Severity scale varies by type
    affected_tiles: list[tuple[int, int]]
    casualties: int = 0
    economic_damage: float = 0.0
    recovery_ticks: int = 0
    cascade_depth: int = 0
    cause_id: str | None = None  # ID of triggering disaster

    @property
    def severity(self) -> str:
        if self.magnitude >= 0.8:
            return "catastrophic"
        elif self.magnitude >= 0.6:
            return "major"
        elif self.magnitude >= 0.4:
            return "significant"
        elif self.magnitude >= 0.2:
            return "minor"
        else:
            return "negligible"


class DisasterSystem:
    """
    Natural disaster simulation system.

    Each disaster type has:
    - Probability model (when/where disasters occur)
    - Physical model (magnitude, affected area, duration)
    - Cascade model (what secondary disasters it can trigger)
    - Impact model (casualties, economic damage, ecological impact)
    """

    def __init__(
        self, config: DisasterConfig, width: int, height: int, seed: int = 42
    ) -> None:
        self.config = config
        self.width = width
        self.height = height
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Active disasters
        self._active_disasters: list[Disaster] = []

        # Disaster history
        self._disaster_history: list[Disaster] = []

        # Plate boundary map (for earthquakes and volcanoes)
        self._plate_boundary: np.ndarray | None = None

        # Per-tick statistics
        self._annual_casualties = 0
        self._annual_damage = 0.0

    def initialize(self, terrain: np.ndarray, elevation: np.ndarray) -> None:
        """Initialize disaster system from terrain."""
        H, W = terrain.shape

        # Mark plate boundaries for earthquake/volcano placement
        self._plate_boundary = np.zeros((H, W), dtype=np.float64)

        for y in range(1, H - 1):
            for x in range(1, W - 1):
                # Simple plate boundary detection (mountain + adjacent lowland)
                elev = elevation[y, x]
                if elev > 500:  # Mountains
                    neighbor_elevs = []
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if 0 <= y + dy < H and 0 <= x + dx < W:
                                neighbor_elevs.append(elevation[y + dy, x + dx])
                    if neighbor_elevs:
                        avg_neighbor = sum(neighbor_elevs) / len(neighbor_elevs)
                        if elev - avg_neighbor > 300:
                            self._plate_boundary[y, x] = 1.0

    def update(self, tick: int, world: World) -> list[Disaster]:
        """
        Update disasters for the current tick.

        Returns list of new disasters that occurred this tick.
        """
        new_disasters: list[Disaster] = []

        # Check for each disaster type
        new_disasters.extend(self._check_earthquakes(tick, world))
        new_disasters.extend(self._check_volcanoes(tick, world))
        new_disasters.extend(self._check_floods(tick, world))
        new_disasters.extend(self._check_droughts(tick, world))
        new_disasters.extend(self._check_wildfires(tick, world))
        new_disasters.extend(self._check_plagues(tick, world))

        # Process cascades
        if self.config.cascade_enabled:
            for disaster in list(new_disasters):
                cascades = self._generate_cascades(disaster, world)
                new_disasters.extend(cascades)

        # Update active disasters
        self._active_disasters = [
            d for d in self._active_disasters if d.recovery_ticks > 0
        ]
        for d in self._active_disasters:
            d.recovery_ticks -= 1

        # Track statistics
        for d in new_disasters:
            self._annual_casualties += d.casualties
            self._annual_damage += d.economic_damage
            self._disaster_history.append(d)

        return new_disasters

    def _check_earthquakes(self, tick: int, world: World) -> list[Disaster]:
        """Check for earthquake occurrence."""
        disasters: list[Disaster] = []

        if self._rng.random() >= self.config.earthquake_probability:
            return disasters

        # Find a location on a plate boundary
        H, W = self.height, self.width
        candidates: list[tuple[int, int]] = []
        for _ in range(100):
            x = self._rng.integers(0, W)
            y = self._rng.integers(0, H)
            if self._plate_boundary is not None and self._plate_boundary[y, x] > 0.5:
                candidates.append((x, y))

        if not candidates:
            return disasters

        x, y = candidates[self._rng.integers(len(candidates))]
        magnitude = self._rng.uniform(0.3, 0.95)
        radius = int(10 + magnitude * 50)  # 10-60 tile radius

        # Find affected tiles
        affected = self._get_affected_area(x, y, radius, world)

        disaster = Disaster(
            disaster_id=f"eq_{tick}_{x}_{y}",
            disaster_type="earthquake",
            tick=tick,
            position=Pos2D(x, y),
            magnitude=magnitude,
            affected_tiles=affected,
            casualties=self._estimate_casualties("earthquake", magnitude, affected, world),
            economic_damage=magnitude * len(affected) * 10.0,
            recovery_ticks=int((1.0 - magnitude) * 1000),
        )

        # Apply effects
        self._apply_earthquake_effects(disaster, world)

        disasters.append(disaster)
        return disasters

    def _apply_earthquake_effects(self, disaster: Disaster, world: World) -> None:
        """Apply earthquake effects to the world."""
        # Destroy buildings (reduce organization population)
        for x, y in disaster.affected_tiles:
            terrain = world.get_terrain(x, y)
            if terrain == TerrainType.HIGH_MOUNTAINS:
                # Trigger landslide
                world.log_event(
                    event_type="landslide",
                    position=Pos2D(x, y),
                    priority=EventPriority.HIGH,
                    data={
                        "magnitude": disaster.magnitude,
                        "affected": len(disaster.affected_tiles),
                    },
                    narrative=f"An earthquake (magnitude {disaster.magnitude:.1f}) struck at ({x}, {y})",
                )

        # Publish disaster signal
        world.publish_signal(
            SignalType.DISASTER_WARNING,
            source_pos=disaster.position,
            intensity=disaster.magnitude,
            duration=100,
        )

    def _check_volcanoes(self, tick: int, world: World) -> list[Disaster]:
        """Check for volcanic eruption."""
        disasters: list[Disaster] = []

        if self._rng.random() >= self.config.volcanic_probability:
            return disasters

        # Find volcanic locations (high mountains)
        H, W = self.height, self.width
        candidates: list[tuple[int, int]] = []
        for _ in range(100):
            x = self._rng.integers(W // 4, 3 * W // 4)
            y = self._rng.integers(H // 4, 3 * H // 4)
            terrain = world.get_terrain(x, y)
            if terrain in (TerrainType.MOUNTAINS, TerrainType.HIGH_MOUNTAINS):
                candidates.append((x, y))

        if not candidates:
            return disasters

        x, y = candidates[self._rng.integers(len(candidates))]
        magnitude = self._rng.uniform(0.4, 0.95)
        radius = int(15 + magnitude * 40)

        affected = self._get_affected_area(x, y, radius, world)

        disaster = Disaster(
            disaster_id=f"vol_{tick}_{x}_{y}",
            disaster_type="volcano",
            tick=tick,
            position=Pos2D(x, y),
            magnitude=magnitude,
            affected_tiles=affected,
            casualties=self._estimate_casualties("volcano", magnitude, affected, world),
            economic_damage=magnitude * len(affected) * 20.0,
            recovery_ticks=int(2000 + magnitude * 3000),
        )

        disasters.append(disaster)

        world.log_event(
            event_type="volcanic_eruption",
            position=Pos2D(x, y),
            priority=EventPriority.CRITICAL,
            data={"magnitude": magnitude, "radius": radius},
            narrative=f"A volcanic eruption (VEI {int(magnitude * 8)}) occurred at ({x}, {y})",
        )

        return disasters

    def _check_floods(self, tick: int, world: World) -> list[Disaster]:
        """Check for flood events."""
        disasters: list[Disaster] = []

        if self._rng.random() >= self.config.flood_probability:
            return disasters

        # Find river-adjacent areas
        H, W = self.height, self.width
        candidates: list[tuple[int, int]] = []

        for _ in range(200):
            x = self._rng.integers(1, W - 1)
            y = self._rng.integers(1, H - 1)
            terrain = world.get_terrain(x, y)
            if terrain in (TerrainType.GRASSLAND, TerrainType.SAVANNA, TerrainType.TEMPERATE_FOREST):
                candidates.append((x, y))

        if not candidates:
            return disasters

        x, y = candidates[self._rng.integers(len(candidates))]
        magnitude = self._rng.uniform(0.2, 0.8)
        radius = int(3 + magnitude * 15)

        affected = self._get_affected_area(x, y, radius, world)

        disaster = Disaster(
            disaster_id=f"flood_{tick}_{x}_{y}",
            disaster_type="flood",
            tick=tick,
            position=Pos2D(x, y),
            magnitude=magnitude,
            affected_tiles=affected,
            casualties=self._estimate_casualties("flood", magnitude, affected, world),
            economic_damage=magnitude * len(affected) * 5.0,
            recovery_ticks=int(200 + magnitude * 500),
        )

        disasters.append(disaster)

        world.log_event(
            event_type="flood",
            position=Pos2D(x, y),
            priority=EventPriority.HIGH,
            data={"magnitude": magnitude},
            narrative=f"A flood struck the region around ({x}, {y})",
        )

        return disasters

    def _check_droughts(self, tick: int, world: World) -> list[Disaster]:
        """Check for drought events."""
        disasters: list[Disaster] = []

        if self._rng.random() >= self.config.drought_probability:
            return disasters

        # Drought affects large regions
        H, W = self.height, self.width
        x = self._rng.integers(W // 4, 3 * W // 4)
        y = self._rng.integers(H // 4, 3 * H // 4)
        radius = self._rng.integers(20, 80)

        affected = self._get_affected_area(x, y, radius, world)
        magnitude = self._rng.uniform(0.3, 0.9)

        disaster = Disaster(
            disaster_id=f"drought_{tick}_{x}_{y}",
            disaster_type="drought",
            tick=tick,
            position=Pos2D(x, y),
            magnitude=magnitude,
            affected_tiles=affected,
            casualties=self._estimate_casualties("drought", magnitude, affected, world),
            economic_damage=magnitude * len(affected) * 2.0,
            recovery_ticks=int(500 + magnitude * 1000),
        )

        disasters.append(disaster)

        world.publish_signal(
            SignalType.DISASTER_WARNING,
            source_pos=disaster.position,
            intensity=magnitude * 0.5,  # Less urgent than earthquake
            duration=200,
        )

        world.log_event(
            event_type="drought",
            position=Pos2D(x, y),
            priority=EventPriority.HIGH,
            data={"magnitude": magnitude, "region_radius": radius},
            narrative=f"A severe drought struck the region around ({x}, {y})",
        )

        return disasters

    def _check_wildfires(self, tick: int, world: World) -> list[Disaster]:
        """Check for wildfire events."""
        disasters: list[Disaster] = []

        if self._rng.random() >= self.config.wildfire_probability:
            return disasters

        # Find forested areas
        H, W = self.height, self.width
        candidates: list[tuple[int, int]] = []

        for _ in range(200):
            x = self._rng.integers(1, W - 1)
            y = self._rng.integers(1, H - 1)
            terrain = world.get_terrain(x, y)
            if terrain.is_forest:
                candidates.append((x, y))

        if not candidates:
            return disasters

        x, y = candidates[self._rng.integers(len(candidates))]
        magnitude = self._rng.uniform(0.2, 0.8)
        radius = int(5 + magnitude * 30)

        affected = self._get_affected_area(x, y, radius, world)

        disaster = Disaster(
            disaster_id=f"fire_{tick}_{x}_{y}",
            disaster_type="wildfire",
            tick=tick,
            position=Pos2D(x, y),
            magnitude=magnitude,
            affected_tiles=affected,
            casualties=self._estimate_casualties("wildfire", magnitude, affected, world),
            economic_damage=magnitude * len(affected) * 3.0,
            recovery_ticks=int(300 + magnitude * 700),
        )

        disasters.append(disaster)

        world.log_event(
            event_type="wildfire",
            position=Pos2D(x, y),
            priority=EventPriority.HIGH,
            data={"magnitude": magnitude, "affected_forest": len(affected)},
            narrative=f"A wildfire swept through the forest near ({x}, {y})",
        )

        return disasters

    def _check_plagues(self, tick: int, world: World) -> list[Disaster]:
        """Check for plague/disease outbreaks."""
        disasters: list[Disaster] = []

        if self._rng.random() >= self.config.plague_probability:
            return disasters

        # Find settlements (high-density areas)
        H, W = self.height, self.width
        x = self._rng.integers(0, W)
        y = self._rng.integers(0, H)
        radius = self._rng.integers(5, 20)

        affected = self._get_affected_area(x, y, radius, world)
        magnitude = self._rng.uniform(0.3, 0.9)

        disaster = Disaster(
            disaster_id=f"plague_{tick}_{x}_{y}",
            disaster_type="plague",
            tick=tick,
            position=Pos2D(x, y),
            magnitude=magnitude,
            affected_tiles=affected,
            casualties=self._estimate_casualties("plague", magnitude, affected, world),
            economic_damage=magnitude * len(affected) * 1.0,
            recovery_ticks=int(300 + magnitude * 500),
        )

        disasters.append(disaster)

        world.publish_signal(
            SignalType.DISASTER_WARNING,
            source_pos=disaster.position,
            intensity=magnitude * 0.7,
            duration=300,
        )

        world.log_event(
            event_type="plague",
            position=Pos2D(x, y),
            priority=EventPriority.CRITICAL,
            data={"magnitude": magnitude, "affected_settlements": len(affected)},
            narrative=f"A plague outbreak struck near ({x}, {y})",
        )

        return disasters

    def _get_affected_area(
        self, x: int, y: int, radius: int, world: World
    ) -> list[tuple[int, int]]:
        """Get list of tiles affected by a disaster."""
        affected: list[tuple[int, int]] = []
        H, W = self.height, self.width
        radius_sq = radius * radius

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy > radius_sq:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    affected.append((nx, ny))

        return affected

    def _estimate_casualties(
        self,
        disaster_type: str,
        magnitude: float,
        affected: list[tuple[int, int]],
        world: World,
    ) -> int:
        """Estimate casualties from a disaster."""
        # Base casualties from magnitude
        base_casualties = {
            "earthquake": magnitude * 500,
            "volcano": magnitude * 1000,
            "flood": magnitude * 200,
            "drought": magnitude * 100,
            "wildfire": magnitude * 100,
            "plague": magnitude * 500,
        }

        base = base_casualties.get(disaster_type, magnitude * 100)

        # Scale by affected area
        area_factor = len(affected) / 1000.0

        # Human presence factor (estimate based on terrain)
        human_density = 0.1  # Default low density
        for x, y in affected[:100]:  # Sample first 100 tiles
            terrain = world.get_terrain(x, y)
            if terrain in (TerrainType.GRASSLAND, TerrainType.SAVANNA, TerrainType.TEMPERATE_FOREST):
                human_density = max(human_density, 0.5)

        casualties = int(base * area_factor * human_density * self._rng.uniform(0.5, 1.5))
        return max(0, casualties)

    def _generate_cascades(self, disaster: Disaster, world: World) -> list[Disaster]:
        """Generate cascading disasters."""
        cascades: list[Disaster] = []

        if disaster.cascade_depth >= self.config.max_cascade_depth:
            return cascades

        # Earthquake -> Tsunami
        if disaster.disaster_type == "earthquake":
            # Check if near coast
            for x, y in disaster.affected_tiles[:20]:
                terrain = world.get_terrain(x, y)
                if terrain in (TerrainType.BEACH, TerrainType.SHALLOW_WATER):
                    cascade = Disaster(
                        disaster_id=f"tsunami_{disaster.tick}_{x}_{y}",
                        disaster_type="tsunami",
                        tick=disaster.tick + 1,
                        position=Pos2D(x, y),
                        magnitude=disaster.magnitude * 0.8,
                        affected_tiles=self._get_affected_area(x, y, 30, world),
                        casualties=self._estimate_casualties(
                            "tsunami", disaster.magnitude * 0.8,
                            self._get_affected_area(x, y, 30, world), world
                        ),
                        economic_damage=disaster.magnitude * 500,
                        recovery_ticks=2000,
                        cascade_depth=disaster.cascade_depth + 1,
                        cause_id=disaster.disaster_id,
                    )
                    cascades.append(cascade)
                    break

        # Drought -> Wildfire
        elif disaster.disaster_type == "drought":
            if self._rng.random() < 0.3:
                x, y = disaster.position.x, disaster.position.y
                # Find nearby forest
                for _ in range(50):
                    nx = self._rng.integers(x - 20, x + 20)
                    ny = self._rng.integers(y - 20, y + 20)
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        terrain = world.get_terrain(nx, ny)
                        if terrain.is_forest:
                            cascade = Disaster(
                                disaster_id=f"cascade_fire_{disaster.tick}_{nx}_{ny}",
                                disaster_type="wildfire",
                                tick=disaster.tick + 10,
                                position=Pos2D(nx, ny),
                                magnitude=disaster.magnitude * 0.7,
                                affected_tiles=self._get_affected_area(nx, ny, 25, world),
                                cascade_depth=disaster.cascade_depth + 1,
                                cause_id=disaster.disaster_id,
                            )
                            cascades.append(cascade)
                            break

        # Any major disaster -> Plague
        elif disaster.magnitude > 0.7:
            if self._rng.random() < 0.2:
                x, y = disaster.position.x, disaster.position.y
                cascade = Disaster(
                    disaster_id=f"cascade_plague_{disaster.tick}_{x}_{y}",
                    disaster_type="plague",
                    tick=disaster.tick + 50,
                    position=Pos2D(x, y),
                    magnitude=disaster.magnitude * 0.6,
                    affected_tiles=self._get_affected_area(x, y, 30, world),
                    cascade_depth=disaster.cascade_depth + 1,
                    cause_id=disaster.disaster_id,
                )
                cascades.append(cascade)

        return cascades

    def get_active_disasters(self) -> list[Disaster]:
        """Get currently active disasters."""
        return list(self._active_disasters)

    def get_disaster_history(self) -> list[Disaster]:
        """Get all past disasters."""
        return list(self._disaster_history)

    def get_stats(self) -> dict:
        """Get disaster statistics."""
        if not self._disaster_history:
            return {"total_disasters": 0}

        by_type: dict[str, int] = {}
        total_casualties = 0
        total_damage = 0.0

        for d in self._disaster_history:
            by_type[d.disaster_type] = by_type.get(d.disaster_type, 0) + 1
            total_casualties += d.casualties
            total_damage += d.economic_damage

        return {
            "total_disasters": len(self._disaster_history),
            "by_type": by_type,
            "total_casualties": total_casualties,
            "total_economic_damage": total_damage,
            "active_disasters": len(self._active_disasters),
        }
