"""
Enhanced Visualization Engine

提供增强的可视化效果：
1. Pseudo-3D 地形渲染
2. 实时热力图
3. 历史轨迹回放
4. 动态效果
"""

from __future__ import annotations

import numpy as np
from typing import Any, Callable
from dataclasses import dataclass


@dataclass
class ViewConfig:
    """视图配置"""
    width: int = 800
    height: int = 600
    camera_x: float = 256.0
    camera_y: float = 256.0
    zoom: float = 1.0
    rotation: float = 0.0  # 弧度
    perspective: float = 0.3  # 伪3D透视强度


@dataclass
class RenderStyle:
    """渲染样式"""
    terrain_colors: dict[int, tuple[int, int, int]]
    agent_colors: dict[int, str]
    signal_colors: dict[str, tuple[int, int, int, int]]
    font_family: str = "monospace"
    show_grid: bool = False
    show_labels: bool = True


DEFAULT_TERRAIN_COLORS = {
    0: (10, 30, 80),      # DEEP_OCEAN
    1: (20, 60, 120),     # OCEAN
    2: (40, 100, 160),     # SHALLOW_WATER
    3: (220, 210, 160),   # BEACH
    4: (237, 201, 130),    # DESERT
    5: (200, 180, 120),    # DESERT_SCRUB
    6: (140, 190, 80),     # GRASSLAND
    7: (100, 160, 60),     # SAVANNA
    8: (160, 180, 80),     # SHRUBLAND
    9: (50, 120, 50),     # TEMPERATE_FOREST
    10: (30, 80, 40),      # TEMPERATE_RAIN_FOREST
    11: (25, 90, 35),      # TROPICAL_FOREST
    12: (15, 70, 25),      # RAIN_FOREST
    13: (30, 80, 60),      # MARSH
    14: (130, 110, 80),    # SWAMP
    15: (100, 90, 70),     # TUNDRA
    16: (150, 150, 160),   # ICE
    17: (180, 200, 210),   # MOUNTAIN_SNOW
}


DEFAULT_AGENT_COLORS = {
    1: '#ffd700',  # L1 - 金色
    2: '#64c8ff',  # L2 - 蓝色
    3: '#969696',  # L3 - 灰色
    4: '#505050',  # L4 - 深灰
}


@dataclass
class AgentTrail:
    """智能体轨迹"""
    agent_id: str
    positions: list[tuple[float, float]]
    color: str
    max_length: int = 100


@dataclass
class HeatmapCell:
    """热力图单元格"""
    x: int
    y: int
    value: float
    radius: float


class EnhancedRenderer:
    """
    增强渲染器

    支持多种渲染模式和视觉效果
    """

    def __init__(
        self,
        world: Any,
        config: ViewConfig | None = None,
        style: RenderStyle | None = None,
    ) -> None:
        self.world = world
        self.config = config or ViewConfig()
        self.style = style or RenderStyle(
            terrain_colors=DEFAULT_TERRAIN_COLORS,
            agent_colors=DEFAULT_AGENT_COLORS,
            signal_colors={},
        )

        # 渲染缓存
        self._terrain_cache: np.ndarray | None = None
        self._last_terrain_hash = ""

        # 轨迹追踪
        self._trails: dict[str, AgentTrail] = {}

        # 热力图
        self._heatmap: np.ndarray | None = None
        self._heatmap_mode: str = "population"

        # 动画状态
        self._animation_time = 0.0
        self._last_render_time = 0.0

    def set_heatmap_mode(self, mode: str) -> None:
        """设置热力图模式"""
        valid_modes = [
            "population",
            "activity",
            "wealth",
            "happiness",
            "temperature",
            "conflict",
            "social",
        ]
        if mode in valid_modes:
            self._heatmap_mode = mode
            self._heatmap = None  # 需要重新计算

    def update_trails(self, agents: list) -> None:
        """更新轨迹"""
        for agent in agents:
            if not hasattr(agent, 'entity_id'):
                continue

            agent_id = agent.entity_id
            x, y = agent.position.x, agent.position.y

            if agent_id not in self._trails:
                color = self.style.agent_colors.get(
                    getattr(agent, 'tier', None) and agent.tier.value,
                    '#ffffff'
                )
                self._trails[agent_id] = AgentTrail(
                    agent_id=agent_id,
                    positions=[],
                    color=color,
                )

            trail = self._trails[agent_id]
            trail.positions.append((x, y))

            if len(trail.positions) > trail.max_length:
                trail.positions.pop(0)

    def render_terrain_3d(
        self,
        terrain: np.ndarray,
        elevation: np.ndarray,
        canvas_width: int,
        canvas_height: int,
    ) -> np.ndarray:
        """
        渲染伪3D地形

        使用高程数据和光照效果创建3D感
        """
        from scipy.ndimage import gaussian_filter

        if terrain is None or len(terrain) == 0:
            return np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)

        h, w = terrain.shape
        output = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)

        # 高程模糊
        if elevation is not None:
            elevation_blur = gaussian_filter(elevation, sigma=1.5)
        else:
            elevation_blur = np.zeros_like(terrain, dtype=float)

        # 归一化高程
        elev_min, elev_max = elevation_blur.min(), elevation_blur.max()
        elev_range = elev_max - elev_min if elev_max != elev_min else 1

        # 光照方向 (从左上角)
        light_x, light_y = -0.5, -0.7

        # 逐像素渲染
        step_x = w / canvas_width
        step_y = h / canvas_height

        for py in range(canvas_height):
            for px in range(canvas_width):
                tx = int(px * step_x)
                ty = int(py * step_y)

                if tx >= w:
                    tx = w - 1
                if ty >= h:
                    ty = h - 1

                terrain_type = int(terrain[ty, tx])
                base_color = self.style.terrain_colors.get(
                    terrain_type,
                    (128, 128, 128)
                )

                # 计算光照
                elev = elevation_blur[ty, tx]
                elev_norm = (elev - elev_min) / elev_range

                # 简单的高度阴影
                shadow = 0.7 + elev_norm * 0.3

                # 应用颜色
                for c in range(3):
                    output[py, px, c] = min(255, int(base_color[c] * shadow))

        return output

    def render_heatmap(
        self,
        agents: list,
        world_width: int,
        world_height: int,
        resolution: int = 256,
    ) -> np.ndarray:
        """
        渲染热力图

        显示活动密度或其他指标
        """
        if self._heatmap is None:
            self._calculate_heatmap(agents, world_width, world_height, resolution)

        return self._heatmap

    def _calculate_heatmap(
        self,
        agents: list,
        world_width: int,
        world_height: int,
        resolution: int,
    ) -> None:
        """计算热力图"""
        heatmap = np.zeros((resolution, resolution), dtype=np.float32)

        if self._heatmap_mode == "population":
            # 基于人口密度
            for agent in agents:
                px = int(agent.position.x / world_width * resolution)
                py = int(agent.position.y / world_height * resolution)
                if 0 <= px < resolution and 0 <= py < resolution:
                    heatmap[py, px] += 1

        elif self._heatmap_mode == "activity":
            # 基于活动
            for agent in agents:
                if hasattr(agent, 'activity_level'):
                    px = int(agent.position.x / world_width * resolution)
                    py = int(agent.position.y / world_height * resolution)
                    if 0 <= px < resolution and 0 <= py < resolution:
                        heatmap[py, px] += getattr(agent, 'activity_level', 1)

        elif self._heatmap_mode == "wealth":
            # 基于财富
            for agent in agents:
                if hasattr(agent, 'wealth'):
                    px = int(agent.position.x / world_width * resolution)
                    py = int(agent.position.y / world_height * resolution)
                    if 0 <= px < resolution and 0 <= py < resolution:
                        heatmap[py, px] += getattr(agent, 'wealth', 0)

        elif self._heatmap_mode == "happiness":
            # 基于幸福度
            for agent in agents:
                happiness = self._get_agent_happiness(agent)
                px = int(agent.position.x / world_width * resolution)
                py = int(agent.position.y / world_height * resolution)
                if 0 <= px < resolution and 0 <= py < resolution:
                    heatmap[py, px] += happiness

        # 应用高斯模糊
        from scipy.ndimage import gaussian_filter
        heatmap = gaussian_filter(heatmap, sigma=3)

        # 归一化
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        self._heatmap = heatmap

    def _get_agent_happiness(self, agent: Any) -> float:
        """获取智能体幸福度"""
        if hasattr(agent, 'emotional_state') and hasattr(agent.emotional_state, 'happiness'):
            return agent.emotional_state.happiness
        if hasattr(agent, 'health'):
            return agent.health
        return 0.5

    def get_agent_trails(self) -> dict[str, AgentTrail]:
        """获取智能体轨迹"""
        return self._trails

    def clear_trails(self) -> None:
        """清除轨迹"""
        self._trails.clear()

    def get_statistics(self) -> dict:
        """获取渲染统计"""
        return {
            'active_trails': len(self._trails),
            'heatmap_mode': self._heatmap_mode,
            'cache_valid': self._terrain_cache is not None,
            'zoom': self.config.zoom,
            'camera': (self.config.camera_x, self.config.camera_y),
        }


class VisualizationDashboard:
    """
    可视化仪表盘

    支持多视图分割
    """

    def __init__(self) -> None:
        self.views: list[ViewConfig] = []
        self.max_views = 4

    def add_view(
        self,
        mode: str,
        x: int = 0,
        y: int = 0,
        width: int = 400,
        height: int = 300,
    ) -> ViewConfig:
        """添加视图"""
        if len(self.views) >= self.max_views:
            raise RuntimeError(f"Maximum {self.max_views} views supported")

        view = ViewConfig(
            width=width,
            height=height,
            camera_x=x,
            camera_y=y,
        )
        self.views.append(view)
        return view

    def get_view_layout(self) -> list[dict]:
        """获取视图布局"""
        layouts = []

        view_count = len(self.views)
        if view_count == 1:
            layouts.append({'x': 0, 'y': 0, 'w': 1, 'h': 1})
        elif view_count == 2:
            layouts.extend([
                {'x': 0, 'y': 0, 'w': 1, 'h': 2},
                {'x': 1, 'y': 0, 'w': 1, 'h': 2},
            ])
        elif view_count == 3:
            layouts.extend([
                {'x': 0, 'y': 0, 'w': 2, 'h': 1},
                {'x': 0, 'y': 1, 'w': 1, 'h': 1},
                {'x': 1, 'y': 1, 'w': 1, 'h': 1},
            ])
        else:
            for i in range(view_count):
                row = i // 2
                col = i % 2
                layouts.append({
                    'x': col,
                    'y': row,
                    'w': 1,
                    'h': 1
                })

        return layouts


class TimelinePlayer:
    """
    时间线播放器

    用于回放历史
    """

    def __init__(self) -> None:
        self.snapshots: list[dict] = []
        self.current_index = 0
        self.playing = False
        self.speed = 1.0

    def add_snapshot(self, tick: int, state: dict) -> None:
        """添加快照"""
        self.snapshots.append({
            'tick': tick,
            'state': state,
        })

        # 按tick排序
        self.snapshots.sort(key=lambda s: s['tick'])

    def play(self) -> None:
        """播放"""
        self.playing = True

    def pause(self) -> None:
        """暂停"""
        self.playing = False

    def seek(self, tick: int) -> None:
        """跳转到指定tick"""
        for i, snap in enumerate(self.snapshots):
            if snap['tick'] >= tick:
                self.current_index = i
                break

    def step_forward(self) -> dict | None:
        """前进一步"""
        if self.current_index < len(self.snapshots) - 1:
            self.current_index += 1
            return self.snapshots[self.current_index]
        return None

    def step_backward(self) -> dict | None:
        """后退一步"""
        if self.current_index > 0:
            self.current_index -= 1
            return self.snapshots[self.current_index]
        return None

    def get_current_snapshot(self) -> dict | None:
        """获取当前快照"""
        if 0 <= self.current_index < len(self.snapshots):
            return self.snapshots[self.current_index]
        return None

    def get_progress(self) -> float:
        """获取播放进度"""
        if len(self.snapshots) <= 1:
            return 0.0
        return self.current_index / (len(self.snapshots) - 1)
