"""
Agent Humanity Layer — 人性认知架构。

为Agent注入真实的人性：
- 情感感染与共鸣
- 认知偏差（损失厌恶、确认偏见、自利归因）
- 非理性行为（高压时随机性增加）
- 文化偏见（刻板印象、群体歧视）
- 短期主义（未来贴现因子）
- 背叛倾向与信任修复
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional
from enum import Enum, auto
import math
import random
from collections import defaultdict

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent


class EmotionType(Enum):
    """情绪类型"""
    JOY = auto()
    SADNESS = auto()
    ANGER = auto()
    FEAR = auto()
    DISGUST = auto()
    SURPRISE = auto()
    TRUST = auto()
    ANTICIPATION = auto()
    LOVE = auto()
    REMORSE = auto()
    ENVY = auto()
    CONTEMPT = auto()


@dataclass
class EmotionState:
    """情绪状态"""
    joy: float = 0.0       # 快乐
    sadness: float = 0.0   # 悲伤
    anger: float = 0.0     # 愤怒
    fear: float = 0.0      # 恐惧
    disgust: float = 0.0   # 厌恶
    surprise: float = 0.0   # 惊讶
    trust: float = 0.5     # 信任
    anticipation: float = 0.0  # 期待
    love: float = 0.0      # 爱
    remorse: float = 0.0   # 悔恨

    def to_dict(self) -> dict:
        return {
            "joy": self.joy,
            "sadness": self.sadness,
            "anger": self.anger,
            "fear": self.fear,
            "disgust": self.disgust,
            "surprise": self.surprise,
            "trust": self.trust,
            "anticipation": self.anticipation,
            "love": self.love,
            "remorse": self.remorse,
            "valence": self._calculate_valence(),
            "arousal": self._calculate_arousal()
        }

    def _calculate_valence(self) -> float:
        """情绪效价 (-1 负面, +1 正面)"""
        positive = self.joy + self.trust + self.love + self.anticipation
        negative = self.sadness + self.anger + self.fear + self.disgust + self.remorse
        total = positive + negative + 0.01
        return (positive - negative) / total

    def _calculate_arousal(self) -> float:
        """唤醒度 (0 平静, 1 激动)"""
        high_arousal = self.anger + self.fear + self.joy + self.surprise
        low_arousal = self.sadness + self.trust + self.remorse
        total = high_arousal + low_arousal + 0.01
        return high_arousal / total


@dataclass
class CognitiveBiases:
    """认知偏差"""
    # 损失厌恶：损失的痛苦是获得的2.25倍
    loss_aversion: float = 2.25

    # 确认偏见：对证实自己信念的信息过度重视
    confirmation_bias: float = 0.3

    # 自利归因：成功归自己，失败归外部
    self_serving_attribution: float = 0.4

    # 锚定效应：过度依赖第一个获得的信息
    anchoring: float = 0.5

    # 可用性启发：容易想到的事情被认为更可能
    availability_bias: float = 0.3

    # 过度自信：对自己的判断过度自信
    overconfidence: float = 0.3

    # 事后诸葛亮：认为事件是可预测的
    hindsight_bias: float = 0.3

    # 群体思维：为了共识牺牲批判性思维
    groupthink: float = 0.2

    # 偏见归因：对他人的负面行为归因于性格，对正面行为归因于情境
    attribution_bias: float = 0.3

    def apply_loss_aversion(self, gain: float, loss: float) -> float:
        """应用损失厌恶"""
        return gain - loss * self.loss_aversion

    def apply_confirmation_bias(self, evidence: dict, belief: str) -> float:
        """应用确认偏见"""
        weight = self.confirmation_bias
        if evidence.get("supports_" + belief, False):
            return weight
        else:
            return 1.0 - weight

    def apply_self_serving_attribution(self, success: bool) -> float:
        """应用自利归因"""
        if success:
            return 1.0 + self.self_serving_attribution
        else:
            return 1.0 - self.self_serving_attribution


@dataclass
class CulturalPrejudice:
    """文化偏见"""
    # 群体认同
    group_identity: str = "default"

    # 偏见强度 (0-1)
    prejudice_strength: float = 0.3

    # 偏见对象 → 态度
    stereotype_attitudes: dict[str, float] = field(default_factory=dict)

    # 内群体偏好
    in_group_bonus: float = 0.2

    # 外群体惩罚
    out_group_penalty: float = 0.2

    # 偏见历史 (用于学习)
    prejudice_history: list[dict] = field(default_factory=list)

    def get_attitude_toward(self, target_group: str) -> float:
        """获取对某群体的态度"""
        base = self.stereotype_attitudes.get(target_group, 0.0)
        if target_group == self.group_identity:
            return base + self.in_group_bonus
        else:
            return base - self.out_group_penalty

    def update_prejudice(self, target_group: str, interaction_result: float) -> None:
        """更新偏见 (基于交互结果)"""
        self.prejudice_history.append({
            "group": target_group,
            "result": interaction_result,
            "tick": 0
        })
        # 简单贝叶斯更新
        current = self.stereotype_attitudes.get(target_group, 0.0)
        self.stereotype_attitudes[target_group] = current * 0.9 + interaction_result * 0.1


@dataclass
class TrustNetwork:
    """信任网络"""
    # agent_id → (trust_score, betrayal_count, cooperation_count, last_interaction)
    trust_scores: dict[str, tuple[float, int, int, int]] = field(default_factory=dict)

    # 背叛倾向 (0-1)
    betrayal_tendency: float = 0.1

    # 信任阈值
    trust_threshold: float = 0.3

    # 报复倾向
    revenge_tendency: float = 0.3

    def get_trust(self, agent_id: str) -> float:
        """获取对某agent的信任"""
        if agent_id not in self.trust_scores:
            return 0.5  # 默认中性信任
        trust, _, _, _ = self.trust_scores[agent_id]
        return trust

    def record_interaction(self, agent_id: str, cooperation: bool, tick: int) -> None:
        """记录交互"""
        if agent_id not in self.trust_scores:
            self.trust_scores[agent_id] = (0.5, 0, 0, tick)

        trust, betrayals, cooperations, _ = self.trust_scores[agent_id]

        if cooperation:
            cooperations += 1
            # 信任增加
            trust = min(1.0, trust + 0.1 * (1 - trust))
        else:
            betrayals += 1
            # 信任下降
            trust = max(0.0, trust - 0.2 * trust)

        self.trust_scores[agent_id] = (trust, betrayals, cooperations, tick)

    def should_betray(self, agent_id: str, potential_gain: float, tick: int) -> bool:
        """判断是否应该背叛"""
        trust = self.get_trust(agent_id)

        # 基础背叛概率
        base_prob = self.betrayal_tendency

        # 如果信任低于阈值，增加背叛概率
        if trust < self.trust_threshold:
            base_prob += (self.trust_threshold - trust) * 0.5

        # 考虑潜在收益（损失厌恶）
        gain_factor = min(2.0, 1 + potential_gain * 0.01)

        # 考虑报复历史
        _, betrayals, cooperations, last_tick = self.trust_scores.get(agent_id, (0.5, 0, 0, 0))
        if betrayals > cooperations * 0.3:
            base_prob *= 1.5  # 对方有背叛历史

        # 距离上次交互越久，越容易背叛
        time_since = tick - last_tick
        time_factor = min(1.5, 1 + time_since * 0.001)

        final_prob = base_prob * gain_factor * time_factor

        return random.random() < final_prob

    def should_forgive(self, agent_id: str) -> bool:
        """判断是否应该原谅"""
        trust, betrayals, _, _ = self.trust_scores.get(agent_id, (0.5, 0, 0, 0))

        # 背叛次数越多，越难原谅
        forgiveness_prob = max(0.0, 0.5 - betrayals * 0.1)

        # 信任越高，越容易原谅
        forgiveness_prob += trust * 0.3

        return random.random() < forgiveness_prob


@dataclass
class TemporalPreference:
    """时间偏好（短期主义）"""
    # 未来贴现因子 (0-1, 越低越短视)
    discount_factor: float = 0.95

    # 即时满足权重
    instant_gratification: float = 0.3

    # 耐心 (与 discount_factor 相关)
    patience: float = 0.5

    def evaluate_options(self, options: list[tuple[float, float]]) -> tuple[int, float]:
        """
        评估选项
        options: [(immediate_reward, delayed_reward), ...]
        返回: (选择的选项索引, 期望效用)
        """
        best_idx = 0
        best_utility = float('-inf')

        for i, (immediate, delayed) in enumerate(options):
            utility = immediate * self.instant_gratification + delayed * self.discount_factor * (1 - self.instant_gratification)
            if utility > best_utility:
                best_utility = utility
                best_idx = i

        return best_idx, best_utility

    def get_present_value(self, future_value: float, delay: int) -> float:
        """计算现值"""
        return future_value * (self.discount_factor ** (delay / 10))


@dataclass
class IrrationalityEngine:
    """非理性引擎"""
    # 基础非理性水平 (0-1)
    base_irrationality: float = 0.2

    # 压力下的非理性增幅
    stress_amplifier: float = 0.5

    # 疲劳导致的非理性
    fatigue_irrationality: float = 0.3

    # 群体极化因子
    group_polarization: float = 0.2

    def calculate_irrationality(self, stress: float, fatigue: float, in_group: bool) -> float:
        """计算当前非理性水平"""
        irrational = self.base_irrationality
        irrational += stress * self.stress_amplifier
        irrational += fatigue * self.fatigue_irrationality
        irrational *= (1 + self.group_polarization if in_group else 1)
        return min(1.0, irrational)

    def make_irrational_choice(self, options: list[Any], irrationality: float) -> Any:
        """做出非理性选择"""
        # 正常选择
        normal_choice = max(options, key=lambda x: getattr(x, 'utility', 0))

        # 随机选择
        random_choice = random.choice(options)

        # 根据非理性水平混合
        if random.random() < irrationality:
            return random_choice
        return normal_choice

    def add_noise_to_value(self, value: float, irrationality: float) -> float:
        """添加噪声到数值评估"""
        noise = random.gauss(0, irrationality * abs(value) * 0.2)
        return value + noise


class AgentHumanityLayer:
    """
    Agent人性层。

    核心组件：
    1. EmotionState - 八种基本情绪 + 复合情绪
    2. CognitiveBiases - 10种认知偏差
    3. CulturalPrejudice - 文化偏见与群体认同
    4. TrustNetwork - 信任、背叛、报复
    5. TemporalPreference - 短期主义与未来折扣
    6. IrrationalityEngine - 高压/疲劳/群体极化下的非理性
    """

    def __init__(self, agent: "Agent"):
        self.agent = agent

        # 核心人性组件
        self.emotions = EmotionState()
        self.biases = CognitiveBiases()
        self.prejudice = CulturalPrejudice()
        self.trust = TrustNetwork()
        self.temporal = TemporalPreference()
        self.irrationality = IrrationalityEngine()

        # 状态追踪
        self.stress_level: float = 0.0
        self.fatigue: float = 0.0
        self.last_emotion_update: int = 0

    # ==================== 情绪系统 ====================

    def affect(self, emotion_type: EmotionType, intensity: float) -> None:
        """触发情绪"""
        current = getattr(self.emotions, emotion_type.name.lower())
        setattr(self.emotions, emotion_type.name.lower(), min(1.0, current + intensity))

        # 情绪感染相关情绪
        self._propagate_emotion(emotion_type, intensity)

    def _propagate_emotion(self, primary: EmotionType, intensity: float) -> None:
        """情绪感染相关情绪"""
        contagion_map = {
            EmotionType.JOY: {EmotionType.LOVE: 0.3, EmotionType.TRUST: 0.2},
            EmotionType.SADNESS: {EmotionType.FEAR: 0.2, EmotionType.REMORSE: 0.3},
            EmotionType.ANGER: {EmotionType.DISGUST: 0.3, EmotionType.ANTICIPATION: 0.2},
            EmotionType.FEAR: {EmotionType.SADNESS: 0.2, EmotionType.DISGUST: 0.2},
            EmotionType.LOVE: {EmotionType.JOY: 0.3, EmotionType.TRUST: 0.4},
            EmotionType.TRUST: {EmotionType.JOY: 0.2, EmotionType.LOVE: 0.3},
        }

        for secondary, contagion in contagion_map.get(primary, {}).items():
            current = getattr(self.emotions, secondary.name.lower())
            setattr(self.emotions, secondary.name.lower(), min(1.0, current + intensity * contagion))

    def decay_emotions(self, rate: float = 0.05) -> None:
        """情绪衰减"""
        for emotion in EmotionType:
            current = getattr(self.emotions, emotion.name.lower())
            if current > 0:
                setattr(self.emotions, emotion.name.lower(), max(0.0, current - rate))

    def get_mood(self) -> float:
        """获取当前心情 (-1 到 1)"""
        return self.emotions._calculate_valence()

    def get_stress(self) -> float:
        """获取压力水平"""
        stress_factors = [
            self.emotions.fear * 0.3,
            self.emotions.anger * 0.2,
            self.emotions.sadness * 0.2,
            1 - self.emotions.joy * 0.3,
        ]
        return min(1.0, sum(stress_factors))

    # ==================== 认知偏差 ====================

    def evaluate_outcome(self, gain: float, loss: float) -> float:
        """评估结果（应用损失厌恶）"""
        return self.biases.apply_loss_aversion(gain, loss)

    def filter_evidence(self, evidence: dict, belief: str) -> float:
        """过滤证据（应用确认偏见）"""
        return self.biases.apply_confirmation_bias(evidence, belief)

    def attribute_event(self, event: dict, is_success: bool) -> float:
        """归因事件（应用自利归因）"""
        return self.biases.apply_self_serving_attribution(is_success)

    # ==================== 文化偏见 ====================

    def get_prejudiced_attitude(self, target_group: str) -> float:
        """获取对目标群体的态度（考虑偏见）"""
        base_attitude = self.trust.get_trust(target_group)
        prejudice_effect = self.prejudice.get_attitude_toward(target_group)

        # 结合基础信任和偏见
        return base_attitude * 0.7 + prejudice_effect * 0.3

    def interact_with_group(self, target_group: str, result: float) -> None:
        """与群体交互后更新偏见"""
        self.prejudice.update_prejudice(target_group, result)

    def form_prejudice(self, target_group: str, observation: dict) -> None:
        """基于观察形成偏见"""
        if observation.get("observed_behavior") == "negative":
            self.prejudice.stereotype_attitudes[target_group] = \
                self.prejudice.stereotype_attitudes.get(target_group, 0) - 0.1
        elif observation.get("observed_behavior") == "positive":
            self.prejudice.stereotype_attitudes[target_group] = \
                self.prejudice.stereotype_attitudes.get(target_group, 0) + 0.05

    # ==================== 信任与背叛 ====================

    def should_cooperate(self, partner_id: str) -> bool:
        """判断是否应该合作"""
        trust = self.trust.get_trust(partner_id)

        # 基础合作概率
        base_prob = trust

        # 压力降低合作意愿
        stress = self.get_stress()
        base_prob -= stress * 0.3

        # 情绪影响
        if self.emotions.anger > 0.5:
            base_prob -= 0.2
        if self.emotions.remorse > 0.3:
            base_prob += 0.1

        # 考虑背叛倾向
        if self.trust.should_betray(partner_id, 10.0, self.agent.world.tick if hasattr(self.agent, 'world') else 0):
            return False

        return random.random() < max(0.0, base_prob)

    def record_cooperation(self, partner_id: str) -> None:
        """记录合作"""
        self.trust.record_interaction(partner_id, True, self.agent.world.tick if hasattr(self.agent, 'world') else 0)

    def record_betrayal(self, partner_id: str) -> None:
        """记录背叛"""
        self.trust.record_interaction(partner_id, False, self.agent.world.tick if hasattr(self.agent, 'world') else 0)

    # ==================== 时间偏好 ====================

    def choose_immediate_or_delayed(self, immediate_reward: float, delayed_reward: float, delay: int) -> bool:
        """选择即时满足还是延迟满足"""
        present_delayed = self.temporal.get_present_value(delayed_reward, delay)

        # 考虑非理性
        irrational = self.calculate_current_irrationality()
        present_delayed = self.irrationality.add_noise_to_value(present_delayed, irrational)

        return immediate_reward > present_delayed

    def calculate_present_value(self, future_value: float, delay: int) -> float:
        """计算现值"""
        return self.temporal.get_present_value(future_value, delay)

    # ==================== 非理性 ====================

    def calculate_current_irrationality(self) -> float:
        """计算当前非理性水平"""
        stress = self.get_stress()
        return self.irrationality.calculate_irrationality(
            stress=stress,
            fatigue=self.fatigue,
            in_group=False  # 可以根据情境调整
        )

    def make_decision_with_irrationality(self, options: list[dict]) -> dict:
        """在非理性影响下做决定"""
        irrational = self.calculate_current_irrationality()

        if irrational < 0.1:
            return max(options, key=lambda x: x.get('utility', 0))

        # 添加噪声到效用
        noisy_options = []
        for opt in options:
            noisy = opt.copy()
            noisy['utility'] = self.irrationality.add_noise_to_value(
                opt.get('utility', 0), irrational
            )
            noisy_options.append(noisy)

        # 选择
        return max(noisy_options, key=lambda x: x.get('utility', 0))

    # ==================== 综合决策 ====================

    def evaluate_interaction(self, partner_id: str, partner_group: str,
                           interaction_type: str, potential_gain: float) -> dict:
        """综合评估交互"""

        # 1. 获取情绪影响
        mood = self.get_mood()
        emotion_bonus = mood * 0.2

        # 2. 应用认知偏差
        perceived_gain = self.biases.apply_self_serving_attribution(True) * potential_gain

        # 3. 考虑偏见
        prejudice_modifier = self.get_prejudiced_attitude(partner_group)
        perceived_gain *= (0.5 + prejudice_modifier)

        # 4. 信任调整
        trust = self.trust.get_trust(partner_id)
        cooperation_prob = trust + emotion_bonus

        # 5. 决定是否合作
        cooperate = self.should_cooperate(partner_id)

        # 6. 计算最终效用
        if cooperate:
            utility = perceived_gain * cooperation_prob
        else:
            utility = self.biases.apply_loss_aversion(
                0, potential_gain * (1 - cooperation_prob)
            )

        # 7. 应用非理性
        final_utility = self.irrationality.add_noise_to_value(
            utility, self.calculate_current_irrationality()
        )

        return {
            "cooperate": cooperate,
            "utility": final_utility,
            "trust": trust,
            "prejudice": prejudice_modifier,
            "mood": mood,
            "irrationality": self.calculate_current_irrationality()
        }

    # ==================== 情绪感染 ====================

    def receive_emotional_contagion(self, source_emotion: dict) -> None:
        """接收情绪感染"""
        if not source_emotion:
            return

        # 情绪感染强度
        contagion_strength = 0.2

        for emotion_name, intensity in source_emotion.items():
            if hasattr(self.emotions, emotion_name):
                current = getattr(self.emotions, emotion_name)
                setattr(self.emotions, emotion_name,
                       min(1.0, current + intensity * contagion_strength))

    def get_emotional_state_for_sharing(self) -> dict:
        """获取可分享的情绪状态"""
        return self.emotions.to_dict()

    # ==================== 状态更新 ====================

    def update(self, tick: int) -> None:
        """更新人性层"""
        # 情绪衰减
        if tick - self.last_emotion_update > 10:
            self.decay_emotions()
            self.last_emotion_update = tick

        # 更新疲劳
        self.fatigue = min(1.0, self.fatigue + 0.01)

        # 压力积累/缓解
        stress = self.get_stress()
        if stress > 0.7:
            self.fatigue += 0.02

    def to_dict(self) -> dict:
        """导出状态"""
        return {
            "emotions": self.emotions.to_dict(),
            "biases": {
                "loss_aversion": self.biases.loss_aversion,
                "confirmation_bias": self.biases.confirmation_bias,
            },
            "prejudice": {
                "group": self.prejudice.group_identity,
                "strength": self.prejudice.prejudice_strength,
            },
            "temporal": {
                "discount_factor": self.temporal.discount_factor,
                "patience": self.temporal.patience,
            },
            "current_irrationality": self.calculate_current_irrationality(),
        }
