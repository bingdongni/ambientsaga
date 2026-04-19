"""
Butterfly Effect System — Chaos-based historical branching.

从一只蝴蝶扇动翅膀到一个帝国的兴衰。
微观事件通过因果链放大，最终改变历史走向。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional
from enum import Enum, auto
import uuid
import math
import random

if TYPE_CHECKING:
    from ambientsaga.world.state import World


class CausalMagnitude(Enum):
    """因果事件强度等级"""
    NEGLIGIBLE = 0.01      # 蝴蝶振翅
    MINOR = 0.1           # 一个人的决定
    MODERATE = 0.5        # 一个家庭的悲剧
    SIGNIFICANT = 1.0     # 一个领袖的死亡
    CRITICAL = 2.0        # 一场瘟疫
    CATASTROPHIC = 5.0    # 一场地震
    APOCALYPTIC = 10.0    # 小行星撞击


class SensitivityLevel(Enum):
    """系统敏感度"""
    STABLE = auto()       # 对微扰免疫
    RESILIENT = auto()    # 短期抵抗，长期消化
    SENSITIVE = auto()    # 容易被微扰改变
    CHAOTIC = auto()      # 对初始条件极度敏感
    CRITICAL = auto()     # 处于临界点


@dataclass
class ButterflyTrace:
    """蝴蝶痕迹 — 一个微事件的长尾因果链"""
    trace_id: str
    origin_tick: int
    origin_agent_id: str
    origin_action: str
    initial_magnitude: float
    current_magnitude: float
    causal_chain: list[dict] = field(default_factory=list)
    affected_domains: set[str] = field(default_factory=set)
    irreversible: bool = False
    branch_point: bool = False
    branch_id: Optional[str] = None

    def amplify(self, factor: float) -> None:
        """因果放大"""
        self.current_magnitude *= factor
        if self.current_magnitude > self.initial_magnitude * 100:
            self.current_magnitude = self.initial_magnitude * 100

    def propagate_to_domain(self, domain: str) -> None:
        """跨域传播"""
        self.affected_domains.add(domain)
        if len(self.affected_domains) >= 3:
            self.branch_point = True


@dataclass
class HistoricalBranchPoint:
    """Historical branching point - marks 'if X had not happened, history would be different'"""
    branch_id: str
    tick: int
    origin_trace_id: str
    description: str
    divergence_score: float  # 0-1, higher = greater historical difference
    affected_agents: set[str] = field(default_factory=set)
    affected_institutions: set[str] = field(default_factory=set)
    alternative_narrative: str = ""

    def __hash__(self):
        return hash(self.branch_id)


@dataclass
class CausalAmplifier:
    """因果放大器 — 微观事件的宏观效应"""
    amplifier_id: str
    trigger_conditions: dict  # 什么条件下触发
    amplification_factor: float  # 放大倍数
    cascade_rules: list[dict]  # 级联规则

    def should_amplify(self, context: dict) -> bool:
        """判断是否应该放大"""
        for key, value in self.trigger_conditions.items():
            if context.get(key, 0) < value:
                return False
        return True


class ButterflyEffectSystem:
    """
    蝴蝶效应引擎。

    核心机制：
    1. 追踪微事件的因果链
    2. 检测因果放大器（关键节点）
    3. 标记历史分叉点
    4. 生成替代历史叙事
    """

    def __init__(self, world: "World"):
        self.world = world
        self.traces: dict[str, ButterflyTrace] = {}
        self.branch_points: dict[str, HistoricalBranchPoint] = {}
        self.amplifiers: list[CausalAmplifier] = []
        self.sensitivity_map: dict[str, SensitivityLevel] = {}

        # 全局敏感度
        self.global_sensitivity: SensitivityLevel = SensitivityLevel.STABLE
        self.chaos_accumulator: float = 0.0

        # 历史记录
        self.historical_timeline: list[dict] = []
        self.alternative_histories: dict[str, list[dict]] = {}

        # 分叉点存储
        self._branch_narratives: dict[str, str] = {}
        self._historical_anchors: dict[int, dict] = {}  # tick -> snapshot

        self._initialize_amplifiers()

    def _initialize_amplifiers(self) -> None:
        """初始化因果放大器"""
        # 领袖死亡放大器
        self.amplifiers.append(CausalAmplifier(
            amplifier_id="leader_death",
            trigger_conditions={"domain": "social", "magnitude": 2.0, "target_tier": 1},
            amplification_factor=10.0,
            cascade_rules=[
                {"target": "politics", "factor": 3.0, "delay": 5},
                {"target": "economy", "factor": 2.0, "delay": 10},
                {"target": "culture", "factor": 1.5, "delay": 20},
            ]
        ))

        # 瘟疫放大器
        self.amplifiers.append(CausalAmplifier(
            amplifier_id="pandemic",
            trigger_conditions={"domain": "biology", "affected_agents": 10},
            amplification_factor=50.0,
            cascade_rules=[
                {"target": "economy", "factor": 5.0, "delay": 3},
                {"target": "social", "factor": 4.0, "delay": 5},
                {"target": "politics", "factor": 2.0, "delay": 15},
            ]
        ))

        # 资源枯竭放大器
        self.amplifiers.append(CausalAmplifier(
            amplifier_id="resource_collapse",
            trigger_conditions={"domain": "ecology", "scarcity": 0.8},
            amplification_factor=20.0,
            cascade_rules=[
                {"target": "social", "factor": 4.0, "delay": 2},
                {"target": "economy", "factor": 3.0, "delay": 5},
                {"target": "politics", "factor": 2.5, "delay": 10},
            ]
        ))

        # 叛逃放大器
        self.amplifiers.append(CausalAmplifier(
            amplifier_id="defection",
            trigger_conditions={"domain": "social", "relationship_breaking": True},
            amplification_factor=5.0,
            cascade_rules=[
                {"target": "social", "factor": 2.0, "delay": 1},
                {"target": "culture", "factor": 1.5, "delay": 8},
            ]
        ))

        # 创新放大器
        self.amplifiers.append(CausalAmplifier(
            amplifier_id="innovation",
            trigger_conditions={"domain": "culture", "novelty": 0.9},
            amplification_factor=15.0,
            cascade_rules=[
                {"target": "economy", "factor": 4.0, "delay": 10},
                {"target": "politics", "factor": 2.0, "delay": 20},
                {"target": "military", "factor": 1.5, "delay": 15},
            ]
        ))

    def update(self, tick: int) -> dict[str, Any]:
        """
        Tick-based update for ButterflyEffectSystem.

        This is a lightweight tick-based wrapper for the event-driven system.
        It handles periodic cleanup and state anchoring.
        """
        # Periodically anchor historical state (every 50 ticks)
        if tick % 50 == 0:
            self.anchor_historical_state(tick)

        # Clean up old traces (keep only traces from last 200 ticks)
        current_tick = getattr(self.world, 'tick', tick)
        cutoff_tick = current_tick - 200
        self.traces = {
            trace_id: trace
            for trace_id, trace in self.traces.items()
            if trace.origin_tick >= cutoff_tick
        }

        # Update chaos accumulator decay
        self.chaos_accumulator *= 0.99  # Slight decay

        return {
            'active_traces': len(self.traces),
            'branch_points': len(self.branch_points),
            'chaos_level': self.chaos_accumulator,
        }

    def record_micro_event(
        self,
        agent_id: str,
        action: str,
        magnitude: float,
        context: dict
    ) -> Optional[str]:
        """记录一个微事件"""
        # 判定初始强度
        if magnitude < 0.1:
            # 太微弱，不记录
            return None

        trace_id = str(uuid.uuid4())

        # 查找匹配的放大器
        amplifier = None
        for amp in self.amplifiers:
            if amp.should_amplify(context):
                amplifier = amp
                break

        # 计算放大后的强度
        final_magnitude = magnitude
        if amplifier:
            final_magnitude = magnitude * amplifier.amplification_factor

        # 创建蝴蝶痕迹
        trace = ButterflyTrace(
            trace_id=trace_id,
            origin_tick=self.world.tick,
            origin_agent_id=agent_id,
            origin_action=action,
            initial_magnitude=magnitude,
            current_magnitude=final_magnitude
        )

        # 初始化因果链
        trace.causal_chain.append({
            "tick": self.world.tick,
            "event": action,
            "agent": agent_id,
            "magnitude": final_magnitude,
            "domain": context.get("domain", "unknown")
        })

        trace.affected_domains.add(context.get("domain", "unknown"))

        self.traces[trace_id] = trace

        # 检查是否是分叉点
        if final_magnitude > 1.0 or len(trace.affected_domains) >= 3:
            self._create_branch_point(trace, amplifier)

        # 更新全局敏感度
        self._update_global_sensitivity(trace)

        return trace_id

    def _create_branch_point(self, trace: ButterflyTrace, amplifier: Optional[CausalAmplifier]) -> None:
        """创建历史分叉点"""
        branch_id = str(uuid.uuid4())

        # 计算分歧度
        divergence = min(1.0, trace.current_magnitude / 10.0)

        branch = HistoricalBranchPoint(
            branch_id=branch_id,
            tick=trace.origin_tick,
            origin_trace_id=trace.trace_id,
            description=self._generate_narrative(trace),
            divergence_score=divergence,
        )

        trace.branch_point = True
        trace.branch_id = branch_id
        self.branch_points[branch_id] = branch

        # 生成替代历史叙事
        trace.alternative_narrative = self._generate_alternative_history(trace)

    def _generate_narrative(self, trace: ButterflyTrace) -> str:
        """生成历史叙事"""
        narratives = {
            "leader_death": f"领袖 {trace.origin_agent_id[:8]} 的死亡引发了动荡",
            "pandemic": f"瘟疫在 tick {trace.origin_tick} 开始蔓延",
            "resource_collapse": f"资源枯竭导致社会崩溃",
            "defection": f"背叛事件撕裂了社区",
            "innovation": f"一项创新改变了游戏规则",
        }

        # 查找匹配的放大器类型
        for amp in self.amplifiers:
            if any(amp.trigger_conditions.get(k) == v for k, v in [("domain", "social"), ("domain", "biology")]):
                return narratives.get(amp.amplifier_id, f"事件 {trace.origin_action}")

        return f"微事件 {trace.origin_action} 触发了连锁反应"

    def _generate_alternative_history(self, trace: ButterflyTrace) -> str:
        """生成替代历史"""
        return f"""
如果 {trace.origin_agent_id[:8]} 没有在 tick {trace.origin_tick}
执行 '{trace.origin_action}'，这个世界将会：
- {'避免' if trace.current_magnitude > 5 else '减少'} 人员伤亡
- {'阻止' if trace.current_magnitude > 10 else '减缓'} 社会动荡
- {'维持' if trace.current_magnitude > 3 else '改善'} 经济秩序
- {'保留' if trace.current_magnitude > 8 else '影响'} 文化遗产
        """.strip()

    def propagate_causal_chain(self, trace_id: str, new_domain: str, new_agent: str, delay: int = 0) -> None:
        """传播因果链"""
        trace = self.traces.get(trace_id)
        if not trace:
            return

        # 放大效应
        if len(trace.causal_chain) < 20:  # 防止无限增长
            trace.causal_chain.append({
                "tick": self.world.tick + delay,
                "event": f"propagated_to_{new_domain}",
                "agent": new_agent,
                "magnitude": trace.current_magnitude * 0.9,
                "domain": new_domain
            })

            trace.amplify(1.1)  # 10% 增幅
            trace.propagate_to_domain(new_domain)

            # 更新分叉点
            if trace.branch_point:
                self.branch_points[trace.branch_id].affected_agents.add(new_agent)

    def _update_global_sensitivity(self, trace: ButterflyTrace) -> None:
        """更新全局敏感度"""
        # 累积混沌值
        self.chaos_accumulator += trace.current_magnitude * 0.1

        # 根据累积值调整敏感度
        if self.chaos_accumulator > 100:
            self.global_sensitivity = SensitivityLevel.CRITICAL
        elif self.chaos_accumulator > 50:
            self.global_sensitivity = SensitivityLevel.CHAOTIC
        elif self.chaos_accumulator > 20:
            self.global_sensitivity = SensitivityLevel.SENSITIVE
        elif self.chaos_accumulator > 5:
            self.global_sensitivity = SensitivityLevel.RESILIENT
        else:
            self.global_sensitivity = SensitivityLevel.STABLE

    def should_trigger_alternative_history(self) -> bool:
        """判断是否触发替代历史"""
        # 只有在高度敏感状态下才可能分叉
        if self.global_sensitivity in [SensitivityLevel.CHAOTIC, SensitivityLevel.CRITICAL]:
            return random.random() < 0.3  # 30% 概率
        elif self.global_sensitivity == SensitivityLevel.SENSITIVE:
            return random.random() < 0.1  # 10% 概率
        return False

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        active_traces = sum(1 for t in self.traces.values()
                           if self.world.tick - t.origin_tick < 100)

        return {
            "total_traces": len(self.traces),
            "active_traces": active_traces,
            "branch_points": len(self.branch_points),
            "global_sensitivity": self.global_sensitivity.name,
            "chaos_accumulator": round(self.chaos_accumulator, 2),
            "amplifiers_count": len(self.amplifiers),
            "alternative_histories": len(self.alternative_histories),
            "critical_traces": sum(1 for t in self.traces.values()
                                  if t.current_magnitude > 5.0),
            "domain_propagations": sum(len(t.affected_domains) for t in self.traces.values()),
        }

    def get_major_events(self, lookback: int = 100) -> list[dict]:
        """获取重大事件"""
        major = []
        for trace in self.traces.values():
            if self.world.tick - trace.origin_tick <= lookback:
                if trace.current_magnitude > 1.0 or trace.branch_point:
                    major.append({
                        "trace_id": trace.trace_id,
                        "tick": trace.origin_tick,
                        "action": trace.origin_action,
                        "magnitude": round(trace.current_magnitude, 2),
                        "domains": list(trace.affected_domains),
                        "is_branch": trace.branch_point,
                        "description": self._generate_narrative(trace)
                    })

        return sorted(major, key=lambda x: x["magnitude"], reverse=True)[:20]

    # =========================================================================
    # 历史回溯与替代历史生成
    # =========================================================================

    def record_to_timeline(self, tick: int, event: dict) -> None:
        """将事件记录到历史时间线"""
        self.historical_timeline.append({
            "tick": tick,
            "event": event,
            "timestamp": tick,
        })
        # 限制时间线长度
        if len(self.historical_timeline) > 10000:
            self.historical_timeline = self.historical_timeline[-5000:]

    def anchor_historical_state(self, tick: int) -> dict:
        """
        锚定当前世界状态到历史锚点。
        用于后续的历史对比和替代历史生成。
        """
        # 记录世界状态的快照
        anchor = {
            "tick": tick,
            "agent_count": self.world.get_agent_count(),
            "chaos_level": self.chaos_accumulator,
            "sensitivity": self.global_sensitivity.name,
            "active_traces": len([t for t in self.traces.values()
                                 if self.world.tick - t.origin_tick < 50]),
            "branch_points": len(self.branch_points),
        }
        self._historical_anchors[tick] = anchor
        return anchor

    def get_alternative_history(self, branch_id: str) -> str:
        """
        获取分支点的替代历史叙事。

        生成"如果X没有发生，世界将会..."的叙事。
        """
        branch = self.branch_points.get(branch_id)
        if not branch:
            return "未知的历史分支"

        # 检查是否已生成叙事
        if branch_id in self._branch_narratives:
            return self._branch_narratives[branch_id]

        # 获取相关的trace
        trace = self.traces.get(branch.origin_trace_id)
        if not trace:
            return "无法生成替代历史"

        # 生成详细的替代历史叙事
        narrative = self._generate_detailed_alternative_history(branch, trace)
        self._branch_narratives[branch_id] = narrative
        return narrative

    def _generate_detailed_alternative_history(self, branch: HistoricalBranchPoint, trace: ButterflyTrace) -> str:
        """生成详细的替代历史叙事"""
        # 获取分支点的上下文
        tick_diff = self.world.tick - branch.tick

        # 生成替代历史
        narrative_parts = []

        # 标题
        narrative_parts.append(f"=== 历史分叉点 #{branch.branch_id[:8]} ===")
        narrative_parts.append(f"时间: Tick {branch.tick} (距今 {tick_diff} ticks)")
        narrative_parts.append(f"分歧度: {branch.divergence_score:.1%}")
        narrative_parts.append("")

        # 原始事件
        narrative_parts.append("【实际发生的历史】")
        narrative_parts.append(f"事件: {trace.origin_action}")
        narrative_parts.append(f"执行者: {trace.origin_agent_id[:8]}")
        narrative_parts.append(f"影响范围: {', '.join(trace.affected_domains)}")
        narrative_parts.append("")

        # 因果链
        if trace.causal_chain:
            narrative_parts.append("【因果传播链】")
            for i, chain_event in enumerate(trace.causal_chain[:5]):
                narrative_parts.append(
                    f"  {i+1}. Tick {chain_event['tick']}: {chain_event['event']} "
                    f"(强度: {chain_event['magnitude']:.2f})"
                )
            narrative_parts.append("")

        # 替代历史
        narrative_parts.append("【替代历史】")
        narrative_parts.append(f"如果 {trace.origin_agent_id[:8]} 没有执行 '{trace.origin_action}'：")
        narrative_parts.append("")

        # 分领域描述影响
        if "social" in trace.affected_domains:
            narrative_parts.append(f"  社会: {'稳定' if trace.current_magnitude < 5 else '动荡'}")
        if "economy" in trace.affected_domains:
            narrative_parts.append(f"  经济: {'繁荣' if trace.current_magnitude < 3 else '衰退'}")
        if "politics" in trace.affected_domains:
            narrative_parts.append(f"  政治: {'和平' if trace.current_magnitude < 5 else '动荡'}")
        if "culture" in trace.affected_domains:
            narrative_parts.append(f"  文化: {'传承' if trace.current_magnitude < 8 else '断裂'}")

        narrative_parts.append("")

        # 受影响的agent
        if branch.affected_agents:
            narrative_parts.append(f"【受影响个体】: {len(branch.affected_agents)} 个")
        if branch.affected_institutions:
            narrative_parts.append(f"【受影响制度】: {', '.join(branch.affected_institutions)}")

        return "\n".join(narrative_parts)

    def get_historical_narrative(self, start_tick: int, end_tick: int) -> str:
        """
        获取指定时间范围内的历史叙事。

        生成从start_tick到end_tick的历史摘要。
        """
        # 筛选时间范围内的记录
        relevant_traces = [
            t for t in self.traces.values()
            if start_tick <= t.origin_tick <= end_tick
        ]

        if not relevant_traces:
            return f"从 Tick {start_tick} 到 {end_tick} 没有重大历史事件记录"

        # 按影响力排序
        relevant_traces.sort(key=lambda t: t.current_magnitude, reverse=True)

        narrative_parts = []
        narrative_parts.append(f"=== 历史叙事 (Tick {start_tick} - {end_tick}) ===")
        narrative_parts.append(f"重大事件: {len(relevant_traces)}")
        narrative_parts.append("")

        # 按时间顺序列出事件
        sorted_traces = sorted(relevant_traces, key=lambda t: t.origin_tick)
        for trace in sorted_traces[:10]:  # 最多10个事件
            narrative_parts.append(
                f"【Tick {trace.origin_tick}】{trace.origin_action} "
                f"(影响力: {trace.current_magnitude:.2f}, 领域: {', '.join(trace.affected_domains)})"
            )

        return "\n".join(narrative_parts)

    def analyze_branch_point_impact(self, branch_id: str) -> dict:
        """
        分析分支点的影响。

        返回对各个领域的影响分析。
        """
        branch = self.branch_points.get(branch_id)
        if not branch:
            return {"error": "分支点不存在"}

        trace = self.traces.get(branch.origin_trace_id)
        if not trace:
            return {"error": "相关trace不存在"}

        # 计算各领域影响
        impact = {
            "branch_id": branch_id,
            "tick": branch.tick,
            "divergence_score": branch.divergence_score,
            "affected_domains": {},
            "affected_agents_count": len(branch.affected_agents),
            "affected_institutions": list(branch.affected_institutions),
        }

        # 各领域影响
        for domain in trace.affected_domains:
            # 基于magnitude和divergence计算影响
            domain_impact = trace.current_magnitude * branch.divergence_score
            impact["affected_domains"][domain] = {
                "severity": min(1.0, domain_impact / 10.0),
                "description": self._get_domain_impact_description(domain, domain_impact),
            }

        return impact

    def _get_domain_impact_description(self, domain: str, magnitude: float) -> str:
        """获取领域影响描述"""
        descriptions = {
            "social": {
                "low": "社会结构轻微调整",
                "medium": "社会关系显著改变",
                "high": "社会秩序剧烈震荡",
            },
            "economy": {
                "low": "市场轻微波动",
                "medium": "经济活动显著变化",
                "high": "经济体系深刻变革",
            },
            "politics": {
                "low": "政治格局微调",
                "medium": "权力结构显著改变",
                "high": "政治秩序根本重塑",
            },
            "culture": {
                "low": "文化传统延续",
                "medium": "文化观念显著变化",
                "high": "文化遗产断裂",
            },
            "biology": {
                "low": "种群结构轻微变化",
                "medium": "物种分布显著改变",
                "high": "生态系统深刻变革",
            },
        }

        level = "low" if magnitude < 3 else "medium" if magnitude < 7 else "high"
        return descriptions.get(domain, {}).get(level, "影响范围待定")

    def export_history(self, format: str = "dict") -> Any:
        """
        导出历史数据。

        支持格式: dict, json
        """
        export_data = {
            "current_tick": self.world.tick,
            "global_sensitivity": self.global_sensitivity.name,
            "chaos_accumulator": self.chaos_accumulator,
            "statistics": self.get_statistics(),
            "timeline": self.historical_timeline[-100:],  # 最近100条
            "branch_points": [
                {
                    "branch_id": bp.branch_id,
                    "tick": bp.tick,
                    "divergence_score": bp.divergence_score,
                    "affected_agents": list(bp.affected_agents),
                    "affected_institutions": list(bp.affected_institutions),
                    "alternative_narrative": self.get_alternative_history(bp.branch_id),
                }
                for bp in list(self.branch_points.values())[-10:]  # 最近10个
            ],
            "major_events": self.get_major_events(lookback=1000),  # 最近1000 ticks
        }

        if format == "json":
            import json
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        return export_data
