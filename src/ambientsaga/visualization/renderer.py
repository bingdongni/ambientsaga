"""
Visualization renderer — 2D canvas-based world renderer.

Provides multiple rendering modes:
- Terrain: colored terrain/biome view
- Temperature: heatmap of temperature
- Population: density of agents
- Social: agent relationships and networks
- Activity: recent agent activity heatmap
- Resources: resource distribution overlay
- Signals: active signal propagation

The renderer outputs to:
- NumPy arrays (for analysis/export)
- Pillow Images (for file export)
- Tkinter Canvas (for interactive display)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.types import TerrainType

if TYPE_CHECKING:
    from ambientsaga.config import VisualizationConfig
    from ambientsaga.world.state import World


# ---------------------------------------------------------------------------
# Color Palettes
# ---------------------------------------------------------------------------

# Terrain color palette (RGB values)
TERRAIN_COLORS: dict[TerrainType, tuple[int, int, int]] = {
    TerrainType.DEEP_OCEAN: (10, 30, 80),
    TerrainType.OCEAN: (20, 60, 120),
    TerrainType.SHALLOW_WATER: (40, 100, 160),
    TerrainType.BEACH: (220, 210, 160),
    TerrainType.DESERT: (237, 201, 130),
    TerrainType.DESERT_SCRUB: (200, 180, 120),
    TerrainType.GRASSLAND: (140, 190, 80),
    TerrainType.SAVANNA: (160, 180, 80),
    TerrainType.TEMPERATE_FOREST: (50, 120, 50),
    TerrainType.BOREAL_FOREST: (30, 80, 40),
    TerrainType.TROPICAL_FOREST: (25, 90, 35),
    TerrainType.RAINFOREST: (15, 70, 25),
    TerrainType.MARSH: (30, 80, 60),
    TerrainType.SWAMP: (30, 80, 60),
    TerrainType.HILLS: (130, 110, 80),
    TerrainType.MOUNTAINS: (100, 90, 70),
    TerrainType.HIGH_MOUNTAINS: (150, 150, 160),
    TerrainType.PLATEAU: (160, 140, 120),
    TerrainType.CAVE: (60, 50, 45),
}

# Temperature color palette (blue to red)
TEMP_COLORS = [
    (20, 20, 180),   # Very cold
    (40, 60, 200),   # Cold
    (80, 120, 220),  # Cool
    (120, 160, 220), # Mild cool
    (180, 200, 180), # Mild
    (220, 220, 140), # Warm
    (240, 180, 80),  # Hot
    (220, 120, 40),  # Very hot
    (180, 60, 20),   # Extreme
]

# Population density colors (transparent to opaque green)
POP_COLORS = [
    (0, 200, 50, 0),      # Very sparse
    (0, 200, 50, 50),
    (0, 200, 50, 100),
    (0, 200, 50, 150),
    (0, 200, 50, 200),
    (0, 200, 50, 255),    # Dense
]

# Agent tier colors
TIER_COLORS = {
    1: (255, 215, 0),    # Gold for L1 Core
    2: (100, 200, 255),  # Blue for L2 Functional
    3: (150, 150, 150),  # Gray for L3 Background
    4: (80, 80, 80),     # Dark gray for L4 Ecological
}


# ---------------------------------------------------------------------------
# Rendering Modes
# ---------------------------------------------------------------------------


class RenderMode(Enum):
    """Available rendering modes."""

    TERRAIN = auto()       # Standard terrain/biome view
    PSEUDO_3D = auto()    # Pseudo-3D terrain with height shading
    TEMPERATURE = auto()   # Temperature heatmap
    POPULATION = auto()     # Agent density heatmap
    ACTIVITY = auto()       # Recent activity heatmap
    SIGNALS = auto()        # Active signal overlay
    SOCIAL_NETWORK = auto()  # Agent relationship network
    WEALTH = auto()         # Wealth distribution
    HAPPINESS = auto()      # Happiness distribution
    CULTURE = auto()        # Cultural region view


# ---------------------------------------------------------------------------
# RenderStats — rendering statistics
# ---------------------------------------------------------------------------


@dataclass
class RenderStats:
    """Statistics about the last render."""

    render_time_ms: float
    pixels_rendered: int
    agents_rendered: int
    signals_rendered: int
    chunks_rendered: int


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class Renderer:
    """
    Main rendering engine for the simulation world.

    Renders the world state to a numpy array that can be:
    - Displayed using PIL/Pillow
    - Saved as an image file
    - Displayed using Tkinter
    - Streamed to a web client

    Supports multiple render modes and camera/zoom controls.
    """

    def __init__(
        self,
        world: World,
        config: VisualizationConfig,
        seed: int = 42,
    ) -> None:
        self.world = world
        self.config = config
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Camera
        self._camera_x: float = 0.0
        self._camera_y: float = 0.0
        self._target_camera_x: float = 0.0
        self._target_camera_y: float = 0.0
        self._zoom: float = 1.0
        self._target_zoom: float = 1.0

        # Rendering mode
        self._mode: RenderMode = RenderMode.TERRAIN

        # Activity heatmap (rolling)
        self._activity_map: np.ndarray | None = None
        self._activity_decay: float = 0.95

        # Signal overlay cache
        self._signal_cache: np.ndarray | None = None

        # Rendered image cache
        self._cached_image: np.ndarray | None = None
        self._cache_tick: int = -1
        self._previous_image: np.ndarray | None = None

        # Frame interpolation (animation support)
        self._interpolation_factor: float = 0.0
        self._enable_animation: bool = True
        self._frame_lerp_speed: float = 0.15

        # Performance tracking
        self._last_render_time: float = 0.0

    def set_camera(self, x: float, y: float) -> None:
        """Set the camera center position."""
        self._camera_x = x
        self._camera_y = y

    def pan(self, dx: float, dy: float) -> None:
        """Pan the camera by the given offset."""
        self._camera_x += dx
        self._camera_y += dy

        # Clamp to world bounds
        w = self.world._config.world.width
        h = self.world._config.world.height
        self._camera_x = max(0, min(w - 1, self._camera_x))
        self._camera_y = max(0, min(h - 1, self._camera_y))

    def set_zoom(self, zoom: float) -> None:
        """Set the zoom level (1.0 = full world, higher = zoomed in)."""
        self._zoom = max(0.1, min(10.0, zoom))

    def set_mode(self, mode: RenderMode) -> None:
        """Set the rendering mode."""
        self._mode = mode

    def render(self, force: bool = False) -> np.ndarray:
        """
        Render the current world state.

        Returns a uint8 numpy array of shape (height, width, 3) in RGB format.
        """
        import time

        t0 = time.perf_counter()

        # Update camera animation for smooth transitions
        self._update_camera_animation()

        # Check cache
        if (
            not force
            and self._cached_image is not None
            and self._cache_tick == self.world.tick
        ):
            return self._cached_image

        # Determine render dimensions
        w = self.world._config.world.width
        h = self.world._config.world.height

        # Apply zoom (render at lower resolution when zoomed out)
        render_w = max(64, int(w / self._zoom))
        render_h = max(64, int(h / self._zoom))

        # Camera viewport
        cx = int(self._camera_x)
        cy = int(self._camera_y)

        # Render based on mode
        if self._mode == RenderMode.TERRAIN:
            image = self._render_terrain(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.PSEUDO_3D:
            image = self._render_terrain_3d(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.TEMPERATURE:
            image = self._render_temperature(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.POPULATION:
            image = self._render_population(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.ACTIVITY:
            image = self._render_activity(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.SIGNALS:
            image = self._render_signals(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.WEALTH:
            image = self._render_wealth(render_w, render_h, cx, cy)
        elif self._mode == RenderMode.HAPPINESS:
            image = self._render_happiness(render_w, render_h, cx, cy)
        else:
            image = self._render_terrain(render_w, render_h, cx, cy)

        # Always overlay agents on top
        if self.config.show_biome or self._mode != RenderMode.TERRAIN:
            image = self._overlay_agents(image, render_w, render_h, cx, cy)

        # Upscale to window size if needed
        if render_w != self.config.window_width or render_h != self.config.window_height:
            image = self._resize_image(
                image,
                self.config.window_width,
                self.config.window_height,
            )

        # Apply frame interpolation for smooth animation
        previous = self._cached_image
        image = self._interpolate_frames(image, previous)
        self._previous_image = previous

        self._cached_image = image
        self._cache_tick = self.world.tick
        self._last_render_time = (time.perf_counter() - t0) * 1000

        return image

    def _render_terrain(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render the terrain/biome view."""
        image = np.zeros((height, width, 3), dtype=np.uint8)

        terrain = self.world._terrain
        if terrain is None:
            return image

        w = self.world._config.world.width
        h = self.world._config.world.height

        for py in range(height):
            ty = (cy - height // 2 + py) % h
            for px in range(width):
                tx = (cx - width // 2 + px) % w

                terrain_type = TerrainType(terrain[ty, tx])
                color = TERRAIN_COLORS.get(terrain_type, (128, 128, 128))

                image[py, px] = color

        return image

    def _render_temperature(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render a temperature heatmap."""
        image = np.zeros((height, width, 3), dtype=np.uint8)

        climate = self.world._climate
        if climate is None or climate._current_temp is None:
            return self._render_terrain(width, height, cx, cy)

        temp = climate._current_temp
        w = self.world._config.world.width
        h = self.world._config.world.height

        min_temp = temp.min()
        max_temp = temp.max()
        temp_range = max(0.1, max_temp - min_temp)

        for py in range(height):
            ty = (cy - height // 2 + py) % h
            for px in range(width):
                tx = (cx - width // 2 + px) % w

                t_norm = (temp[ty, tx] - min_temp) / temp_range
                t_idx = min(len(TEMP_COLORS) - 1, int(t_norm * (len(TEMP_COLORS) - 1)))
                image[py, px] = TEMP_COLORS[t_idx]

        return image

    def _render_population(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render agent density heatmap."""
        # Start with dark base
        image = np.full((height, width, 3), 20, dtype=np.uint8)

        w = self.world._config.world.width
        h = self.world._config.world.height

        # Build density map
        density = np.zeros((h, w), dtype=np.float32)

        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue
            x = int(agent.position.x) % w
            y = int(agent.position.y) % h
            # Gaussian kernel for smooth density
            radius = 5
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny = (y + dy) % h
                    nx = (x + dx) % w
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist <= radius:
                        density[ny, nx] += (1.0 - dist / radius) * 0.1

        # Render density
        max_density = max(1.0, density.max())
        for py in range(height):
            ty = (cy - height // 2 + py) % h
            for px in range(width):
                tx = (cx - width // 2 + px) % w

                d_norm = min(1.0, density[ty, tx] / max_density)
                idx = int(d_norm * (len(POP_COLORS) - 1))
                color = POP_COLORS[idx]
                if len(color) == 4:
                    image[py, px] = color[:3]
                else:
                    image[py, px] = color

        return image

    def _render_activity(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render recent activity heatmap."""
        # Initialize or update activity map
        w = self.world._config.world.width
        h = self.world._config.world.height

        if self._activity_map is None:
            self._activity_map = np.zeros((h, w), dtype=np.float32)

        # Decay
        self._activity_map *= self._activity_decay

        # Add current activity
        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue
            x = int(agent.position.x) % w
            y = int(agent.position.y) % h
            self._activity_map[y, x] += 1.0

        # Render
        image = np.full((height, width, 3), 10, dtype=np.uint8)
        max_act = max(1.0, self._activity_map.max())

        for py in range(height):
            ty = (cy - height // 2 + py) % h
            for px in range(width):
                tx = (cx - width // 2 + px) % w

                a_norm = min(1.0, self._activity_map[ty, tx] / max_act)
                intensity = int(a_norm * 200)
                image[py, px] = [intensity // 3, intensity, intensity // 2]

        return image

    def _render_signals(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render active signal overlay."""
        # Start with terrain
        image = self._render_terrain(width, height, cx, cy)

        # Overlay signals
        signal_bus = self.world._signal_bus
        if signal_bus is None:
            return image

        w = self.world._config.world.width
        h = self.world._config.world.height

        # Signal colors by type
        signal_colors: dict[str, tuple[int, int, int]] = {
            "EVENT": (255, 200, 0),
            "CONFLICT": (255, 50, 50),
            "DISCOVERY": (100, 255, 100),
            "TRADE": (200, 200, 50),
            "DISASTER_WARNING": (255, 100, 0),
            "CULTURAL": (200, 100, 255),
            "POLITICAL": (100, 200, 255),
        }

        # Render signal positions
        for signal in signal_bus._active_signals:
            sx = int(signal.source_pos.x) % w
            sy = int(signal.source_pos.y) % h

            # Check if in viewport
            if abs(sx - cx) > width or abs(sy - cy) > height:
                continue

            color = signal_colors.get(signal.signal_type.name, (255, 255, 255))

            # Render signal radius
            radius = int(signal.radius)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > radius:
                        continue
                    ny = (sy + dy) % h
                    nx = (sx + dx) % w
                    py = ny - (cy - height // 2)
                    px = nx - (cx - width // 2)
                    if 0 <= py < height and 0 <= px < width:
                        alpha = 1.0 - dist / radius
                        alpha *= signal.intensity * 0.5
                        existing = image[py, px].astype(float)
                        image[py, px] = np.clip(
                            existing + np.array(color) * alpha, 0, 255
                        ).astype(np.uint8)

        return image

    def _render_wealth(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render wealth distribution heatmap."""
        image = np.full((height, width, 3), 20, dtype=np.uint8)

        w = self.world._config.world.width
        h = self.world._config.world.height

        # Build wealth map
        wealth_map = np.zeros((h, w), dtype=np.float32)
        count_map = np.zeros((h, w), dtype=np.float32)

        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue
            x = int(agent.position.x) % w
            y = int(agent.position.y) % h
            wealth_map[y, x] += agent.wealth
            count_map[y, x] += 1

        # Average wealth
        avg_wealth = np.divide(
            wealth_map, count_map, out=np.zeros_like(wealth_map), where=count_map > 0
        )

        if avg_wealth.max() > 0:
            max_w = avg_wealth.max()
            for py in range(height):
                ty = (cy - height // 2 + py) % h
                for px in range(width):
                    tx = (cx - width // 2 + px) % w
                    w_norm = min(1.0, avg_wealth[ty, tx] / max_w)

                    # Green = low, yellow = medium, purple = high
                    if w_norm < 0.33:
                        image[py, px] = (
                            int(50 + w_norm * 3 * 100),
                            int(200 + w_norm * 3 * 55),
                            50,
                        )
                    elif w_norm < 0.66:
                        image[py, px] = (
                            int(200 - (w_norm - 0.33) * 3 * 50),
                            int(200 - (w_norm - 0.33) * 3 * 50),
                            100,
                        )
                    else:
                        image[py, px] = (
                            int(150 + (w_norm - 0.66) * 3 * 105),
                            int(50 + (w_norm - 0.66) * 3 * 50),
                            int(150 + (w_norm - 0.66) * 3 * 105),
                        )

        return image

    def _get_agent_happiness(self, agent: Any) -> float:
        """Get happiness from an agent (handles missing emotional_state)."""
        if hasattr(agent, "emotional_state") and hasattr(agent.emotional_state, "happiness"):
            return agent.emotional_state.happiness
        # Fallback: derive from health
        if hasattr(agent, "health"):
            return agent.health - 0.5
        return 0.0

    def _render_happiness(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render happiness distribution."""
        image = np.full((height, width, 3), 128, dtype=np.uint8)

        w = self.world._config.world.width
        h = self.world._config.world.height

        happiness_map = np.zeros((h, w), dtype=np.float32)
        count_map = np.zeros((h, w), dtype=np.float32)

        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue
            x = int(agent.position.x) % w
            y = int(agent.position.y) % h
            happiness_map[y, x] += self._get_agent_happiness(agent)
            count_map[y, x] += 1

        avg_happiness = np.divide(
            happiness_map, count_map, out=np.zeros_like(happiness_map), where=count_map > 0
        )

        for py in range(height):
            ty = (cy - height // 2 + py) % h
            for px in range(width):
                tx = (cx - width // 2 + px) % w

                if count_map[ty, tx] == 0:
                    continue

                h_norm = (avg_happiness[ty, tx] + 1.0) / 2.0  # -1 to 1 -> 0 to 1

                # Blue = unhappy, gray = neutral, orange/yellow = happy
                if h_norm < 0.5:
                    intensity = int((0.5 - h_norm) * 2 * 200)
                    image[py, px] = [intensity // 2, intensity // 4, intensity]
                else:
                    intensity = int((h_norm - 0.5) * 2 * 200)
                    image[py, px] = [intensity, intensity, int(intensity * 0.3)]

        return image

    def _overlay_agents(
        self,
        image: np.ndarray,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Overlay agents on the rendered image."""
        w = self.world._config.world.width
        h = self.world._config.world.height

        agents_rendered = 0

        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue

            ax = int(agent.position.x) % w
            ay = int(agent.position.y) % h

            # Check if in viewport
            dx = ax - cx
            dy = ay - cy

            # With zoom, agents appear at different scales
            scale = max(1, int(2 / self._zoom))

            for sy in range(-scale, scale + 1):
                for sx in range(-scale, scale + 1):
                    py = height // 2 + dy + sy
                    px = width // 2 + dx + sx

                    if 0 <= py < height and 0 <= px < width:
                        # Distance from center of agent
                        dist = math.sqrt(sx * sx + sy * sy)
                        if dist <= scale:
                            # Get tier color
                            tier = getattr(agent, "tier", 3)
                            color = TIER_COLORS.get(tier, (150, 150, 150))

                            # Brighten the pixel
                            alpha = 1.0 - dist / max(1, scale)
                            image[py, px] = np.clip(
                                np.array(color) * alpha + image[py, px] * (1 - alpha),
                                0,
                                255,
                            ).astype(np.uint8)

            agents_rendered += 1

        return image

    def _resize_image(
        self, image: np.ndarray, target_w: int, target_h: int
    ) -> np.ndarray:
        """Resize image using simple nearest-neighbor scaling."""
        h, w = image.shape[:2]

        # Simple nearest-neighbor resize
        result = np.zeros((target_h, target_w, 3), dtype=np.uint8)

        for py in range(target_h):
            src_y = int(py * h / target_h)
            for px in range(target_w):
                src_x = int(px * w / target_w)
                result[py, px] = image[src_y, src_x]

        return result

    def get_stats(self) -> RenderStats:
        """Get rendering statistics."""
        return RenderStats(
            render_time_ms=self._last_render_time,
            pixels_rendered=self.config.window_width * self.config.window_height,
            agents_rendered=len(self.world.get_all_agents()),
            signals_rendered=(
                len(self.world._signal_bus._active_signals)
                if self.world._signal_bus
                else 0
            ),
            chunks_rendered=0,
        )

    def save_image(self, path: str, force: bool = True) -> None:
        """Save the current render to an image file."""
        image = self.render(force=force)
        self._save_numpy_as_image(image, path)

    def _save_numpy_as_image(self, image: np.ndarray, path: str) -> None:
        """Save a numpy array as an image file."""
        try:
            from PIL import Image

            pil_img = Image.fromarray(image, mode="RGB")
            pil_img.save(path)
        except ImportError:
            # Fallback: save as PPM (plain text)
            h, w = image.shape[:2]
            with open(path, "w") as f:
                f.write(f"P3\n{w} {h}\n255\n")
                for row in image:
                    for pixel in row:
                        f.write(f"{pixel[0]} {pixel[1]} {pixel[2]}\n")

    # ===========================================================================
    # 3D Rendering (Pseudo-3D with heightmap shading)
    # ===========================================================================

    def _render_terrain_3d(
        self,
        width: int,
        height: int,
        cx: int,
        cy: int,
    ) -> np.ndarray:
        """Render terrain with pseudo-3D height-based shading."""
        image = np.zeros((height, width, 3), dtype=np.uint8)

        terrain = self.world._terrain
        elevation = self.world._elevation
        if terrain is None or elevation is None:
            return self._render_terrain(width, height, cx, cy)

        w = self.world._config.world.width
        h = self.world._config.world.height

        # Lighting direction (from top-left)
        light_dir_x = -1.0
        light_dir_y = -1.0
        light_dir_z = 1.0
        light_mag = math.sqrt(light_dir_x**2 + light_dir_y**2 + light_dir_z**2)
        light_dir_x /= light_mag
        light_dir_y /= light_mag
        light_dir_z /= light_mag

        # Pre-compute elevation gradient
        grad_x = np.zeros((h, w), dtype=np.float32)
        grad_y = np.zeros((h, w), dtype=np.float32)

        for py in range(h):
            for px in range(w):
                # Simple gradient using neighbors
                left_x = (px - 1) % w
                right_x = (px + 1) % w
                top_y = (py - 1) % h
                bottom_y = (py + 1) % h

                grad_x[py, px] = elevation[py, right_x] - elevation[py, left_x]
                grad_y[py, px] = elevation[bottom_y, px] - elevation[top_y, px]

        # Normalize gradients
        grad_scale = 10.0
        grad_x /= grad_scale
        grad_y /= grad_scale

        max_elev = max(0.001, elevation.max())

        for py in range(height):
            ty = (cy - height // 2 + py) % h
            for px in range(width):
                tx = (cx - width // 2 + px) % w

                terrain_type = TerrainType(terrain[ty, tx])
                base_color = np.array(TERRAIN_COLORS.get(terrain_type, (128, 128, 128)), dtype=np.float32)

                # Get height for shading
                elev = elevation[ty, tx]
                height_factor = elev / max_elev

                # Calculate normal from gradients (simplified)
                nx = grad_x[ty, tx]
                ny = grad_y[ty, tx]
                nz = 1.0
                n_mag = math.sqrt(nx**2 + ny**2 + nz**2)
                nx /= n_mag
                ny /= n_mag
                nz /= n_mag

                # Diffuse lighting
                diffuse = max(0.0, nx * light_dir_x + ny * light_dir_y + nz * light_dir_z)

                # Ambient + diffuse lighting
                ambient = 0.3
                lighting = ambient + diffuse * 0.7

                # Apply lighting with height boost
                final_color = base_color * lighting * (0.8 + height_factor * 0.4)

                # Clamp to 0-255
                image[py, px] = np.clip(final_color, 0, 255).astype(np.uint8)

        return image

    # ===========================================================================
    # Animation Support (Frame interpolation)
    # ===========================================================================

    def enable_animation(self, enabled: bool) -> None:
        """Enable or disable frame animation."""
        self._enable_animation = enabled

    def set_zoom(self, zoom: float) -> None:
        """Set the zoom level (1.0 = full world, higher = zoomed in)."""
        self._target_zoom = max(0.1, min(10.0, zoom))
        self._zoom = self._target_zoom

    def set_camera(self, x: float, y: float) -> None:
        """Set the target camera center position."""
        self._target_camera_x = x
        self._target_camera_y = y
        self._camera_x = x
        self._camera_y = y

    def pan(self, dx: float, dy: float) -> None:
        """Pan the camera by the given offset."""
        self._target_camera_x += dx
        self._target_camera_y += dy

        # Clamp to world bounds
        w = self.world._config.world.width
        h = self.world._config.world.height
        self._target_camera_x = max(0, min(w - 1, self._target_camera_x))
        self._target_camera_y = max(0, min(h - 1, self._target_camera_y))

    def _update_camera_animation(self) -> None:
        """Update camera position with smooth interpolation."""
        if not self._enable_animation:
            self._camera_x = self._target_camera_x
            self._camera_y = self._target_camera_y
            self._zoom = self._target_zoom
            return

        # Smooth interpolation
        self._camera_x += (self._target_camera_x - self._camera_x) * self._frame_lerp_speed
        self._camera_y += (self._target_camera_y - self._camera_y) * self._frame_lerp_speed
        self._zoom += (self._target_zoom - self._zoom) * self._frame_lerp_speed

    def _interpolate_frames(self, current: np.ndarray, previous: np.ndarray | None) -> np.ndarray:
        """Interpolate between current and previous frame for smooth animation."""
        if not self._enable_animation or previous is None:
            return current

        if previous.shape != current.shape:
            return current

        # Linear interpolation
        self._interpolation_factor = min(1.0, self._interpolation_factor + self._frame_lerp_speed)
        return (current.astype(np.float32) * self._interpolation_factor +
                 previous.astype(np.float32) * (1.0 - self._interpolation_factor)).astype(np.uint8)

    # ===========================================================================
    # Multi-View Dashboard
    # ===========================================================================

    def render_dashboard(self, view_modes: list[RenderMode] | None = None) -> np.ndarray:
        """
        Render a multi-view dashboard with multiple views arranged in a grid.

        Args:
            view_modes: List of render modes to display. Defaults to common views.

        Returns:
            Dashboard image as uint8 numpy array (height, width, 3).
        """
        if view_modes is None:
            view_modes = [
                RenderMode.TERRAIN,
                RenderMode.POPULATION,
                RenderMode.ACTIVITY,
                RenderMode.WEALTH,
            ]

        num_views = len(view_modes)

        # Calculate grid layout
        if num_views <= 2:
            cols, rows = num_views, 1
        elif num_views <= 4:
            cols, rows = 2, 2
        else:
            cols, rows = 3, (num_views + 2) // 3

        # View dimensions (with padding for labels)
        view_w = self.config.window_width // cols
        view_h = self.config.window_height // rows
        label_h = 30

        # Create dashboard
        dashboard_h = rows * view_h
        dashboard_w = cols * view_w
        dashboard = np.full((dashboard_h, dashboard_w, 3), 20, dtype=np.uint8)

        # Render each view
        for i, mode in enumerate(view_modes):
            row = i // cols
            col = i % cols

            # Set mode and render
            old_mode = self._mode
            self._mode = mode
            view_image = self.render()

            # Resize to fit view
            view_image = self._resize_image(view_image, view_w, view_h - label_h)

            # Add label
            label = np.full((label_h, view_w, 3), 40, dtype=np.uint8)
            mode_name = mode.name.replace("_", " ")
            # Simple text rendering would require PIL, so just use background color

            # Combine label and view
            view_with_label = np.vstack([label, view_image])

            # Place in dashboard
            y_start = row * view_h
            x_start = col * view_w
            dashboard[y_start:y_start + view_h, x_start:x_start + view_w] = view_with_label

            self._mode = old_mode

        return dashboard

    def render_with_minimap(
        self,
        minimap_size: int = 150,
        minimap_position: str = "bottom-right",
    ) -> np.ndarray:
        """
        Render the main view with a minimap overlay.

        Args:
            minimap_size: Size of the minimap in pixels.
            minimap_position: Position of minimap ('top-right', 'bottom-right', etc.)

        Returns:
            Main view with minimap overlay.
        """
        # Render main view
        main_view = self.render()

        # Render minimap (terrain overview)
        old_mode = self._mode
        self._mode = RenderMode.POPULATION
        minimap = self.render(force=True)
        self._mode = old_mode

        # Resize minimap
        minimap = self._resize_image(minimap, minimap_size, minimap_size)

        # Create overlay with transparency
        overlay = np.zeros((minimap_size, minimap_size, 4), dtype=np.uint8)
        overlay[:, :, :3] = minimap
        overlay[:, :, 3] = 180  # Semi-transparent

        # Draw viewport rectangle
        w = self.world._config.world.width
        h = self.world._config.world.height

        # Calculate viewport bounds
        view_w = w / self._zoom
        view_h = h / self._zoom
        vp_x = (self._camera_x - view_w / 2) / w * minimap_size
        vp_y = (self._camera_y - view_h / 2) / h * minimap_size
        vp_w = view_w / w * minimap_size
        vp_h = view_h / h * minimap_size

        # Draw rectangle
        vp_x = int(max(0, min(minimap_size - 1, vp_x)))
        vp_y = int(max(0, min(minimap_size - 1, vp_y)))
        vp_w = int(min(minimap_size - vp_x, max(1, vp_w)))
        vp_h = int(min(minimap_size - vp_y, max(1, vp_h)))

        overlay[vp_y:vp_y + vp_h, vp_x, :] = [255, 255, 255, 255]
        overlay[vp_y:vp_y + vp_h, vp_x + vp_w - 1, :] = [255, 255, 255, 255]
        overlay[vp_y, vp_x:vp_x + vp_w, :] = [255, 255, 255, 255]
        overlay[vp_y + vp_h - 1, vp_x:vp_x + vp_w, :] = [255, 255, 255, 255]

        # Composite onto main view
        result = main_view.copy()
        h_main, w_main = main_view.shape[:2]

        if minimap_position == "bottom-right":
            x_offset = w_main - minimap_size - 10
            y_offset = h_main - minimap_size - 10
        elif minimap_position == "top-right":
            x_offset = w_main - minimap_size - 10
            y_offset = 10
        elif minimap_position == "bottom-left":
            x_offset = 10
            y_offset = h_main - minimap_size - 10
        else:  # top-left
            x_offset = 10
            y_offset = 10

        # Alpha blend minimap
        for y in range(minimap_size):
            for x in range(minimap_size):
                py = y_offset + y
                px = x_offset + x
                if 0 <= py < h_main and 0 <= px < w_main:
                    alpha = overlay[y, x, 3] / 255.0
                    for c in range(3):
                        result[py, px, c] = int(
                            overlay[y, x, c] * alpha + main_view[py, px, c] * (1 - alpha)
                        )

        return result


# ---------------------------------------------------------------------------
# Canvas Renderer — Tkinter-based interactive renderer
# ---------------------------------------------------------------------------


class CanvasRenderer(Renderer):
    """
    Tkinter Canvas-based interactive renderer.

    Extends the base Renderer with Tkinter integration for
    real-time interactive display.
    """

    def __init__(
        self,
        world: World,
        config: VisualizationConfig,
        canvas=None,
        seed: int = 42,
    ) -> None:
        super().__init__(world, config, seed)
        self._canvas = canvas
        self._running = False

    def start(self) -> None:
        """Start the interactive renderer."""
        try:
            import tkinter as tk
        except ImportError:
            return  # No Tkinter available

        self._running = True
        self._render_loop()

    def _render_loop(self) -> None:
        """Main rendering loop."""
        if not self._running:
            return

        image = self.render()
        self._update_canvas(image)

        # Schedule next frame

        if self._canvas:
            delay = int(1000 / max(1, self.config.fps_target))
            self._canvas.after(delay, self._render_loop)

    def _update_canvas(self, image: np.ndarray) -> None:
        """Update the Tkinter canvas with the rendered image."""
        if self._canvas is None:
            return

        try:
            from PIL import Image, ImageTk

            pil_img = Image.fromarray(image, mode="RGB")
            tk_img = ImageTk.PhotoImage(pil_img)

            # Update canvas
            self._canvas.create_image(0, 0, anchor="nw", image=tk_img)
            self._canvas.image = tk_img  # Keep reference
        except Exception:
            pass  # Silently fail if PIL/Tkinter not available

    def stop(self) -> None:
        """Stop the rendering loop."""
        self._running = False
