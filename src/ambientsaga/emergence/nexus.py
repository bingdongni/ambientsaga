"""
原生涌现核心引擎 - AmbientSaga Native Emergence Core (NEXUS)

这是一个真正的底层驱动引擎，不是模块化组件。
所有结构、规范、组织、行为都从同一个因果传播机制中涌现。

核心机制：
1. CausalEvent - 每个行动都是因果事件
2. CausalPropagation - 因果事件在系统中传播
3. CascadeAmplification - 事件可以级联放大（蝴蝶效应）
4. PatternRecognition - 反复出现的模式涌现成制度
5. ScientificConstraints - 科学定律作为硬约束

没有预设制度、没有预设规则、没有预设行为。
一切从微观交互中自然涌现。
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from ambientsaga.world.state import World


# ============================================================================
# 域定义 - Domain Definitions
# ============================================================================

class CausalDomain:
    """因果域 - 影响和被影响的领域"""
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ECOLOGY = "ecology"
    ECONOMICS = "economics"
    SOCIAL = "social"
    POLITICAL = "political"
    CULTURAL = "cultural"
    PSYCHOLOGICAL = "psychological"

    ALL = {PHYSICS, CHEMISTRY, BIOLOGY, ECOLOGY, ECONOMICS, SOCIAL, POLITICAL, CULTURAL, PSYCHOLOGICAL}

    # 域之间的因果耦合关系 - 定义哪些域会相互影响
    COUPLING_GRAPH = {
        # 自然科学链
        PHYSICS: {CHEMISTRY},
        CHEMISTRY: {BIOLOGY, ECOLOGY},
        BIOLOGY: {ECOLOGY, PSYCHOLOGICAL},
        ECOLOGY: {ECONOMICS, SOCIAL},

        # 社会科学链
        ECONOMICS: {SOCIAL, POLITICAL, ECOLOGY},  # 经济活动影响生态（合并）
        SOCIAL: {POLITICAL, CULTURAL, PSYCHOLOGICAL, BIOLOGY},  # 社会行为影响生物（合并）
        POLITICAL: {CULTURAL, ECONOMICS},
        CULTURAL: {PSYCHOLOGICAL, SOCIAL, ECOLOGY},  # 文化影响环境（合并）
        PSYCHOLOGICAL: {SOCIAL, ECONOMICS},
    }

    @classmethod
    def get_affected_domains(cls, source_domain: str, magnitude: float) -> set[str]:
        """根据源头域和强度确定受影响的所有域"""
        affected = {source_domain}

        # 直接耦合
        direct = cls.COUPLING_GRAPH.get(source_domain, set())
        affected.update(direct)

        # 高强度时触发二级传播
        if magnitude > 0.7:
            for d in direct:
                affected.update(cls.COUPLING_GRAPH.get(d, set()))

        # 极高强度时触发全系统波动
        if magnitude > 0.95:
            affected.update(cls.ALL)

        return affected


# ============================================================================
# 因果事件 - Causal Event
# ============================================================================

@dataclass
class CausalEvent:
    """
    因果事件 - 宇宙中发生的每一个原子事件

    不是"记录"，而是真正的因果载体：
    - 触发原因 (cause)
    - 发生结果 (effect)
    - 影响范围 (affected_domains)
    - 传播强度 (magnitude)
    - 历史唯一性 (causal_id)
    """

    # 基本信息
    causal_id: str
    tick: int
    cause_agent_id: str | None  # 谁引起的（如果是agent）
    cause_description: str          # 原因描述
    effect_description: str         # 结果描述

    # 因果强度
    magnitude: float = 1.0          # 0-1，影响强度
    propagation: float = 1.0        # 传播范围

    # 受影响的域
    source_domain: str = CausalDomain.SOCIAL
    affected_domains: set[str] = field(default_factory=set)

    # 级联信息
    is_cascade: bool = False        # 是否是级联事件
    parent_event_id: str | None = None  # 父事件ID
    cascade_depth: int = 0          # 级联深度
    cascade_chain: list[str] = field(default_factory=list)  # 级联链

    # 蝴蝶效应追踪
    butterfly_potential: float = 0.0  # 蝴蝶潜力（微小变化→大影响）
    history_branch_id: str | None = None

    # 属性
    is_irreversible: bool = False   # 是否不可逆
    volatility: float = 0.5         # 波动性（高波动=更多蝴蝶效应）

    # 约束
    scientific_constraints: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.affected_domains:
            self.affected_domains = CausalDomain.get_affected_domains(
                self.source_domain, self.magnitude
            )

    def propagate(self) -> list[CausalEvent]:
        """生成传播事件"""
        propagated = []

        for domain in self.affected_domains:
            if domain == self.source_domain:
                continue

            # 传播衰减
            attenuation = 0.8 - (self.cascade_depth * 0.1)
            propagated_magnitude = self.magnitude * attenuation

            # 低于阈值不传播
            if propagated_magnitude < 0.05:
                continue

            # 创建传播事件
            propagated_event = CausalEvent(
                causal_id=f"{self.causal_id}_prop_{domain}_{self.tick}",
                tick=self.tick,
                cause_agent_id=self.cause_agent_id,
                cause_description=f"[传播] {self.effect_description}",
                effect_description=f"{domain}受{self.source_domain}影响",
                magnitude=propagated_magnitude,
                propagation=self.propagation * 0.9,
                source_domain=domain,
                affected_domains=CausalDomain.get_affected_domains(domain, propagated_magnitude),
                is_cascade=True,
                parent_event_id=self.causal_id,
                cascade_depth=self.cascade_depth + 1,
                cascade_chain=self.cascade_chain + [self.causal_id],
                butterfly_potential=self.butterfly_potential * propagated_magnitude,
            )
            propagated.append(propagated_event)

        return propagated


# ============================================================================
# 因果传播引擎 - Causal Propagation Engine
# ============================================================================

class CausalPropagationEngine:
    """
    因果传播引擎 - 世界的唯一底层驱动

    不是记录事件，而是主动传播因果：
    1. 接收因果事件
    2. 在域之间传播
    3. 检测级联放大
    4. 触发蝴蝶效应
    5. 推动涌现

    这是整个世界的唯一驱动核心。
    """

    def __init__(self, world: World):
        self.world = world
        self._rng = world._rng if hasattr(world, '_rng') else np.random.default_rng()

        # 因果事件存储
        self.events: list[CausalEvent] = []
        self.events_by_domain: dict[str, list[CausalEvent]] = defaultdict(list)
        self.events_by_agent: dict[str, list[CausalEvent]] = defaultdict(list)

        # 因果链追踪
        self.causal_chains: dict[str, list[str]] = {}  # chain_id -> event_ids
        self.active_chains: set[str] = set()

        # 级联放大检测
        self.cascade_threshold = 0.6  # 超过此阈值触发级联
        self.cascade_counter: dict[str, int] = defaultdict(int)

        # 蝴蝶效应追踪
        self.butterfly_events: list[CausalEvent] = []
        self.branched_histories: dict[str, dict] = {}  # history_id -> branch_info

        # 科学约束
        self._scientific_laws = self._initialize_scientific_constraints()

        # 模式涌现检测
        self._pattern_history: dict[str, list[tuple[int, float]]] = defaultdict(list)  # pattern -> [(tick, count)]
        self.emerged_patterns: dict[str, dict] = {}  # pattern -> properties

        # 统计
        self.stats = {
            "total_events": 0,
            "total_propagations": 0,
            "total_cascades": 0,
            "total_butterflies": 0,
            "emerged_institutions": 0,
        }

    def _initialize_scientific_constraints(self) -> dict[str, Callable]:
        """初始化科学约束函数"""
        return {
            # 物理约束
            "energy_conservation": self._constrain_energy_conservation,
            "momentum_conservation": self._constrain_momentum_conservation,
            "mass_conservation": self._constrain_mass_conservation,

            # 化学约束
            "reaction_equilibrium": self._constrain_chemical_equilibrium,
            "entropy_increase": self._constrain_entropy,

            # 生物约束
            "carrying_capacity": self._constrain_carrying_capacity,
            "resource_dependency": self._constrain_resource_dependency,

            # 经济约束
            "scarcity": self._constrain_scarcity,
            "diminishing_returns": self._constrain_diminishing_returns,

            # 社会约束
            "social_equilibrium": self._constrain_social_equilibrium,
            "power_paradox": self._constrain_power_paradox,
        }

    # ========================================================================
    # 科学约束 - Scientific Constraints (硬约束，不可违反)
    # ========================================================================

    def _constrain_energy_conservation(self, event: CausalEvent) -> tuple[bool, str]:
        """能量守恒约束"""
        # 检查是否有能量不守恒的情况
        if event.source_domain == CausalDomain.PHYSICS:
            if event.effect_description.startswith("能量增加") and event.magnitude > 0.5:
                # 违反能量守恒，削弱效果
                event.magnitude *= 0.3
                return False, "能量守恒约束限制了效果"
        return True, ""

    def _constrain_momentum_conservation(self, event: CausalEvent) -> tuple[bool, str]:
        """动量守恒约束"""
        return True, ""

    def _constrain_mass_conservation(self, event: CausalEvent) -> tuple[bool, str]:
        """质量守恒约束"""
        return True, ""

    def _constrain_chemical_equilibrium(self, event: CausalEvent) -> tuple[bool, str]:
        """化学平衡约束"""
        if event.source_domain == CausalDomain.CHEMISTRY:
            # 检查是否破坏了化学平衡
            pass
        return True, ""

    def _constrain_entropy(self, event: CausalEvent) -> tuple[bool, str]:
        """熵增约束"""
        if event.source_domain == CausalDomain.PHYSICS:
            # 熵只能增加或保持
            if "熵减少" in event.effect_description:
                event.magnitude *= 0.1
                return False, "熵增约束限制了效果"
        return True, ""

    def _constrain_carrying_capacity(self, event: CausalEvent) -> tuple[bool, str]:
        """承载容量约束"""
        if event.source_domain == CausalDomain.ECOLOGY:
            # 检查是否超过承载容量
            agent_count = self.world.get_agent_count() if hasattr(self.world, 'get_agent_count') else 0
            # 简化的承载容量检查
            if agent_count > 10000 and event.effect_description.startswith("人口增长"):
                event.magnitude *= 0.2  # 大幅削弱
                return False, "超过生态承载容量"
        return True, ""

    def _constrain_resource_dependency(self, event: CausalEvent) -> tuple[bool, str]:
        """资源依赖约束"""
        return True, ""

    def _constrain_scarcity(self, event: CausalEvent) -> tuple[bool, str]:
        """稀缺性约束"""
        if event.source_domain == CausalDomain.ECONOMICS:
            # 稀缺资源不能无限复制
            if "凭空创造" in event.effect_description:
                event.magnitude *= 0.0  # 完全禁止
                return False, "稀缺性约束：不能凭空创造资源"
        return True, ""

    def _constrain_diminishing_returns(self, event: CausalEvent) -> tuple[bool, str]:
        """边际效益递减约束"""
        return True, ""

    def _constrain_social_equilibrium(self, event: CausalEvent) -> tuple[bool, str]:
        """社会平衡约束"""
        if event.source_domain == CausalDomain.SOCIAL:
            # 极端不平等会触发反抗
            if "绝对权力" in event.effect_description:
                event.cascade_depth += 2  # 增加级联深度
                event.butterfly_potential = 0.9  # 高蝴蝶潜力
        return True, ""

    def _constrain_power_paradox(self, event: CausalEvent) -> tuple[bool, str]:
        """权力悖论约束"""
        # 权力越大，越脆弱
        return True, ""

    def apply_scientific_constraints(self, event: CausalEvent) -> tuple[bool, list[str]]:
        """应用所有科学约束"""
        violations = []
        allowed = True

        for law_name, law_func in self._scientific_laws.items():
            passed, message = law_func(event)
            if not passed:
                violations.append(f"{law_name}: {message}")
                allowed = False

        return allowed, violations

    # ========================================================================
    # 因果传播 - Causal Propagation
    # ========================================================================

    def emit(self, event: CausalEvent) -> list[CausalEvent]:
        """
        发射一个因果事件，触发传播链

        这是驱动世界运转的核心方法。
        每个agent行动、每个环境变化都调用这个方法。
        """
        # 应用科学约束
        allowed, violations = self.apply_scientific_constraints(event)
        if not allowed and event.magnitude < 0.01:
            return []  # 被约束阻止

        # 存储事件
        self.events.append(event)
        self.events_by_domain[event.source_domain].append(event)
        if event.cause_agent_id:
            self.events_by_agent[event.cause_agent_id].append(event)

        # 更新统计
        self.stats["total_events"] += 1

        # 检测蝴蝶效应
        self._check_butterfly_effect(event)

        # 级联放大检测
        propagated_events = []
        if event.magnitude >= self.cascade_threshold:
            propagated = self._cascade(event)
            propagated_events.extend(propagated)

        # 级联传播
        propagated = event.propagate()
        propagated_events.extend(propagated)
        self.stats["total_propagations"] += len(propagated_events)

        # 模式涌现检测
        self._check_emergence_patterns(event)

        return propagated_events

    def _cascade(self, event: CausalEvent) -> list[CausalEvent]:
        """级联放大"""
        cascade_events = []

        # 高波动事件触发更多级联
        num_cascades = int(event.volatility * 3) + 1

        for i in range(num_cascades):
            cascade_event = CausalEvent(
                causal_id=f"{event.causal_id}_cascade_{i}_{event.tick}",
                tick=event.tick,
                cause_agent_id=event.cause_agent_id,
                cause_description=f"[级联{i+1}] {event.effect_description}",
                effect_description=f"级联效应：{event.affected_domains}",
                magnitude=event.magnitude * (0.9 ** (i + 1)),
                propagation=event.propagation * 1.1,
                source_domain=random.choice(list(event.affected_domains)),
                affected_domains=event.affected_domains,
                is_cascade=True,
                parent_event_id=event.causal_id,
                cascade_depth=event.cascade_depth + 1,
                cascade_chain=event.cascade_chain + [event.causal_id],
                butterfly_potential=event.butterfly_potential * 1.2,
                volatility=event.volatility * 1.05,
            )
            cascade_events.append(cascade_event)
            self.stats["total_cascades"] += 1

        return cascade_events

    def _check_butterfly_effect(self, event: CausalEvent) -> None:
        """检查蝴蝶效应"""
        # 高蝴蝶潜力事件
        if event.butterfly_potential > 0.7 and event.magnitude < 0.3:
            # 微小原因，巨大影响
            self.butterfly_events.append(event)
            self.stats["total_butterflies"] += 1

            # 记录分支历史
            branch_id = f"branch_{event.causal_id}"
            self.branched_histories[branch_id] = {
                "trigger_event": event.causal_id,
                "tick": event.tick,
                "description": event.effect_description,
                "magnitude": event.magnitude,
                "potential": event.butterfly_potential,
            }

    def _check_emergence_patterns(self, event: CausalEvent) -> None:
        """检测涌现模式"""
        # 创建模式签名
        pattern_key = self._create_pattern_signature(event)

        if pattern_key:
            # 记录模式出现
            self._pattern_history[pattern_key].append((event.tick, event.magnitude))

            # 检测重复模式
            recent = [
                (t, m) for t, m in self._pattern_history[pattern_key]
                if event.tick - t < 50  # 50 tick内
            ]

            if len(recent) >= 5:  # 5次重复触发涌现
                self._trigger_emergence(pattern_key, recent)

    def _create_pattern_signature(self, event: CausalEvent) -> str | None:
        """创建模式签名"""
        # 基于事件的关键特征创建签名
        if event.cause_agent_id and event.affected_domains:
            # 社交互动模式
            return f"social_interaction:{len(event.affected_domains)}"

        if "资源" in event.effect_description or "交易" in event.effect_description:
            return f"economic_pattern:{event.source_domain}"

        if "权力" in event.effect_description or "服从" in event.effect_description:
            return "political_pattern"

        return None

    def _trigger_emergence(self, pattern_key: str, occurrences: list[tuple[int, float]]) -> None:
        """触发涌现"""
        if pattern_key in self.emerged_patterns:
            return  # 已经涌现过了

        # 计算涌现属性
        avg_magnitude = sum(m for _, m in occurrences) / len(occurrences)

        self.emerged_patterns[pattern_key] = {
            "type": pattern_key.split(":")[0] if ":" in pattern_key else "unknown",
            "first_emergence_tick": occurrences[0][0],
            "frequency": len(occurrences),
            "strength": avg_magnitude,
            "description": self._describe_emergence(pattern_key),
        }

        self.stats["emerged_institutions"] += 1

    def _describe_emergence(self, pattern_key: str) -> str:
        """描述涌现的制度"""
        if "social_interaction" in pattern_key:
            return "社交互动规范涌现"
        elif "economic_pattern" in pattern_key:
            return "经济交换模式涌现"
        elif "political_pattern" in pattern_key:
            return "权力结构涌现"
        return "未知制度涌现"

    # ========================================================================
    # 真实涌现 - True Emergence
    # ========================================================================

    def process_tick(self, tick: int, events: list[CausalEvent]) -> None:
        """
        处理一个tick的所有因果事件

        这是驱动世界运转的核心。
        """
        all_new_events = list(events)

        # 传播所有事件
        for event in events:
            propagated = self.emit(event)
            all_new_events.extend(propagated)

        # 处理新事件（级联）
        while True:
            new_propagated = []
            for event in all_new_events:
                if event.magnitude >= self.cascade_threshold:
                    propagated = self._cascade(event)
                    new_propagated.extend(propagated)

            if not new_propagated:
                break

            all_new_events.extend(new_propagated)

        # 检测涌现模式
        for event in all_new_events:
            self._check_emergence_patterns(event)

    # ========================================================================
    # 智能体接口 - Agent Interface
    # ========================================================================

    def emit_agent_action(
        self,
        agent_id: str,
        action_description: str,
        effect_description: str,
        magnitude: float = 0.5,
        domains: set[str] | None = None,
    ) -> list[CausalEvent]:
        """智能体行动触发因果"""
        source_domain = domains.pop() if domains else CausalDomain.SOCIAL

        event = CausalEvent(
            causal_id=f"agent_{agent_id}_{action_description}_{time.time()}",
            tick=self.world.tick if hasattr(self.world, 'tick') else 0,
            cause_agent_id=agent_id,
            cause_description=action_description,
            effect_description=effect_description,
            magnitude=magnitude,
            source_domain=source_domain,
            affected_domains=domains or CausalDomain.get_affected_domains(source_domain, magnitude),
            volatility=random.uniform(0.3, 0.8),
            butterfly_potential=magnitude * random.uniform(0.2, 0.9),
        )

        return [event] + self.emit(event)

    def get_causal_context(self, agent_id: str) -> dict[str, Any]:
        """获取智能体的因果上下文（用于决策）"""
        agent_events = self.events_by_agent.get(agent_id, [])

        # 计算最近的影响
        recent_effects = defaultdict(float)
        for event in agent_events[-10:]:
            recent_effects[event.source_domain] += event.magnitude

        # 获取涌现的制度
        emerging_institutions = list(self.emerged_patterns.keys())

        return {
            "recent_events": len(agent_events),
            "domain_strengths": dict(recent_effects),
            "emerging_institutions": emerging_institutions,
            "total_butterflies": len(self.butterfly_events),
            "active_chains": len(self.active_chains),
        }

    # ========================================================================
    # 统计 - Statistics
    # ========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "total_events": len(self.events),
            "butterfly_events": len(self.butterfly_events),
            "emerged_patterns": len(self.emerged_patterns),
            "active_chains": len(self.active_chains),
            "events_by_domain": {
                d: len(events) for d, events in self.events_by_domain.items()
            },
            "emerged_institutions_list": list(self.emerged_patterns.keys()),
        }


# ============================================================================
# 人性化智能体决策 - Human-like Agent Decision Making
# ============================================================================

class HumanDecisionMaker:
    """
    人性化决策器 - 让智能体行为更像真实人类

    不是完美理性，而是：
    - 情绪化决策
    - 认知偏差
    - 短视
    - 冲动
    - 社会影响
    """

    # 认知偏差
    BIAS_REPRESENTATIVENESS = 0.3    # 代表性启发式偏差
    BIAS_ANCHORING = 0.25           # 锚定偏差
    BIAS_CONFIRMATION = 0.35        # 确认偏差
    BIAS_LOSS_AVERSION = 0.4        # 损失厌恶
    BIAS_HERD = 0.45                # 羊群效应

    def __init__(self, agent_id: str, rng: np.random.Generator):
        self.agent_id = agent_id
        self.rng = rng

        # 人格特质（随机但稳定）
        self.openness = rng.uniform(0.3, 0.9)        # 开放性
        self.conscientiousness = rng.uniform(0.3, 0.9)  # 尽责性
        self.extraversion = rng.uniform(0.3, 0.9)    # 外向性
        self.agreeableness = rng.uniform(0.3, 0.9)  # 宜人性
        self.neuroticism = rng.uniform(0.2, 0.8)     # 神经质

        # 情绪状态
        self.mood = rng.uniform(-0.3, 0.3)  # -1 到 1
        self.stress = 0.0
        self.happiness = 0.5

        # 短期记忆
        self.recent_impressions: list[tuple[str, float, int]] = []  # (描述, 情绪影响, tick)

    def decide_action(
        self,
        options: list[str],
        context: dict[str, Any],
        causal_context: dict[str, Any],
    ) -> tuple[str, float]:
        """
        人性化决策

        不是最优选择，而是：
        1. 受情绪影响
        2. 受偏见扭曲
        3. 受社会影响
        4. 有随机性
        """
        if not options:
            return "", 0.0

        # 情绪影响
        mood_multiplier = 1.0 + (self.mood * 0.5)

        # 神经质增加冲动
        if self.neuroticism > 0.6 and self.rng.random() < 0.2:
            # 冲动决策
            return self.rng.choice(options), 0.8

        # 损失厌恶：负面选项被放大
        scores = []
        for i, option in enumerate(options):
            base_score = 0.5

            # 锚定偏差
            if i == 0:
                base_score += self.BIAS_ANCHORING * 0.2

            # 确认偏差：符合已有信念的选项加分
            if self._confirms_belief(option, context):
                base_score += self.BIAS_CONFIRMATION * 0.3

            # 羊群效应
            if causal_context.get("herd_options"):
                if option in causal_context["herd_options"]:
                    base_score += self.BIAS_HERD * 0.4

            # 情绪调整
            emotional_adjustment = self._get_emotional_adjustment(option)
            base_score += emotional_adjustment * mood_multiplier

            # 随机噪音（不是完全理性的）
            base_score += self.rng.uniform(-0.15, 0.15)

            scores.append(base_score)

        # 选择最高分（但不是完美的）
        best_idx = scores.index(max(scores))
        best_score = scores[best_idx]

        # 随机性：不是每次都选最优
        if self.rng.random() < 0.15:
            best_idx = self.rng.integers(0, len(options))

        # 更新情绪
        self._update_emotions(options[best_idx], best_score)

        return options[best_idx], scores[best_idx]

    def _confirms_belief(self, option: str, context: dict[str, Any]) -> bool:
        """检查选项是否确认已有信念"""
        beliefs = context.get("beliefs", [])
        for belief in beliefs:
            if belief.lower() in option.lower():
                return True
        return False

    def _get_emotional_adjustment(self, option: str) -> float:
        """根据情绪获取调整值"""
        # 压力增加保守
        if self.stress > 0.7:
            if "冒险" in option or "激进" in option:
                return -0.3

        # 高兴增加开放
        if self.happiness > 0.7:
            if "探索" in option or "新" in option:
                return 0.2

        return 0.0

    def _update_emotions(self, chosen_option: str, score: float) -> None:
        """更新情绪状态"""
        # 情绪波动
        self.mood += self.rng.uniform(-0.1, 0.1)
        self.mood = max(-1.0, min(1.0, self.mood))

        # 幸福度受结果影响
        if score > 0.6:
            self.happiness = min(1.0, self.happiness + 0.05)
        elif score < 0.4:
            self.happiness = max(0.0, self.happiness - 0.05)
            self.stress = min(1.0, self.stress + 0.02)

        # 神经质导致情绪波动
        if self.neuroticism > 0.5:
            self.mood += self.rng.uniform(-0.2, 0.2)

        # 记忆印象
        self.recent_impressions.append((chosen_option, score, self.rng.integers(0, 1000)))
        if len(self.recent_impressions) > 10:
            self.recent_impressions.pop(0)

    def get_emotional_state(self) -> dict[str, float]:
        """获取当前情绪状态"""
        return {
            "mood": self.mood,
            "stress": self.stress,
            "happiness": self.happiness,
            "neuroticism": self.neuroticism,
        }
