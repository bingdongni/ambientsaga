"""
Terrain and geological generation system.

Generates realistic terrain using:
- Multi-scale Perlin noise
- Plate tectonics simulation
- Erosion modeling
- Soil formation
- Mineral deposit placement
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ambientsaga.config import TerrainConfig, WorldConfig
from ambientsaga.types import TerrainType, SoilType, MineralType, MineralDeposit, Pos2D

if TYPE_CHECKING:
    from ambientsaga.world.state import World


# ---------------------------------------------------------------------------
# Perlin Noise Implementation
# ---------------------------------------------------------------------------


class PerlinNoise:
    """
    Multi-dimensional Perlin noise generator.

    Uses permutation table for reproducibility and gradient interpolation
    for smooth terrain features.
    """

    def __init__(self, seed: int) -> None:
        self._rng = np.random.Generator(np.random.PCG64(seed))
        self._perm = self._generate_permutation()

    def _generate_permutation(self) -> np.ndarray:
        """Generate a shuffled permutation table."""
        p = np.arange(256, dtype=np.int32)
        self._rng.shuffle(p)
        return np.concatenate([p, p])

    def _fade(self, t: float) -> float:
        """Quintic fade function for smooth interpolation."""
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    def _lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation."""
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        """Compute gradient vector."""
        h = hash_val & 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise2d(self, x: float, y: float) -> float:
        """Generate 2D Perlin noise at (x, y)."""
        X = int(np.floor(x)) & 255
        Y = int(np.floor(y)) & 255
        xf = x - np.floor(x)
        yf = y - np.floor(y)

        u = self._fade(xf)
        v = self._fade(yf)

        p = self._perm
        aa = p[p[X] + Y]
        ab = p[p[X] + Y + 1]
        ba = p[p[X + 1] + Y]
        bb = p[p[X + 1] + Y + 1]

        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)

        return self._lerp(x1, x2, v)

    def noise2d_batch(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """Vectorized 2D Perlin noise for arrays of coordinates."""
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)

        X0 = np.floor(X).astype(np.int32) & 255
        Y0 = np.floor(Y).astype(np.int32) & 255
        Xf = X - np.floor(X)
        Yf = Y - np.floor(Y)
        u = self._fade_float(Xf)
        v = self._fade_float(Yf)

        p = self._perm
        aa = p[p[X0] + Y0]
        ab = p[p[X0] + Y0 + 1]
        ba = p[p[X0 + 1] + Y0]
        bb = p[p[X0 + 1] + Y0 + 1]

        grad_aa = self._grad_int(aa, Xf, Yf)
        grad_ba = self._grad_int(ba, Xf - 1, Yf)
        grad_ab = self._grad_int(ab, Xf, Yf - 1)
        grad_bb = self._grad_int(bb, Xf - 1, Yf - 1)

        x1 = self._lerp_float(grad_aa, grad_ba, u)
        x2 = self._lerp_float(grad_ab, grad_bb, u)
        return self._lerp_float(x1, x2, v)

    def _fade_float(self, t: np.ndarray) -> np.ndarray:
        """Vectorized quintic fade."""
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    def _lerp_float(self, a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Vectorized linear interpolation."""
        return a + t * (b - a)

    def _grad_int(self, hash_val: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Vectorized gradient computation."""
        h = hash_val & 3
        u = np.where(h < 2, x, y)
        v = np.where(h < 2, y, x)
        result = np.where((h & 1) == 0, u, -u) + np.where((h & 2) == 0, v, -v)
        return result.astype(float)

    def fbm(
        self,
        x: float,
        y: float,
        octaves: int = 6,
        lacunarity: float = 2.0,
        persistence: float = 0.5,
    ) -> float:
        """
        Fractal Brownian Motion — layered noise for natural terrain.

        Combines multiple octaves of noise at different scales.
        """
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return total / max_value

    def fbm_batch(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        octaves: int = 6,
        lacunarity: float = 2.0,
        persistence: float = 0.5,
    ) -> np.ndarray:
        """Vectorized FBM for arrays of coordinates."""
        total = np.zeros_like(X, dtype=float)
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise2d_batch(X * frequency, Y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return total / max_value


# ---------------------------------------------------------------------------
# Plate Tectonics
# ---------------------------------------------------------------------------


@dataclass
class Plate:
    """A tectonic plate."""

    plate_id: int
    points: np.ndarray  # [n, 2] array of grid points
    velocity: tuple[float, float]  # (vx, vy) in km/year
    plate_type: str  # "continental", "oceanic", "mixed"
    crust_thickness: float  # km
    elevation_bias: float  # Base elevation adjustment


class PlateTectonics:
    """
    Simplified plate tectonics simulation.

    Creates continental plates, oceanic plates, and their interactions.
    For computational efficiency, we use a simplified model that:
    1. Divides the world into plate regions
    2. Assigns plate properties (thickness, velocity)
    3. Computes boundary zones for mountain formation
    """

    def __init__(self, width: int, height: int, seed: int) -> None:
        self.width = width
        self.height = height
        self._rng = np.random.Generator(np.random.PCG64(seed + 999))
        self.plates: list[Plate] = []
        self._plate_map: np.ndarray | None = None

    def generate(self, num_plates: int = 8) -> np.ndarray:
        """
        Generate plate map for the world.

        Returns plate_map[y, x] = plate_id
        """
        H, W = self.height, self.width

        # Create plate seeds (centers)
        seeds_x = self._rng.integers(0, W, size=num_plates)
        seeds_y = self._rng.integers(0, H, size=num_plates)
        seeds = np.stack([seeds_x, seeds_y], axis=1)  # [num_plates, 2]

        # Vectorized Voronoi: compute all distances at once via broadcasting
        # Create coordinate grids
        y_grid, x_grid = np.mgrid[0:H, 0:W]  # [H, W]

        # Compute distance from every cell to every seed: [num_plates, H, W]
        dx = x_grid[np.newaxis, :, :] - seeds[:, 1][:, np.newaxis, np.newaxis]
        dy = y_grid[np.newaxis, :, :] - seeds[:, 0][:, np.newaxis, np.newaxis]
        dist = np.sqrt(dx * dx + dy * dy)

        # Assign nearest plate
        plate_map = np.argmin(dist, axis=0).astype(np.int32)  # [H, W]

        # Generate plate properties
        for pid in range(num_plates):
            is_continental = self._rng.random() > 0.4
            plate = Plate(
                plate_id=pid,
                points=np.array([]),
                velocity=(
                    self._rng.uniform(-5, 5),  # cm/year
                    self._rng.uniform(-5, 5),
                ),
                plate_type="continental" if is_continental else "oceanic",
                crust_thickness=(
                    self._rng.uniform(30, 50) if is_continental
                    else self._rng.uniform(5, 15)
                ),
                elevation_bias=(
                    self._rng.uniform(500, 2000) if is_continental
                    else self._rng.uniform(-3000, -500)
                ),
            )
            self.plates.append(plate)

        self._plate_map = plate_map
        self._seeds = seeds  # store for boundary detection
        return plate_map

    def get_plate_at(self, x: int, y: int) -> Plate | None:
        """Get the plate at a position."""
        if self._plate_map is None:
            return None
        pid = int(self._plate_map[y, x])
        if 0 <= pid < len(self.plates):
            return self.plates[pid]
        return None

    def is_plate_boundary(self, x: int, y: int) -> bool:
        """Check if position is near a plate boundary."""
        if self._plate_map is None:
            return False
        current = int(self._plate_map[y, x])
        neighbors = [
            (y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1),
            (y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1),
        ]
        for ny, nx in neighbors:
            if 0 <= ny < self.height and 0 <= nx < self.width:
                if int(self._plate_map[ny, nx]) != current:
                    return True
        return False

    def is_plate_boundary_batch(self, plate_map: np.ndarray) -> np.ndarray:
        """Vectorized plate boundary detection. Returns [H, W] boolean array."""
        padded = np.pad(plate_map, 1, mode='edge')
        center = plate_map
        return (
            (padded[0:-2, 0:-2] != center) |
            (padded[0:-2, 1:-1] != center) |
            (padded[0:-2, 2:] != center) |
            (padded[1:-1, 0:-2] != center) |
            (padded[1:-1, 2:] != center) |
            (padded[2:, 0:-2] != center) |
            (padded[2:, 1:-1] != center) |
            (padded[2:, 2:] != center)
        )

    def get_elevation_bias_batch(self, plate_map: np.ndarray) -> np.ndarray:
        """Vectorized plate elevation bias. Returns [H, W] float array."""
        biases = np.array([p.elevation_bias for p in self.plates], dtype=np.float64)
        return biases[plate_map]


# ---------------------------------------------------------------------------
# Erosion Model
# ---------------------------------------------------------------------------


class ErosionModel:
    """
    Hydraulic erosion simulation using stream power law.

    Models:
    - Sheet wash erosion
    - Channel erosion (stream power law)
    - Deposition in low-energy areas
    - Soil creep
    """

    def __init__(self, seed: int) -> None:
        self._rng = np.random.Generator(np.random.PCG64(seed + 7777))

    def simulate(
        self,
        elevation: np.ndarray,
        precipitation: np.ndarray,
        iterations: int = 500,
    ) -> np.ndarray:
        """
        Simulate hydraulic erosion - vectorized per iteration.

        Args:
            elevation: [H, W] elevation in meters
            precipitation: [H, W] annual precipitation in mm
            iterations: Number of erosion passes
        """
        H, W = elevation.shape
        K = 0.0001  # Erodibility coefficient
        local_rain = precipitation / precipitation.max()

        for _ in range(iterations):
            # Vectorized flow direction
            flow_dir = self._compute_flow_direction(elevation)

            # Vectorized drainage (simplified single-pass accumulation)
            drainage = self._compute_drainage(elevation, flow_dir)

            # Vectorized slope using numpy gradient
            slope = self._compute_slope(elevation)

            # Stream power law: erosion = K * drainage^0.5 * slope^2
            stream_power = K * (drainage + 1) ** 0.5 * slope ** 2
            erosion_amount = stream_power * local_rain * 0.01

            elevation -= erosion_amount
            np.maximum(elevation, 0, out=elevation)

        return elevation

    def _compute_flow_direction(self, elevation: np.ndarray) -> np.ndarray:
        """Vectorized flow direction using array shifting and argmax."""
        H, W = elevation.shape

        # Get neighbor elevations using slice indexing (avoids wraparound from np.roll)
        elev_n = np.concatenate([elevation[0:1, :], elevation[0:-1, :]], axis=0)  # row 0 repeated, then rows 0..H-2
        elev_s = np.concatenate([elevation[1:, :], elevation[-1:, :]], axis=0)
        elev_w = np.concatenate([elevation[:, 0:1], elevation[:, 0:-1]], axis=1)
        elev_e = np.concatenate([elevation[:, 1:], elevation[:, -1:]], axis=1)

        # Drop from center to each neighbor
        drop_n = elevation - elev_n
        drop_s = elevation - elev_s
        drop_w = elevation - elev_w
        drop_e = elevation - elev_e

        # Stack drops: axis 0 = neighbor, axis 1 = H, axis 2 = W
        drops = np.stack([drop_n, drop_e, drop_s, drop_w], axis=0)
        flow_dir = np.argmax(drops, axis=0).astype(np.int32)  # [H, W]

        return flow_dir

    def _compute_slope(self, elevation: np.ndarray) -> np.ndarray:
        """Vectorized slope using numpy gradient."""
        dy, dx = np.gradient(elevation.astype(np.float64))
        return np.sqrt(dx * dx + dy * dy)

    def _compute_drainage(self, elevation: np.ndarray, flow_dir: np.ndarray) -> np.ndarray:
        """Compute contributing drainage area using batch path tracing."""
        H, W = elevation.shape
        drainage = np.ones((H, W), dtype=np.float64)

        # Batch path tracing: trace multiple steps at once
        # Direction offsets: 0=north, 1=east, 2=south, 3=west
        dy = np.array([-1, 0, 1, 0], dtype=np.int32)
        dx = np.array([0, 1, 0, -1], dtype=np.int32)

        # Build next-cell lookup from flow_dir
        next_y = np.clip(np.arange(H)[:, None] + dy[flow_dir], 0, H - 1)
        next_x = np.clip(np.arange(W)[None, :] + dx[flow_dir], 0, W - 1)

        # Accumulate drainage over iterations
        for _ in range(20):
            next_drainage = drainage[next_y, next_x]
            drainage += next_drainage * 0.5
            # Clamp to prevent overflow
            drainage = np.minimum(drainage, H * W)

        return drainage


# ---------------------------------------------------------------------------
# Main Terrain Generator
# ---------------------------------------------------------------------------


class TerrainGenerator:
    """
    Generates complete terrain for the simulation world.

    Pipeline:
    1. Plate tectonics → base elevation
    2. Multi-scale Perlin noise → terrain features
    3. Erosion simulation → realistic landforms
    4. Biome assignment → terrain types
    5. Soil generation → soil types
    6. Mineral placement → resource deposits
    7. River carving → river networks
    """

    def __init__(self, config: WorldConfig, terrain_config: TerrainConfig) -> None:
        self.config = config
        self.terrain_config = terrain_config
        self.width = config.width
        self.height = config.height

        # Initialize noise generators with different seeds
        base_seed = config.seed or 42
        self._noise1 = PerlinNoise(base_seed)
        self._noise2 = PerlinNoise(base_seed + 1)
        self._noise3 = PerlinNoise(base_seed + 2)
        self._noise4 = PerlinNoise(base_seed + 3)

        self._plate_tectonics = PlateTectonics(
            self.width, self.height, base_seed + 100
        )
        self._erosion = ErosionModel(base_seed + 200)
        self._rng = np.random.Generator(np.random.PCG64(base_seed + 300))

        # Generated data
        self._elevation: np.ndarray | None = None
        self._terrain: np.ndarray | None = None
        self._soil: np.ndarray | None = None
        self._minerals: dict[tuple[int, int], MineralDeposit] = {}
        self._rivers: list[list[tuple[int, int]]] = []

    def generate(self) -> dict[str, np.ndarray | dict]:
        """
        Generate complete terrain for the world.

        Returns:
            dict with keys: terrain, elevation, soil, minerals, rivers
        """
        # Step 1: Base elevation from plates and noise
        elevation = self._generate_base_elevation()

        # Step 2: Apply erosion (vectorized - can use more iterations now)
        if self.terrain_config.erosion_iterations > 0:
            precip = np.ones_like(elevation) * 1000  # Default precipitation
            elevation = self._erosion.simulate(
                elevation, precip, iterations=self.terrain_config.erosion_iterations
            )

        self._elevation = elevation

        # Step 3: Determine sea level and assign terrain types
        terrain = self._assign_terrain_types(elevation)

        # Step 4: Generate rivers
        self._rivers = self._generate_rivers(terrain, elevation)

        # Step 5: Carve rivers into terrain
        terrain, elevation = self._carve_rivers(terrain, elevation, self._rivers)

        # Step 6: Generate soil
        soil = self._generate_soil(terrain, elevation)

        # Step 7: Place minerals
        minerals = self._place_minerals(terrain, elevation)

        self._terrain = terrain
        self._soil = soil

        return {
            "terrain": terrain,
            "elevation": elevation,
            "soil": soil,
            "minerals": minerals,
            "rivers": self._rivers,
        }

    def _generate_base_elevation(self) -> np.ndarray:
        """Generate base elevation using multi-scale noise and plate tectonics."""
        H, W = self.height, self.width

        # Generate plate map once
        plate_map = self._plate_tectonics.generate(num_plates=8)

        # Pre-compute coordinate arrays
        y_grid, x_grid = np.mgrid[0:H, 0:W]

        # Multi-scale noise at different scales
        scale1 = self.terrain_config.noise_scale_octave1
        scale2 = self.terrain_config.noise_scale_octave2
        scale3 = self.terrain_config.noise_scale_octave3
        amp1, amp2, amp3 = self.terrain_config.noise_amplitude_ratio

        # Large scale: continental vs oceanic shape
        n1 = self._noise1.fbm_batch(x_grid / scale1, y_grid / scale1, octaves=4)
        # Medium scale: regional terrain variation
        n2 = self._noise2.fbm_batch(x_grid / scale2, y_grid / scale2, octaves=4)
        # Fine scale: local detail
        n3 = self._noise3.fbm_batch(x_grid / scale3, y_grid / scale3, octaves=3)

        # Normalize each noise to [-1, 1]
        n1 = np.tanh(n1 / (np.std(n1) + 1e-6))
        n2 = np.tanh(n2 / (np.std(n2) + 1e-6))
        n3 = np.tanh(n3 / (np.std(n3) + 1e-6))

        # Mountain ranges near plate boundaries
        is_boundary = self._plate_tectonics.is_plate_boundary_batch(plate_map)
        boundary_noise = self._noise1.fbm_batch(x_grid / 60.0, y_grid / 60.0, octaves=2)
        boundary_boost = is_boundary * np.maximum(0, boundary_noise) * 500

        # Elevation formula:
        # - continental noise (n1): large-scale land/water variation
        # - regional noise (n2): lowlands vs highlands within continents
        # - detail noise (n3): fine local variation
        # - boundary boost: mountains at plate edges
        elevation = (
            n1 * 600        # large-scale: continent shapes
            + n2 * 300      # medium-scale: regional terrain
            + n3 * 100      # fine-scale: local detail
            + boundary_boost
            + 200           # base level
        )

        return elevation

    def _assign_terrain_types(self, elevation: np.ndarray) -> np.ndarray:
        """Assign terrain types based on elevation and noise - fully vectorized."""
        H, W = self.height, self.width
        # Compute sea level as a ratio of elevation range for geological realism
        elev_min = elevation.min()
        elev_max = elevation.max()
        sea_level = elev_min + self.terrain_config.sea_level * (elev_max - elev_min)

        # Pre-compute latitude and humidity maps
        y_grid, x_grid = np.mgrid[0:H, 0:W]
        latitude = np.abs(y_grid / self.height - 0.5) * 2
        humidity = self._noise4.noise2d_batch(x_grid / 50.0, y_grid / 50.0) * 0.5 + 0.5
        humidity_hills = self._noise4.noise2d_batch(x_grid / 30.0, y_grid / 30.0) * 0.5 + 0.5

        elev_offset = elevation - sea_level

        # Terrain type values
        DEEP = TerrainType.DEEP_OCEAN.value
        OCEAN = TerrainType.OCEAN.value
        BEACH = TerrainType.BEACH.value
        TROPICAL = TerrainType.TROPICAL_FOREST.value
        RAIN = TerrainType.RAINFOREST.value
        SAVANNA = TerrainType.SAVANNA.value
        DESERT = TerrainType.DESERT.value
        TEMPERATE = TerrainType.TEMPERATE_FOREST.value
        BOREAL = TerrainType.BOREAL_FOREST.value
        TUNDRA = TerrainType.TUNDRA.value
        GRASS = TerrainType.GRASSLAND.value
        HILLS = TerrainType.HILLS.value
        SCRUB = TerrainType.DESERT_SCRUB.value
        MOUNTAINS = TerrainType.MOUNTAINS.value
        HIGH = TerrainType.HIGH_MOUNTAINS.value

        # Build conditions list and choice list - MUST be same length
        conditions = [
            elev_offset < -200,  # 0: Deep ocean
            elev_offset < 0,  # 1: Ocean
            elev_offset < 5,  # 2: Beach
            # Coastal zone (5-50m): tropics (latitude <= 0.5)
            (elev_offset >= 5) & (elev_offset < 50) & (latitude <= 0.5) & (humidity > 0.7),  # 3
            (elev_offset >= 5) & (elev_offset < 50) & (latitude <= 0.5) & (humidity <= 0.7) & (humidity > 0.5),  # 4
            (elev_offset >= 5) & (elev_offset < 50) & (latitude <= 0.5) & (humidity <= 0.5) & (humidity > 0.3),  # 5
            (elev_offset >= 5) & (elev_offset < 50) & (latitude <= 0.5) & (humidity <= 0.3),  # 6
            # Coastal zone: cold (0.5 < latitude <= 0.7)
            (elev_offset >= 5) & (elev_offset < 50) & (latitude > 0.5) & (latitude <= 0.7) & (humidity > 0.5),  # 7
            (elev_offset >= 5) & (elev_offset < 50) & (latitude > 0.5) & (latitude <= 0.7) & (humidity <= 0.5),  # 8
            # Coastal zone: polar (latitude > 0.7)
            (elev_offset >= 5) & (elev_offset < 50) & (latitude > 0.7),  # 9
            # Lowlands (50-200m): tropics
            (elev_offset >= 50) & (elev_offset < 200) & (latitude <= 0.5) & (humidity > 0.6),  # 10
            (elev_offset >= 50) & (elev_offset < 200) & (latitude <= 0.5) & (humidity <= 0.6) & (humidity > 0.3),  # 11
            (elev_offset >= 50) & (elev_offset < 200) & (latitude <= 0.5) & (humidity <= 0.3),  # 12
            # Lowlands: temperate (0.5 < latitude <= 0.7)
            (elev_offset >= 50) & (elev_offset < 200) & (latitude > 0.5) & (latitude <= 0.7) & (humidity > 0.4),  # 13
            (elev_offset >= 50) & (elev_offset < 200) & (latitude > 0.5) & (latitude <= 0.7) & (humidity <= 0.4),  # 14
            # Lowlands: polar
            (elev_offset >= 50) & (elev_offset < 200) & (latitude > 0.7),  # 15
            # Hills (200-500m)
            (elev_offset >= 200) & (elev_offset < 500) & (humidity_hills > 0.5),  # 16
            (elev_offset >= 200) & (elev_offset < 500) & (humidity_hills <= 0.5),  # 17
            # Mountains (500-1000m)
            (elev_offset >= 500) & (elev_offset < 1000),  # 18
            # High mountains (>= 1000m)
            elev_offset >= 1000,  # 19
        ]

        choices = [
            DEEP, OCEAN, BEACH,
            RAIN, TROPICAL, SAVANNA, DESERT,
            BOREAL, TUNDRA, TUNDRA,
            TROPICAL, SAVANNA, DESERT,
            TEMPERATE, GRASS, TUNDRA,
            HILLS, SCRUB,
            MOUNTAINS,
            HIGH,
        ]

        assert len(conditions) == len(choices), f"{len(conditions)} conditions != {len(choices)} choices"

        terrain = np.select(conditions, choices, default=GRASS).astype(np.int32)
        return terrain

    def _classify_terrain(
        self, elevation: float, x: int, y: int, sea_level: float
    ) -> TerrainType:
        """Classify a single tile as a terrain type."""
        # Get climate modifiers from position
        latitude = abs(y / self.height - 0.5) * 2  # 0 at center, 1 at poles

        if elevation < sea_level - 200:
            return TerrainType.DEEP_OCEAN
        elif elevation < sea_level:
            return TerrainType.OCEAN
        elif elevation < sea_level + 5:
            return TerrainType.BEACH
        elif elevation < sea_level + 50:
            # Coastal zone - use humidity
            humidity = self._noise4.noise2d(x / 50.0, y / 50.0) * 0.5 + 0.5
            if latitude > 0.7:  # Polar
                return TerrainType.TUNDRA
            elif latitude > 0.5:  # Cold
                if humidity > 0.5:
                    return TerrainType.BOREAL_FOREST
                else:
                    return TerrainType.TUNDRA
            else:
                if humidity > 0.7:
                    return TerrainType.RAINFOREST
                elif humidity > 0.5:
                    return TerrainType.TROPICAL_FOREST
                elif humidity > 0.3:
                    return TerrainType.SAVANNA
                else:
                    return TerrainType.DESERT
        elif elevation < sea_level + 200:
            # Lowlands
            humidity = self._noise4.noise2d(x / 50.0, y / 50.0) * 0.5 + 0.5
            if latitude > 0.7:
                return TerrainType.TUNDRA
            elif latitude > 0.5:
                if humidity > 0.4:
                    return TerrainType.TEMPERATE_FOREST
                else:
                    return TerrainType.GRASSLAND
            else:
                if humidity > 0.6:
                    return TerrainType.TROPICAL_FOREST
                elif humidity > 0.3:
                    return TerrainType.SAVANNA
                else:
                    return TerrainType.DESERT
        elif elevation < sea_level + 500:
            # Hills
            humidity = self._noise4.noise2d(x / 30.0, y / 30.0) * 0.5 + 0.5
            if humidity > 0.5:
                return TerrainType.HILLS
            else:
                return TerrainType.DESERT_SCRUB
        elif elevation < sea_level + 1000:
            return TerrainType.MOUNTAINS
        else:
            return TerrainType.HIGH_MOUNTAINS

    def _generate_rivers(
        self, terrain: np.ndarray, elevation: np.ndarray
    ) -> list[list[tuple[int, int]]]:
        """Generate river networks using steepest descent."""
        H, W = self.height, self.width
        rivers: list[list[tuple[int, int]]] = []

        # Find all high-elevation land tiles and sort by elevation
        land_mask = np.array([
            TerrainType(t).is_land for t in terrain.flatten()
        ]).reshape(H, W)
        land_elev = np.where(land_mask, elevation, -np.inf)

        # Use quantile-based threshold for source tiles (top 5% of land elevation)
        source_threshold = np.quantile(elevation[land_mask], 0.95)
        source_positions = np.argwhere(
            land_mask & (elevation >= source_threshold)
        )

        if len(source_positions) == 0:
            return rivers

        # Shuffle and take top sources
        rng = np.random.Generator(np.random.PCG64(self._rng.integers(0, 2**31)))
        rng.shuffle(source_positions)
        source_positions = source_positions[:self.terrain_config.river_count]

        for pos in source_positions:
            sx, sy = int(pos[1]), int(pos[0])
            river: list[tuple[int, int]] = [(sx, sy)]
            cx, cy = sx, sy
            visited: set[tuple[int, int]] = {(sx, sy)}

            for _ in range(2000):  # Max river length
                min_elev = elevation[cy, cx]
                next_pos = None

                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = cx + dx, cy + dy
                        if (
                            0 <= nx < W
                            and 0 <= ny < H
                            and (nx, ny) not in visited
                        ):
                            if TerrainType(terrain[ny, nx]).is_water:
                                river.append((nx, ny))
                                break
                            if (
                                TerrainType(terrain[ny, nx]).is_land
                                and elevation[ny, nx] < min_elev
                            ):
                                min_elev = elevation[ny, nx]
                                next_pos = (nx, ny)

                if next_pos is None:
                    break

                river.append(next_pos)
                visited.add(next_pos)
                cx, cy = next_pos

            # Keep rivers that reach water and are at least 5 tiles long
            if len(river) >= 5:
                rivers.append(river)

        return rivers

    def _carve_rivers(
        self,
        terrain: np.ndarray,
        elevation: np.ndarray,
        rivers: list[list[tuple[int, int]]],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Carve river valleys into the terrain."""
        H, W = self.height, self.width
        carved = elevation.copy()

        for river in rivers:
            for i, (x, y) in enumerate(river):
                if 0 <= x < W and 0 <= y < H:
                    # Create valley
                    carve_depth = 5.0 * (1.0 - i / len(river))
                    carved[y, x] = elevation[y, x] - carve_depth

                    # Make shallow water tiles adjacent to river
                    if i > len(river) * 0.8 and TerrainType(terrain[y, x]).is_land:
                        terrain[y, x] = TerrainType.SHALLOW_WATER.value

        return terrain, carved

    def _generate_soil(
        self, terrain: np.ndarray, elevation: np.ndarray
    ) -> np.ndarray:
        """Generate soil types - fully vectorized."""
        H, W = self.height, self.width
        sea_level = np.percentile(elevation, 50)

        # Terrain type values
        DEEP = TerrainType.DEEP_OCEAN.value
        OCEAN = TerrainType.OCEAN.value
        SHALLOW = TerrainType.SHALLOW_WATER.value
        HIGH = TerrainType.HIGH_MOUNTAINS.value
        DESERT = TerrainType.DESERT.value

        is_water = (terrain == DEEP) | (terrain == OCEAN) | (terrain == SHALLOW)
        is_coastal = (~is_water) & (elevation < sea_level + 10)

        # Use vectorized noise for terrain-appropriate soil variation
        y_grid, x_grid = np.mgrid[0:H, 0:W]
        soil_noise = self._rng.random((H, W))  # Pseudo-random for variety

        soil = np.select(
            [
                is_water,
                is_coastal,
                terrain == HIGH,
                terrain == DESERT,
            ],
            [
                SoilType.ROCK.value,
                SoilType.ALLUVIAL.value if hasattr(SoilType, 'ALLUVIAL') else SoilType.LOAM.value,
                SoilType.ROCK.value,
                SoilType.SAND.value if hasattr(SoilType, 'SAND') else SoilType.LOAM.value,
            ],
            default=SoilType.LOAM.value,
        ).astype(np.int32)

        return soil

    def _place_minerals(
        self, terrain: np.ndarray, elevation: np.ndarray
    ) -> dict[tuple[int, int], MineralDeposit]:
        """Place mineral deposits - vectorized placement with randomized selection."""
        H, W = self.height, self.width
        minerals: dict[tuple[int, int], MineralDeposit] = {}

        # Mineral placement rules: (terrain values, mineral types, probability)
        placement_rules = [
            (
                frozenset([TerrainType.MOUNTAINS.value, TerrainType.HIGH_MOUNTAINS.value]),
                [MineralType.IRON_ORE, MineralType.COPPER_ORE],
                0.02,
            ),
            (
                frozenset([TerrainType.HILLS.value, TerrainType.MOUNTAINS.value]),
                [MineralType.GOLD_ORE, MineralType.SILVER_ORE],
                0.005,
            ),
            (
                frozenset([TerrainType.BEACH.value, TerrainType.SHALLOW_WATER.value]),
                [MineralType.SALT, MineralType.FLINT],
                0.01,
            ),
            (
                frozenset([TerrainType.GRASSLAND.value, TerrainType.SAVANNA.value]),
                [MineralType.CLAY, MineralType.LIMESTONE],
                0.03,
            ),
            (
                frozenset([TerrainType.DESERT.value]),
                [MineralType.SALT, MineralType.SULFUR],
                0.01,
            ),
            (
                frozenset([TerrainType.PLATEAU.value]),
                [MineralType.COAL, MineralType.IRON_ORE],
                0.01,
            ),
        ]

        # Vectorized placement: for each rule, compute a probability mask
        # and randomly select positions using the rng
        for terrain_set, mineral_types, prob in placement_rules:
            # Create terrain mask: which cells match this rule
            terrain_mask = np.isin(terrain, list(terrain_set))

            # Generate random values for placement
            random_values = self._rng.random((H, W))

            # Create placement mask: terrain matches AND passes probability check
            placement_mask = terrain_mask & (random_values < prob)

            # Find all positions that pass
            y_indices, x_indices = np.where(placement_mask)

            # Create MineralDeposit for each selected position
            for ix, iy in zip(x_indices, y_indices):
                minerals[(ix, iy)] = MineralDeposit(
                    position=Pos2D(ix, iy),
                    mineral_type=self._rng.choice(mineral_types),
                    richness=self._rng.uniform(0.3, 0.9),
                    depth=self._rng.uniform(1, 50),
                    remaining=self._rng.uniform(100, 1000),
                )

        return minerals

    def get_elevation(self) -> np.ndarray | None:
        return self._elevation

    def get_terrain(self) -> np.ndarray | None:
        return self._terrain

    def get_soil(self) -> np.ndarray | None:
        return self._soil

    def get_minerals(self) -> dict[tuple[int, int], MineralDeposit]:
        return self._minerals

    def get_rivers(self) -> list[list[tuple[int, int]]]:
        return self._rivers

    def get_biome_color(self, terrain_type: TerrainType) -> tuple[int, int, int]:
        """Get RGB color for terrain visualization."""
        colors = {
            TerrainType.DEEP_OCEAN: (0, 30, 80),
            TerrainType.OCEAN: (0, 50, 120),
            TerrainType.SHALLOW_WATER: (30, 100, 150),
            TerrainType.BEACH: (220, 210, 160),
            TerrainType.DESERT: (220, 200, 120),
            TerrainType.DESERT_SCRUB: (180, 160, 100),
            TerrainType.GRASSLAND: (100, 160, 60),
            TerrainType.SAVANNA: (150, 180, 80),
            TerrainType.SHRUBLAND: (120, 140, 80),
            TerrainType.TEMPERATE_FOREST: (50, 120, 60),
            TerrainType.TROPICAL_FOREST: (30, 90, 40),
            TerrainType.BOREAL_FOREST: (30, 70, 40),
            TerrainType.RAINFOREST: (20, 70, 30),
            TerrainType.TUNDRA: (180, 200, 210),
            TerrainType.MARSH: (60, 100, 80),
            TerrainType.SWAMP: (40, 80, 60),
            TerrainType.HILLS: (100, 90, 70),
            TerrainType.MOUNTAINS: (120, 110, 100),
            TerrainType.HIGH_MOUNTAINS: (180, 170, 160),
            TerrainType.PLATEAU: (140, 130, 110),
            TerrainType.CAVE: (50, 40, 35),
        }
        return colors.get(terrain_type, (128, 128, 128))
