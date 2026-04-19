"""
Performance Optimization Module

提供性能优化工具：
1. 内存池
2. 空间索引优化
3. 向量化操作
4. 缓存机制
"""

from __future__ import annotations

import numpy as np
from typing import Any, Generic, TypeVar, Callable
from collections import OrderedDict
import weakref
from dataclasses import dataclass


T = TypeVar('T')


class MemoryPool(Generic[T]):
    """
    内存池 - 复用对象以减少GC压力
    """

    def __init__(self, factory: Callable[[], T], initial_size: int = 100) -> None:
        self._factory = factory
        self._pool: list[T] = []
        self._allocated = 0

        # 预分配
        for _ in range(initial_size):
            self._pool.append(factory())

    def acquire(self) -> T:
        """获取对象"""
        if self._pool:
            self._allocated += 1
            return self._pool.pop()
        else:
            self._allocated += 1
            return self._factory()

    def release(self, obj: T) -> None:
        """归还对象"""
        self._allocated -= 1
        if len(self._pool) < 1000:  # 限制池大小
            self._pool.append(obj)

    def get_stats(self) -> dict:
        """获取统计"""
        return {
            'pool_size': len(self._pool),
            'allocated': self._allocated,
        }


class LRUCache(Generic[T]):
    """
    LRU缓存 - 最近最少使用缓存
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: Any, default: T | None = None) -> T | None:
        """获取值"""
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        else:
            self._misses += 1
            return default

    def put(self, key: Any, value: T) -> None:
        """放入值"""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value

        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_stats(self) -> dict:
        """获取统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
        }


class SpatialHashGrid:
    """
    空间哈希网格 - 高效的空间查询

    比KD-Tree更简单，但在大多数情况下足够快，
    特别适合均匀分布的对象。
    """

    def __init__(self, cell_size: float = 50.0) -> None:
        self._cell_size = cell_size
        self._cells: dict[tuple[int, int], list] = {}

    def clear(self) -> None:
        """清空网格"""
        self._cells.clear()

    def _get_cell_coords(self, x: float, y: float) -> tuple[int, int]:
        """获取单元格坐标"""
        return (int(x // self._cell_size), int(y // self._cell_size))

    def insert(self, x: float, y: float, obj: Any) -> None:
        """插入对象"""
        coords = self._get_cell_coords(x, y)
        if coords not in self._cells:
            self._cells[coords] = []
        self._cells[coords].append(obj)

    def remove(self, x: float, y: float, obj: Any) -> None:
        """移除对象"""
        coords = self._get_cell_coords(x, y)
        if coords in self._cells and obj in self._cells[coords]:
            self._cells[coords].remove(obj)

    def query_radius(self, x: float, y: float, radius: float) -> list:
        """
        查询半径范围内的所有对象

        时间复杂度: O(cells_in_range + objects_in_cells)
        """
        results = []
        cell_radius = int(radius // self._cell_size) + 1

        cx, cy = self._get_cell_coords(x, y)

        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell_coords = (cx + dx, cy + dy)
                if cell_coords in self._cells:
                    for obj in self._cells[cell_coords]:
                        results.append(obj)

        return results

    def query_neighbors(self, x: float, y: float, radius: float) -> list:
        """查询邻居"""
        return self.query_radius(x, y, radius)

    def rebuild(self, objects: list, get_position: Callable[[Any], tuple[float, float]]) -> None:
        """
        重建整个网格

        用于批量更新
        """
        self.clear()
        for obj in objects:
            x, y = get_position(obj)
            self.insert(x, y, obj)

    def get_stats(self) -> dict:
        """获取统计"""
        total_objects = sum(len(cell) for cell in self._cells.values())
        return {
            'cell_count': len(self._cells),
            'total_objects': total_objects,
            'avg_objects_per_cell': total_objects / max(len(self._cells), 1),
        }


@dataclass
class VectorizedOperation:
    """向量化操作"""
    name: str
    func: Callable
    enabled: bool = True


class VectorizedOperations:
    """
    向量化操作工具集

    使用NumPy进行批量计算加速
    """

    def __init__(self) -> None:
        self._operations: list[VectorizedOperation] = []

    def batch_distance(
        self,
        positions: np.ndarray,
        center: tuple[float, float] | np.ndarray,
    ) -> np.ndarray:
        """
        批量计算距离

        positions: (N, 2) 数组
        center: (2,) 数组或元组

        Returns: (N,) 距离数组
        """
        if len(positions) == 0:
            return np.array([])

        center_arr = np.array(center)
        diff = positions - center_arr
        return np.sqrt(np.sum(diff ** 2, axis=1))

    def batch_distance_matrix(self, positions: np.ndarray) -> np.ndarray:
        """
        计算距离矩阵

        positions: (N, 2) 数组

        Returns: (N, N) 距离矩阵
        """
        if len(positions) == 0:
            return np.array([])

        # 使用广播
        diffs = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
        return np.sqrt(np.sum(diffs ** 2, axis=2))

    def batch_in_radius(
        self,
        positions: np.ndarray,
        center: tuple[float, float] | np.ndarray,
        radius: float,
    ) -> np.ndarray:
        """
        批量判断哪些点在半径内

        Returns: (N,) 布尔数组
        """
        distances = self.batch_distance(positions, center)
        return distances <= radius

    def batch_interpolate(
        self,
        values: np.ndarray,
        factor: float,
    ) -> np.ndarray:
        """
        批量插值

        values: (N,) 数组
        factor: 插值因子

        Returns: (N,) 插值后数组
        """
        # 线性插值到均值
        mean_val = np.mean(values)
        return values * (1 - factor) + mean_val * factor

    def batch_smooth(
        self,
        values: np.ndarray,
        kernel_size: int = 3,
    ) -> np.ndarray:
        """
        批量平滑

        使用移动平均
        """
        if len(values) < kernel_size:
            return values

        kernel = np.ones(kernel_size) / kernel_size
        return np.convolve(values, kernel, mode='same')

    def batch_gaussian_weight(
        self,
        distances: np.ndarray,
        sigma: float,
    ) -> np.ndarray:
        """
        计算高斯权重

        weight = exp(-d² / (2σ²))
        """
        return np.exp(-(distances ** 2) / (2 * sigma ** 2))


class PerformanceOptimizer:
    """
    性能优化器

    整合所有优化工具
    """

    def __init__(self) -> None:
        # 内存池
        self.position_pool = MemoryPool(
            factory=lambda: np.zeros(2, dtype=np.float32),
            initial_size=1000,
        )

        # 空间索引
        self.spatial_grid = SpatialHashGrid(cell_size=50.0)

        # LRU缓存
        self.agent_cache = LRUCache(max_size=500)
        self.terrain_cache = LRUCache(max_size=100)

        # 向量化操作
        self.vectorized = VectorizedOperations()

        # 统计
        self._start_time = None
        self._tick_times: list[float] = []
        self._max_tick_times = 100

    def record_tick_time(self, tick: int, duration: float) -> None:
        """记录tick耗时"""
        self._tick_times.append(duration)
        if len(self._tick_times) > self._max_tick_times:
            self._tick_times.pop(0)

    def get_average_tick_time(self) -> float:
        """获取平均tick时间"""
        if not self._tick_times:
            return 0.0
        return sum(self._tick_times) / len(self._tick_times)

    def get_tps(self) -> float:
        """获取TPS"""
        avg_time = self.get_average_tick_time()
        if avg_time > 0:
            return 1.0 / avg_time
        return 0.0

    def optimize_agent_positions(self, agents: list) -> np.ndarray:
        """
        优化智能体位置数组

        用于批量计算
        """
        positions = np.zeros((len(agents), 2), dtype=np.float32)
        for i, agent in enumerate(agents):
            if hasattr(agent, 'position'):
                positions[i, 0] = agent.position.x
                positions[i, 1] = agent.position.y
        return positions

    def optimize_spatial_query(self, x: float, y: float, radius: float, agents: list) -> list:
        """
        优化空间查询

        智能选择使用缓存或网格
        """
        # 尝试从缓存获取
        cache_key = f"{x:.0f}_{y:.0f}_{radius:.0f}"
        cached = self.agent_cache.get(cache_key)
        if cached is not None:
            return cached

        # 使用空间网格查询
        results = self.spatial_grid.query_radius(x, y, radius)

        # 存入缓存
        self.agent_cache.put(cache_key, results)

        return results

    def rebuild_spatial_index(self, agents: list) -> None:
        """
        重建空间索引

        在智能体大规模移动后调用
        """
        positions = self.optimize_agent_positions(agents)
        self.spatial_grid.clear()

        for i, agent in enumerate(agents):
            if hasattr(agent, 'position'):
                self.spatial_grid.insert(
                    positions[i, 0],
                    positions[i, 1],
                    agent,
                )

    def get_statistics(self) -> dict:
        """获取优化统计"""
        return {
            'position_pool': self.position_pool.get_stats(),
            'spatial_grid': self.spatial_grid.get_stats(),
            'agent_cache': self.agent_cache.get_stats(),
            'terrain_cache': self.terrain_cache.get_stats(),
            'avg_tick_time': self.get_average_tick_time(),
            'tps': self.get_tps(),
        }
