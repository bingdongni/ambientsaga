"""
真实人类智能体 (Human-Like Agent)

核心特性：
1. 非理性决策 - 认知偏差、情绪波动、短期利益
2. 情境依赖 - 根据环境做出不同决策
3. 社会嵌入 - 受群体影响、关系网络
4. 动态学习 - 从交互中学习，不断调整行为
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class CognitiveBias(Enum):
    """认知偏差类型"""
    CONFIRMATION_BIAS = auto()     # 确认偏差
    AVAILABILITY_HEURISTIC = auto()  # 可得性启发
    ANCHORING = auto()            # 锚定效应
    OVERCONFIDENCE = auto()       # 过度自信
    LOSS_AVERSION = auto()        # 损失厌恶
    HERDING = auto()              # 从众效应
    SUNK_COST = auto()            # 沉没成本谬误
    GAMBLERS_FALLACY = auto()     # 赌徒谬误


@dataclass
class EmotionalState:
    """情绪状态"""
    joy: float = 0.5          # 快乐 0-1
    sadness: float = 0.0       # 悲伤
    anger: float = 0.0         # 愤怒
    fear: float = 0.0          # 恐惧
    disgust: float = 0.0      # 厌恶
    surprise: float = 0.0      # 惊讶
    trust: float = 0.5         # 信任
    anticipation: float = 0.5 # 期待

    def normalize(self) -> None:
        """归一化情绪值"""
        total = self.joy + self.sadness + self.anger + self.fear + self.disgust + self.surprise
        if total > 1.0:
            self.joy /= total
            self.sadness /= total
            self.anger /= total
            self.fear /= total
            self.disgust /= total
            self.surprise /= total


@dataclass
class PersonalityTraits:
    """人格特质"""
    openness: float = 0.5        # 开放性
    conscientiousness: float = 0.5  # 尽责性
    extraversion: float = 0.5     # 外向性
    agreeableness: float = 0.5    # 宜人性
    neuroticism: float = 0.5     # 神经质

    # 行为倾向
    risk_seeking: float = 0.5    # 风险寻求
    competitiveness: float = 0.5  # 竞争性
    altruism: float = 0.3         # 利他主义
    reciprocity: float = 0.5      # 互惠
    patience: float = 0.3         # 耐心

    @classmethod
    def random(cls) -> PersonalityTraits:
        """随机生成人格特质"""
        return cls(
            openness=random.uniform(0.2, 0.8),
            conscientiousness=random.uniform(0.2, 0.8),
            extraversion=random.uniform(0.2, 0.8),
            agreeableness=random.uniform(0.2, 0.8),
            neuroticism=random.uniform(0.1, 0.9),
            risk_seeking=random.uniform(0.1, 0.9),
            competitiveness=random.uniform(0.2, 0.8),
            altruism=random.uniform(0.0, 0.6),
            reciprocity=random.uniform(0.3, 0.7),
            patience=random.uniform(0.1, 0.7),
        )


@dataclass
class IrrationalFactor:
    """非理性因素"""
    bias_type: CognitiveBias
    strength: float  # 0-1
    affected_decisions: list[str] = field(default_factory=list)


class HumanLikeAgent:
    """
    真实人类智能体

    模拟真实人类的行为特征：
    - 非理性决策
    - 情绪波动
    - 认知偏差
    - 社会影响
    - 情境依赖
    """

    def __init__(
        self,
        entity_id: str,
        name: str,
        position: Any,
        personality: PersonalityTraits | None = None,
    ) -> None:
        self.entity_id = entity_id
        self.name = name
        self.position = position

        # 人格特质
        self.personality = personality or PersonalityTraits.random()

        # 情绪状态
        self.emotions = EmotionalState()

        # 认知偏差
        self.cognitive_biases: list[IrrationalFactor] = self._generate_cognitive_biases()

        # 心理历史（影响当前决策）
        self.psychological_history: list[dict] = []  # {tick, event, emotional_impact}

        # 社会关系
        self.relationships: dict[str, float] = {}  # agent_id -> trust (-1 to 1)
        self.group_affiliations: list[str] = []

        # 近期记忆（带衰减的记忆）
        self.recent_memories: list[dict] = []  # {tick, content, strength}
        self.max_recent_memories = 50

        # 当前状态
        self.current_goal: str | None = None
        self.frustration_level: float = 0.0
        self.satisfaction_level: float = 0.5

    def _generate_cognitive_biases(self) -> list[IrrationalFactor]:
        """生成认知偏差组合"""
        biases = []

        # 确认偏差（几乎人人都有）
        biases.append(IrrationalFactor(
            bias_type=CognitiveBias.CONFIRMATION_BIAS,
            strength=random.uniform(0.3, 0.8),
        ))

        # 损失厌恶（普遍存在）
        biases.append(IrrationalFactor(
            bias_type=CognitiveBias.LOSS_AVERSION,
            strength=random.uniform(1.5, 2.5),  # 损失影响约为收益的1.5-2.5倍
        ))

        # 随机添加其他偏差
        if random.random() > 0.5:
            biases.append(IrrationalFactor(
                bias_type=CognitiveBias.HERDING,
                strength=random.uniform(0.2, 0.7),
            ))

        if random.random() > 0.6:
            biases.append(IrrationalFactor(
                bias_type=CognitiveBias.AVAILABILITY_HEURISTIC,
                strength=random.uniform(0.3, 0.6),
            ))

        if random.random() > 0.7:
            biases.append(IrrationalFactor(
                bias_type=CognitiveBias.OVERCONFIDENCE,
                strength=random.uniform(1.1, 1.5),
            ))

        return biases

    def make_decision(
        self,
        perception: dict,
        available_actions: list[dict],
        world: Any,
        tick: int,
    ) -> dict | None:
        """
        做出决策 - 融合理性与非理性

        Args:
            perception: 当前感知
            available_actions: 可用行动列表
            world: 世界状态
            tick: 当前时间

        Returns:
            选择的行动
        """
        if not available_actions:
            return None

        # 1. 理性评估（基础）
        rational_scores = self._rational_evaluation(available_actions, perception, world)

        # 2. 情绪影响
        emotional_modifier = self._calculate_emotional_modifier()

        # 3. 认知偏差注入
        biased_scores = self._apply_cognitive_biases(
            rational_scores, available_actions, perception
        )

        # 4. 社会影响
        social_influence = self._calculate_social_influence(available_actions, world)

        # 5. 情境因素
        situational_factor = self._calculate_situational_factor(world, tick)

        # 6. 随机性（真实人类不可完全预测）
        randomness = random.uniform(-0.15, 0.15)

        # 组合所有因素
        final_scores = {}
        for i, action in enumerate(available_actions):
            action_id = action.get('id', str(i))
            rational = rational_scores.get(action_id, 0.5)
            bias_factor = biased_scores.get(action_id, 1.0)
            social = social_influence.get(action_id, 0.0)
            situational = situational_factor.get(action_id, 1.0)

            final_scores[action_id] = (
                rational * bias_factor * 0.35 +    # 理性评估
                emotional_modifier * 0.15 +         # 情绪影响
                social * 0.20 +                     # 社会影响
                situational * 0.10 +                # 情境因素
                randomness * 0.20                   # 随机性
            )

        # 选择最高分行动
        best_action_id = max(final_scores, key=final_scores.get)
        selected_action = next(
            (a for a in available_actions if a.get('id') == best_action_id),
            available_actions[0]
        )

        # 更新心理状态
        self._update_psychological_state(selected_action, tick)

        # 记录决策
        self._record_memory({
            'tick': tick,
            'type': 'decision',
            'action': selected_action,
            'scores': final_scores,
            'perception_hash': hash(str(perception)) % 1000000,
        })

        return selected_action

    def _rational_evaluation(
        self,
        actions: list[dict],
        perception: dict,
        world: Any,
    ) -> dict[str, float]:
        """
        理性评估 - 考虑长期利益和实际收益
        """
        scores = {}

        for action in actions:
            action_id = action.get('id', '')
            action.get('type', '')
            expected_outcome = action.get('expected_outcome', 0.5)
            cost = action.get('cost', 0.0)
            risk = action.get('risk', 0.0)

            # 净收益评估
            net_value = expected_outcome - cost

            # 风险调整（高风险厌恶者会降低高分行动）
            risk_adjustment = 1.0 - risk * (1.0 - self.personality.risk_seeking)

            # 时间折扣（耐心的人更考虑长期）
            time_horizon = action.get('time_horizon', 1)
            discount = self.personality.patience ** time_horizon

            # 计算综合分数
            score = net_value * risk_adjustment * discount

            scores[action_id] = max(0.0, min(1.0, score))

        return scores

    def _calculate_emotional_modifier(self) -> float:
        """
        计算情绪修正因子

        情绪积极时倾向于尝试新事物
        情绪消极时倾向于保守
        """
        # 综合情绪值
        mood = (
            self.emotions.joy * 0.3 +
            self.emotions.trust * 0.2 +
            self.emotions.anticipation * 0.2 -
            self.emotions.anger * 0.2 -
            self.emotions.fear * 0.2 -
            self.emotions.sadness * 0.2 +
            self.emotions.disgust * 0.1
        )

        # 映射到修正因子
        # 情绪正面：略微提高行动倾向
        # 情绪负面：降低行动倾向，可能做出冲动决策
        modifier = 0.5 + mood * 0.5

        # 神经质的人情绪波动更大
        modifier *= (0.5 + self.personality.neuroticism * 0.5)

        return modifier

    def _apply_cognitive_biases(
        self,
        rational_scores: dict[str, float],
        actions: list[dict],
        perception: dict,
    ) -> dict[str, float]:
        """
        应用认知偏差 - 导致非理性决策
        """
        biased_scores = rational_scores.copy()

        for bias in self.cognitive_biases:
            if bias.bias_type == CognitiveBias.CONFIRMATION_BIAS:
                # 确认偏差：偏好支持已有信念的行动
                for action in actions:
                    action_id = action.get('id', '')
                    if action_id in rational_scores:
                        # 寻找支持当前信念的证据
                        supporting_evidence = self._find_supporting_evidence(action, perception)
                        if supporting_evidence > 0:
                            biased_scores[action_id] *= (1 + supporting_evidence * bias.strength * 0.3)

            elif bias.bias_type == CognitiveBias.LOSS_AVERSION:
                # 损失厌恶：损失比收益影响更大
                for action in actions:
                    action_id = action.get('id', '')
                    if action_id in rational_scores:
                        if action.get('cost', 0) > action.get('expected_outcome', 0):
                            # 损失情境，放大负面感受
                            biased_scores[action_id] *= (1 / bias.strength)

            elif bias.bias_type == CognitiveBias.HERDING:
                # 从众效应：受多数人影响
                herd_effect = bias.strength * self.personality.extraversion * 0.2
                for action in actions:
                    action_id = action.get('id', '')
                    if action.get('popularity', 0.5) > 0.6:
                        biased_scores[action_id] += herd_effect

            elif bias.bias_type == CognitiveBias.OVERCONFIDENCE:
                # 过度自信：高估自己的判断能力
                for action in actions:
                    action_id = action.get('id', '')
                    if action_id in rational_scores:
                        biased_scores[action_id] *= bias.strength

            elif bias.bias_type == CognitiveBias.AVAILABILITY_HEURISTIC:
                # 可得性启发：近期事件权重过大
                recent_memory_strength = self._get_recent_memory_strength()
                for action in actions:
                    action_id = action.get('id', '')
                    if action_id in rational_scores:
                        if action.get('type') == self._get_recent_action_type():
                            # 与近期行动相似，权重增加
                            biased_scores[action_id] *= (1 + recent_memory_strength * 0.2)

        # 归一化
        max_score = max(biased_scores.values()) if biased_scores else 1.0
        if max_score > 0:
            for k in biased_scores:
                biased_scores[k] /= max_score

        return biased_scores

    def _find_supporting_evidence(self, action: dict, perception: dict) -> float:
        """寻找支持当前信念的证据"""
        # 简化的证据查找
        action_type = action.get('type', '')
        recent_beliefs = [m.get('action', {}).get('type') for m in self.recent_memories[-5:]]

        if action_type in recent_beliefs:
            return 0.5

        return 0.1

    def _get_recent_memory_strength(self) -> float:
        """获取近期记忆强度"""
        if not self.recent_memories:
            return 0.0

        recent = self.recent_memories[-3:]
        return sum(m.get('strength', 0.5) for m in recent) / len(recent)

    def _get_recent_action_type(self) -> str | None:
        """获取近期行动类型"""
        if not self.recent_memories:
            return None
        return self.recent_memories[-1].get('action', {}).get('type')

    def _calculate_social_influence(
        self,
        actions: list[dict],
        world: Any,
    ) -> dict[str, float]:
        """
        计算社会影响
        """
        influence = {}

        # 获取可观察到的其他人
        nearby_agents = world.get_agents_in_radius(
            self.position.x, self.position.y, radius=50
        )

        # 获取可观察的行动
        observed_actions = {}
        for agent in nearby_agents:
            if hasattr(agent, 'current_goal') and agent.current_goal:
                goal_type = agent.current_goal
                observed_actions[goal_type] = observed_actions.get(goal_type, 0) + 1

        # 计算社会影响
        for action in actions:
            action_id = action.get('id', '')
            action_type = action.get('type', '')

            # 被观察行动的频率
            observed_count = observed_actions.get(action_type, 0)
            total_nearby = len(nearby_agents) or 1

            # 影响力 = 从众倾向 * 可观察到的比例
            social_pressure = (observed_count / total_nearby) * self.personality.extraversion

            influence[action_id] = social_pressure

        return influence

    def _calculate_situational_factor(
        self,
        world: Any,
        tick: int,
    ) -> dict[str, float]:
        """
        计算情境因素

        紧急情况、可用资源、社会动荡等
        """
        factor = {}

        # 检查是否处于紧急状态
        is_urgent = self._check_urgency(world)

        # 资源可用性
        resource_level = self._get_resource_level(world)

        # 社会压力
        social_pressure = self._get_social_pressure(world)

        # 综合情境
        crisis_level = max(is_urgent, 1.0 - resource_level, social_pressure)

        for i in range(10):  # 假设10个可能行动
            action_id = str(i)

            if crisis_level > 0.7:
                # 危机情境：倾向于防御/逃跑行动
                factor[action_id] = 0.7
            elif crisis_level > 0.4:
                # 中等压力：保持现状倾向
                factor[action_id] = 0.9
            else:
                # 正常情境：开放新行动
                factor[action_id] = 1.0

        return factor

    def _check_urgency(self, world: Any) -> float:
        """检查紧急程度"""
        # 简化：基于健康和财富
        health = getattr(self, 'health', 0.5)
        wealth = getattr(self, 'wealth', 0.0)

        urgency = 0.0
        if health < 0.3:
            urgency = 0.8
        elif health < 0.5:
            urgency = 0.5
        elif wealth < 10:
            urgency = 0.3

        return urgency

    def _get_resource_level(self, world: Any) -> float:
        """获取资源水平"""
        # 简化
        wealth = getattr(self, 'wealth', 0.0)
        return min(wealth / 100, 1.0)

    def _get_social_pressure(self, world: Any) -> float:
        """获取社会压力"""
        # 检查是否有冲突
        conflict_count = 0
        for _other_id, trust in self.relationships.items():
            if trust < -0.3:
                conflict_count += 1

        return min(conflict_count * 0.2, 1.0)

    def _update_psychological_state(self, action: dict, tick: int) -> None:
        """更新心理状态"""
        action_type = action.get('type', '')
        outcome = action.get('outcome', 0.5)

        # 更新情绪
        if outcome > 0.7:
            self.emotions.joy += 0.1
            self.emotions.sadness = max(0, self.emotions.sadness - 0.05)
        elif outcome < 0.3:
            self.emotions.sadness += 0.1
            self.emotions.anger += 0.05

        # 情绪会随时间回归基线
        self._decay_emotions()

        # 归一化
        self.emotions.normalize()

        # 记录心理历史
        self.psychological_history.append({
            'tick': tick,
            'action': action_type,
            'outcome': outcome,
            'emotional_state': {
                'joy': self.emotions.joy,
                'sadness': self.emotions.sadness,
                'anger': self.emotions.anger,
            }
        })

        # 限制历史长度
        if len(self.psychological_history) > 100:
            self.psychological_history = self.psychological_history[-50:]

    def _decay_emotions(self) -> None:
        """情绪衰减 - 回归基线"""
        decay_rate = 0.05

        self.emotions.joy = self.emotions.joy * (1 - decay_rate) + 0.5 * decay_rate
        self.emotions.sadness *= (1 - decay_rate)
        self.emotions.anger *= (1 - decay_rate)
        self.emotions.fear *= (1 - decay_rate)
        self.emotions.trust = self.emotions.trust * (1 - decay_rate) + 0.5 * decay_rate

    def _record_memory(self, memory: dict) -> None:
        """记录记忆"""
        self.recent_memories.append(memory)

        if len(self.recent_memories) > self.max_recent_memories:
            self.recent_memories = self.recent_memories[-self.max_recent_memories:]

    def update_relationships(self, other_id: str, interaction_outcome: float) -> None:
        """
        更新与另一智能体的关系

        Args:
            other_id: 对方ID
            interaction_outcome: 交互结果 (-1 到 1)
        """
        current_trust = self.relationships.get(other_id, 0.0)

        # 信任更新
        if interaction_outcome > 0:
            trust_change = interaction_outcome * self.personality.reciprocity * 0.2
        else:
            trust_change = interaction_outcome * 0.3

        new_trust = current_trust + trust_change
        self.relationships[other_id] = max(-1.0, min(1.0, new_trust))

    def get_trust(self, other_id: str) -> float:
        """获取对某人的信任"""
        return self.relationships.get(other_id, 0.0)

    def get_state_summary(self) -> dict:
        """获取状态摘要"""
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'position': (self.position.x, self.position.y),
            'personality': {
                'risk_seeking': self.personality.risk_seeking,
                'altruism': self.personality.altruism,
                'patience': self.personality.patience,
                'neuroticism': self.personality.neuroticism,
            },
            'emotions': {
                'joy': self.emotions.joy,
                'trust': self.emotions.trust,
                'anger': self.emotions.anger,
                'fear': self.emotions.fear,
            },
            'cognitive_bias_count': len(self.cognitive_biases),
            'relationship_count': len(self.relationships),
            'memory_count': len(self.recent_memories),
        }
