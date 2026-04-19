"""
历史蝴蝶效应系统 (Historical Butterfly Effect System)

核心目标：
确保每次模拟都产生独特的历史轨迹，
真实体现混沌性、偶然性与历史分叉性。

关键特性：
1. 蝴蝶效应检测 - 微小扰动产生巨大影响
2. 分叉点识别 - 识别并标记历史关键节点
3. 多历史轨迹 - 支持不同历史分支
4. 路径依赖 - 过去决策影响未来
5. 不可预测性 - 确保模拟独特性
"""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class ButterflyEvent:
    """蝴蝶事件"""
    event_id: str
    tick: int
    trigger: str
    magnitude: float              # 初始规模
    amplification_factor: float   # 放大因子
    affected_domains: list[str]    # 影响的领域
    cascade_result: dict          # 级联结果


@dataclass
class BifurcationPoint:
    """历史分叉点"""
    tick: int
    point_id: str
    description: str
    triggered_by: str              # 触发原因
    alternative_outcomes: list[str]  # 可能的替代结果
    actual_outcome: str            # 实际发生的结果
    impact_radius: float           # 影响半径
    divergence_level: float         # 分叉程度 (0-1)


@dataclass
class HistoricalPath:
    """历史路径"""
    path_id: str
    tick_range: tuple[int, int]
    key_events: list[str]          # 关键事件
    bifurcation_count: int         # 分叉点数量
    cumulative_divergence: float    # 累计偏离度
    world_state_hash: str          # 世界状态哈希


class HistoricalButterflySystem:
    """
    历史蝴蝶效应系统

    确保模拟的唯一性和不可预测性
    """

    def __init__(self, world: Any, base_seed: int | None = None) -> None:
        self.world = world

        # 基础随机种子
        self.base_seed = base_seed or int(random.random() * 1000000)
        self.tick_seed = self.base_seed

        # 蝴蝶事件记录
        self._butterfly_events: list[ButterflyEvent] = []
        self._max_butterfly_events = 500

        # 分叉点记录
        self._bifurcation_points: list[BifurcationPoint] = []
        self._max_bifurcations = 100

        # 历史路径
        self._historical_paths: list[HistoricalPath] = []
        self._current_path: list[str] = []

        # 微扰动注入
        self._perturbation_accumulator = 0.0
        self._last_state_hash = ""

        # 混沌参数
        self._chaos_sensitivity = 0.3  # 混沌敏感度
        self._amplification_threshold = 0.5  # 放大阈值

        # 路径依赖跟踪
        self._path_dependencies: dict[str, list[str]] = defaultdict(list)
        self._critical_decisions: list[dict] = []

    def update(self, tick: int) -> dict[str, Any]:
        """
        执行一个tick的蝴蝶效应计算

        Returns:
            蝴蝶效应结果
        """
        # 1. 更新随机种子
        self._update_tick_seed(tick)

        # 2. 检测蝴蝶效应
        butterfly_result = self._detect_butterfly_effects(tick)

        # 3. 检测分叉点
        bifurcation_result = self._detect_bifurcations(tick)

        # 4. 注入微扰动
        perturbation = self._apply_micro_perturbations(tick)

        # 5. 追踪路径依赖
        self._track_path_dependencies(tick)

        # 6. 更新当前历史路径
        self._update_historical_path(tick)

        return {
            'butterfly_events': butterfly_result,
            'bifurcations': bifurcation_result,
            'perturbation': perturbation,
            'path_length': len(self._current_path),
        }

    def _update_tick_seed(self, tick: int) -> None:
        """
        更新tick随机种子

        关键：每次模拟的tick序列都略有不同
        """
        # 使用tick和base_seed生成确定性但不可预测的种子
        self.tick_seed = (self.base_seed * 1103515245 + tick * 12345 + 67890) % (2**31)

        # 设置numpy随机
        if hasattr(self.world, '_rng'):
            # 使用tick特定的种子创建随机状态
            np.random.seed(self.tick_seed % (2**31))
        else:
            random.seed(self.tick_seed % (2**31))

    def _detect_butterfly_effects(self, tick: int) -> list[ButterflyEvent]:
        """
        检测蝴蝶效应

        真实蝴蝶效应：
        - 微小事件可能产生巨大影响
        - 巨大事件可能无关紧要
        - 结果完全不可预测
        """
        events = []

        # 获取当前世界状态
        current_hash = self._compute_world_state_hash()

        if self._last_state_hash and current_hash != self._last_state_hash:
            # 状态发生了变化，检测是否是蝴蝶效应

            # 获取近期事件
            recent_events = self._get_recent_events(tick, window=50)

            for event in recent_events:
                # 计算混沌因子
                chaos_factor = self._calculate_chaos_factor(event, tick)

                # 如果混沌因子超过阈值，触发蝴蝶效应
                if chaos_factor > self._amplification_threshold:
                    butterfly = ButterflyEvent(
                        event_id=f"bf_{tick}_{random.randint(1000, 9999)}",
                        tick=tick,
                        trigger=event.get('type', 'unknown'),
                        magnitude=event.get('magnitude', 0.1),
                        amplification_factor=chaos_factor,
                        affected_domains=self._get_affected_domains(event),
                        cascade_result=self._propagate_chaos(event, chaos_factor),
                    )
                    events.append(butterfly)
                    self._butterfly_events.append(butterfly)

        self._last_state_hash = current_hash

        # 限制记录数量
        if len(self._butterfly_events) > self._max_butterfly_events:
            self._butterfly_events = self._butterfly_events[-self._max_butterfly_events // 2:]

        return events

    def _calculate_chaos_factor(self, event: dict, tick: int) -> float:
        """
        计算混沌因子

        关键：混沌是非线性的
        """
        # 基础混沌
        base_chaos = 0.1

        # 事件规模影响（但非线性）
        magnitude = event.get('magnitude', 0.5)
        magnitude_impact = magnitude ** 2 * 0.5  # 平方衰减

        # 系统临界状态放大
        criticality = self._calculate_system_criticality()
        criticality_amplification = criticality * 0.4

        # 随机混沌（真实不可预测性）
        random.seed((self.tick_seed * tick) % (2**31))
        random_chaos = random.uniform(0, 0.3)

        # 正反馈效应
        positive_feedback = self._check_positive_feedback(event, tick)

        # 综合混沌因子
        chaos = (
            base_chaos +
            magnitude_impact +
            criticality_amplification +
            random_chaos +
            positive_feedback * 0.3
        )

        return min(max(chaos, 0.0), 2.0)  # 0-2范围，可能大于1

    def _calculate_system_criticality(self) -> float:
        """
        计算系统临界程度

        系统越接近临界点，蝴蝶效应越容易放大
        """
        # 简化指标组合
        indicators = []

        # 资源压力
        if hasattr(self.world, '_vegetation'):
            veg = float(np.mean(self.world._vegetation))
            resource_pressure = 1.0 - veg
            indicators.append(resource_pressure)

        # 社会压力
        if hasattr(self.world, '_agents'):
            pop = len(self.world._agents)
            if hasattr(self.world, '_config'):
                area = self.world._config.world.width * self.world._config.world.height
                density = pop / area if area > 0 else 0
                density_pressure = min(density * 1000, 1.0)
                indicators.append(density_pressure)

        # 政治不稳定
        if hasattr(self.world, '_causal_engine'):
            stability = self.world._causal_engine._causal_state.get('politics', {}).get('stability', 0.5)
            instability = 1.0 - stability
            indicators.append(instability)

        # 平均临界度
        return sum(indicators) / len(indicators) if indicators else 0.5

    def _check_positive_feedback(self, event: dict, tick: int) -> float:
        """
        检测正反馈效应

        正反馈会放大初始扰动
        """
        feedback = 0.0

        # 检查是否是新事件类型
        recent_types = [e.get('type') for e in self._get_recent_events(tick, window=20)]
        event_type = event.get('type', '')

        if recent_types.count(event_type) == 0:
            # 新事件类型，可能引发关注-行动-反应循环
            feedback = 0.3
        elif recent_types.count(event_type) > 3:
            # 事件反复出现，可能形成趋势
            feedback = 0.5

        return feedback

    def _get_affected_domains(self, event: dict) -> list[str]:
        """获取事件影响的领域"""
        # 基于事件类型推断影响领域
        event_type = event.get('type', '')

        domain_map = {
            'disaster': ['ecology', 'economy', 'social'],
            'economic': ['economy', 'social', 'politics'],
            'political': ['politics', 'social', 'culture'],
            'social': ['social', 'culture', 'economy'],
            'natural': ['ecology', 'biology', 'economy'],
            'technological': ['economy', 'culture', 'social'],
        }

        return domain_map.get(event_type, ['social', 'economy'])

    def _propagate_chaos(self, event: dict, chaos_factor: float) -> dict:
        """
        传播混沌效应

        混沌如何在系统中扩散
        """
        domains = self._get_affected_domains(event)

        cascade = {}

        for domain in domains:
            # 每个领域的混沌衰减
            domain_decay = random.uniform(0.3, 0.7)
            domain_chaos = chaos_factor * domain_decay

            # 某些领域对混沌更敏感
            sensitive_domains = ['social', 'economy', 'politics']
            if domain in sensitive_domains:
                domain_chaos *= 1.5

            cascade[domain] = domain_chaos

        return cascade

    def _detect_bifurcations(self, tick: int) -> list[BifurcationPoint]:
        """
        检测历史分叉点

        当累积偏离达到一定程度时，历史分叉
        """
        bifurcations = []

        # 计算累积偏离度
        divergence = self._calculate_cumulative_divergence()

        # 分叉阈值（可调整）
        bifurcation_threshold = 0.7

        # 检查是否达到分叉条件
        if divergence > bifurcation_threshold:
            # 检测是否为有效的分叉点
            recent_events = self._get_recent_events(tick, window=100)

            if self._is_valid_bifurcation(recent_events, tick):
                point = BifurcationPoint(
                    tick=tick,
                    point_id=f"bp_{tick}_{random.randint(1000, 9999)}",
                    description=self._generate_bifurcation_description(recent_events),
                    triggered_by=recent_events[-1].get('type', 'unknown') if recent_events else 'system',
                    alternative_outcomes=self._generate_alternative_outcomes(),
                    actual_outcome=recent_events[-1].get('outcome', 'continuation') if recent_events else 'status quo',
                    impact_radius=divergence * 100,
                    divergence_level=divergence,
                )
                bifurcations.append(point)
                self._bifurcation_points.append(point)

                # 重置偏离度（分叉后重新开始）
                self._perturbation_accumulator = 0.0

        # 限制分叉点数量
        if len(self._bifurcation_points) > self._max_bifurcations:
            self._bifurcation_points = self._bifurcation_points[-self._max_bifurcations // 2:]

        return bifurcations

    def _calculate_cumulative_divergence(self) -> float:
        """
        计算累积偏离度

        衡量当前历史路径与基准路径的差异
        """
        divergence = self._perturbation_accumulator

        # 蝴蝶效应贡献
        if self._butterfly_events:
            recent_butterflies = self._butterfly_events[-10:]
            butterfly_impact = sum(b.amplification_factor for b in recent_butterflies) * 0.1
            divergence += butterfly_impact

        # 关键决策贡献
        critical_impact = sum(
            d.get('impact', 0.1) for d in self._critical_decisions[-10:]
        ) * 0.2

        divergence += critical_impact

        return min(divergence, 1.0)

    def _is_valid_bifurcation(self, events: list[dict], tick: int) -> bool:
        """
        判断是否为有效的分叉点

        避免过度分叉
        """
        # 检查最近是否有分叉
        if self._bifurcation_points:
            last_bifurcation = self._bifurcation_points[-1]
            if tick - last_bifurcation.tick < 100:
                return False

        # 检查事件是否足够重要
        if len(events) < 5:
            return False

        # 检查是否有足够的混沌积累
        return self._perturbation_accumulator > 0.3

    def _generate_bifurcation_description(self, events: list[dict]) -> str:
        """生成历史分叉描述"""
        if not events:
            return "System reached critical threshold"

        last_event = events[-1]
        event_type = last_event.get('type', 'event')

        descriptions = {
            'disaster': f"A catastrophic {event_type} forced societal reorganization",
            'economic': "Economic crisis triggered new paradigm",
            'political': "Political upheaval reshaped power structure",
            'social': "Social movement fundamentally altered norms",
            'technological': "Technology breakthrough changed trajectory",
        }

        return descriptions.get(event_type, "Critical event sequence led to historical turning point")

    def _generate_alternative_outcomes(self) -> list[str]:
        """生成替代历史结果"""
        outcomes = [
            "Rapid adaptation and growth",
            "Prolonged crisis and stagnation",
            "Complete systemic collapse",
            "Unexpected synthesis and innovation",
            "Return to previous equilibrium",
        ]
        return random.sample(outcomes, k=min(3, len(outcomes)))

    def _apply_micro_perturbations(self, tick: int) -> dict:
        """
        注入微扰动

        关键机制：确保即使相同参数也会产生不同结果
        """
        # 计算微扰动
        np.random.seed((self.tick_seed * tick) % (2**31))

        # 多维度微扰动
        perturbations = {
            'economic': np.random.uniform(-0.01, 0.01),
            'social': np.random.uniform(-0.01, 0.01),
            'political': np.random.uniform(-0.005, 0.005),
            'cultural': np.random.uniform(-0.02, 0.02),
        }

        # 应用到世界状态（如果支持）
        if hasattr(self.world, '_micro_perturbations'):
            self.world._micro_perturbations = perturbations
        else:
            self.world._micro_perturbations = perturbations

        # 累积偏离度
        total_perturbation = sum(abs(v) for v in perturbations.values())
        self._perturbation_accumulator += total_perturbation * 0.1

        return perturbations

    def _track_path_dependencies(self, tick: int) -> None:
        """
        追踪路径依赖

        确保过去决策持续影响未来
        """
        # 识别关键决策
        recent_events = self._get_recent_events(tick, window=50)

        for event in recent_events:
            if event.get('magnitude', 0) > 0.6:
                # 关键决策
                decision_id = event.get('id', f"decision_{tick}")
                self._critical_decisions.append({
                    'id': decision_id,
                    'tick': tick,
                    'type': event.get('type'),
                    'impact': event.get('magnitude', 0.1),
                })

                # 追踪依赖关系
                self._path_dependencies[decision_id].extend(
                    event.get('affected', [])
                )

        # 限制关键决策数量
        if len(self._critical_decisions) > 100:
            self._critical_decisions = self._critical_decisions[-50:]

    def _update_historical_path(self, tick: int) -> None:
        """更新历史路径"""
        # 添加当前tick的关键事件
        recent_events = self._get_recent_events(tick, window=10)
        for event in recent_events:
            event_desc = f"{event.get('type', 'event')}_{tick}"
            if event_desc not in self._current_path[-10:]:  # 避免重复
                self._current_path.append(event_desc)

        # 限制路径长度
        if len(self._current_path) > 1000:
            self._current_path = self._current_path[-500:]

        # 定期创建历史快照
        if tick % 500 == 0 and tick > 0:
            path = HistoricalPath(
                path_id=f"path_{tick}",
                tick_range=(tick - 500, tick),
                key_events=self._current_path[-50:],
                bifurcation_count=len(self._bifurcation_points),
                cumulative_divergence=self._calculate_cumulative_divergence(),
                world_state_hash=self._compute_world_state_hash(),
            )
            self._historical_paths.append(path)

    def _get_recent_events(self, tick: int, window: int) -> list[dict]:
        """获取近期事件"""
        events = []

        # 从因果引擎获取
        if hasattr(self.world, '_causal_engine'):
            try:
                causation_events = self.world._causal_engine.get_causation_events(lookback=window)
                events.extend([
                    {'type': 'causal', 'tick': e.tick, 'magnitude': abs(e.source_value) + abs(e.propagation)}
                    for e in causation_events
                ])
            except (AttributeError, TypeError):
                pass  # Causal engine may not have this method

        # 从涌现层获取
        if hasattr(self.world, '_emergence_layer'):
            try:
                layer = self.world._emergence_layer
                if hasattr(layer, '_traces') and layer._traces:
                    traces = layer._traces[-window:] if len(layer._traces) > window else layer._traces
                    for t in traces:
                        outcome = getattr(t, 'outcome', 0)
                        if isinstance(outcome, (int, float)):
                            events.append({'type': 'emergence', 'tick': getattr(t, 'tick', tick), 'magnitude': abs(outcome)})
            except (AttributeError, TypeError, IndexError):
                pass  # Emergence layer may have different structure

        # 从灾难系统获取
        if hasattr(self.world, '_disaster_system'):
            try:
                stats = self.world._disaster_system.get_stats()
                if stats and stats.get('recent_disasters'):
                    events.extend(stats['recent_disasters'][-window:])
            except (AttributeError, TypeError):
                pass  # Disaster system may not exist

        return events

    def _compute_world_state_hash(self) -> str:
        """计算世界状态哈希"""
        # 收集关键状态
        state_parts = []

        # 人口
        if hasattr(self.world, '_agents'):
            state_parts.append(f"pop:{len(self.world._agents)}")

        # 经济指标
        if hasattr(self.world, '_causal_engine'):
            state = self.world._causal_engine.get_domain_state('economy')
            state_parts.append(f"econ:{state:.3f}")

        # 社会指标
        if hasattr(self.world, '_causal_engine'):
            state = self.world._causal_engine.get_domain_state('social')
            state_parts.append(f"social:{state:.3f}")

        # 植被状态
        if hasattr(self.world, '_vegetation'):
            veg = float(np.mean(self.world._vegetation))
            state_parts.append(f"veg:{veg:.3f}")

        # 生成哈希
        state_str = "|".join(state_parts)
        return hashlib.md5(state_str.encode()).hexdigest()

    # ========== 查询接口 ==========

    def get_butterfly_events(self, tick_range: tuple[int, int] | None = None) -> list[dict]:
        """获取蝴蝶事件"""
        events = [e.__dict__ for e in self._butterfly_events]

        if tick_range:
            events = [e for e in events
                     if tick_range[0] <= e['tick'] <= tick_range[1]]

        return events

    def get_bifurcation_points(self) -> list[dict]:
        """获取分叉点"""
        return [b.__dict__ for b in self._bifurcation_points]

    def get_historical_paths(self) -> list[dict]:
        """获取历史路径"""
        return [p.__dict__ for p in self._historical_paths]

    def get_current_path(self) -> list[str]:
        """获取当前历史路径"""
        return self._current_path.copy()

    def get_divergence_level(self) -> float:
        """获取当前偏离度"""
        return self._calculate_cumulative_divergence()

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'total_butterfly_events': len(self._butterfly_events),
            'total_bifurcations': len(self._bifurcation_points),
            'current_path_length': len(self._current_path),
            'historical_paths_count': len(self._historical_paths),
            'critical_decisions_count': len(self._critical_decisions),
            'current_divergence': self._calculate_cumulative_divergence(),
            'base_seed': self.base_seed,
        }
