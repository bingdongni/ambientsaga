"""
真实涌现层 (True Emergence Layer)

核心原理：
从微观智能体的真实交互中自发产生宏观结构，
而非依赖预设信号或固定规则。

关键特性：
1. 无预设信号 - 信号从交互中动态产生
2. 模式检测 - 从重复交互中识别结构
3. 制度涌现 - 规范和制度自然形成
4. 市场涌现 - 交换模式形成价格
5. 文化涌现 - 共享符号和信念形成
"""

from __future__ import annotations

import numpy as np
import random
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict, Counter
from dataclasses import dataclass


@dataclass
class InteractionTrace:
    """交互痕迹"""
    trace_id: str
    tick: int
    actor_id: str
    target_id: str | None
    signal: str                    # 动态信号（而非预设枚举）
    content: dict                  # 动态内容
    outcome: float                 # 结果 (-1 到 1)
    context: dict                  # 情境信息
    emerging_meaning: str | None   # 涌现出的含义


@dataclass
class EmergedPattern:
    """涌现模式"""
    pattern_id: str
    pattern_type: str               # "institution", "market", "norm", "language", "role"
    trigger_signals: list[str]     # 触发信号序列
    frequency: float               # 出现频率
    stability: float               # 稳定性
    participating_agents: set[str]   # 参与的智能体
    created_tick: int
    properties: dict                # 模式特有属性


class TrueEmergenceLayer:
    """
    真实涌现引擎

    从智能体交互中自发产生：
    - 社会规范
    - 经济制度
    - 市场结构
    - 语言符号
    - 社会角色
    """

    def __init__(self, world: Any) -> None:
        self.world = world

        # 交互痕迹记录
        self._traces: list[InteractionTrace] = []
        self._max_traces = 10000

        # 涌现模式注册表
        self._emerged_patterns: dict[str, EmergedPattern] = {}

        # 信号空间（动态扩展）
        self._signal_space: dict[str, int] = defaultdict(int)  # signal -> usage_count
        self._signal_meanings: dict[str, str] = {}              # signal -> meaning
        self._shared_signals: dict[str, float] = {}            # signal -> sharedness

        # 模式检测窗口
        self._pattern_window = 200  # ticks
        self._emergence_threshold = 0.7  # 涌现阈值
        self._stability_threshold = 3    # 稳定性要求

        # 因果关系追踪
        self._causal_chains: list[dict] = []

    def process_interaction(
        self,
        actor_id: str,
        target_id: str | None,
        signal: str,
        content: dict,
        outcome: float,
        context: dict,
        tick: int,
    ) -> InteractionTrace | None:
        """
        处理智能体交互，产生涌现效应

        Args:
            actor_id: 行动者ID
            target_id: 目标ID（可为None）
            signal: 交互信号（动态字符串）
            content: 交互内容
            outcome: 交互结果
            context: 情境信息
            tick: 当前时间

        Returns:
            交互痕迹
        """
        # 1. 创建痕迹
        trace = InteractionTrace(
            trace_id=f"{tick}_{actor_id}_{random.randint(1000, 9999)}",
            tick=tick,
            actor_id=actor_id,
            target_id=target_id,
            signal=signal,
            content=content,
            outcome=outcome,
            context=context,
            emerging_meaning=None,
        )

        # 2. 记录信号使用
        self._signal_space[signal] += 1

        # 3. 检测/形成共享信号含义
        self._update_signal_meaning(trace)

        # 4. 检测涌现模式
        self._detect_emergence(trace, tick)

        # 5. 更新社会规范
        self._update_social_norms(trace)

        # 6. 更新因果链
        self._update_causal_chain(trace)

        # 7. 记录痕迹
        self._traces.append(trace)
        if len(self._traces) > self._max_traces:
            self._traces = self._traces[-5000:]

        return trace

    def _update_signal_meaning(self, trace: InteractionTrace) -> None:
        """
        更新信号的涌现含义

        当同一信号被多个智能体以相似方式使用时，
        其含义逐渐浮现
        """
        signal = trace.signal

        # 获取使用此信号的智能体
        signal_users = [
            t.actor_id for t in self._traces[-100:]
            if t.signal == signal
        ]

        # 计算共享程度
        unique_users = len(set(signal_users))
        total_uses = len(signal_users)

        sharedness = unique_users / max(total_uses, 1)
        self._shared_signals[signal] = sharedness

        # 如果共享程度高，尝试推断含义
        if sharedness > 0.5 and signal not in self._signal_meanings:
            meaning = self._infer_signal_meaning(trace)
            if meaning:
                self._signal_meanings[signal] = meaning
                trace.emerging_meaning = meaning

    def _infer_signal_meaning(self, trace: InteractionTrace) -> str | None:
        """
        推断信号的涌现含义

        基于使用模式推断
        """
        content = trace.content
        context = trace.context

        # 基于内容类型推断
        if 'resource' in content or 'give' in str(content).lower():
            return "exchange"
        elif 'help' in str(content).lower() or 'assist' in str(content).lower():
            return "cooperation"
        elif 'threat' in str(content).lower() or 'attack' in str(content).lower():
            return "conflict"
        elif 'promise' in str(content).lower() or 'commit' in str(content).lower():
            return "commitment"

        # 基于情境推断
        if trace.outcome > 0.5:
            return "positive_interaction"
        elif trace.outcome < -0.5:
            return "negative_interaction"

        return None

    def _detect_emergence(self, trace: InteractionTrace, tick: int) -> None:
        """
        检测涌现模式

        检查是否形成了新的制度、规范或结构
        """
        # 获取近期相关交互
        recent_traces = [t for t in self._traces[-self._pattern_window:]
                        if tick - t.tick < self._pattern_window]

        # 检测不同类型的涌现

        # 1. 互惠模式
        self._detect_reciprocity_pattern(recent_traces, tick)

        # 2. 交换模式（市场）
        self._detect_exchange_pattern(recent_traces, tick)

        # 3. 规范模式
        self._detect_norm_pattern(recent_traces, tick)

        # 4. 角色模式
        self._detect_role_pattern(recent_traces, tick)

        # 5. 语言模式
        self._detect_language_pattern(recent_traces, tick)

    def _detect_reciprocity_pattern(
        self,
        traces: list[InteractionTrace],
        tick: int,
    ) -> None:
        """
        检测互惠模式

        当A帮助B后，B倾向于帮助A
        """
        # 构建关系矩阵
        help_events: dict[tuple, list] = defaultdict(list)

        for t in traces:
            if t.signal in {'help', 'cooperate', 'gift', 'share'}:
                key = (t.actor_id, t.target_id)
                help_events[key].append(t)

        # 检测互惠
        for (a, b), events in help_events.items():
            reverse_key = (b, a)
            if reverse_key in help_events:
                # 存在互惠迹象
                mutual_events = len(events) + len(help_events[reverse_key])

                if mutual_events >= self._stability_threshold:
                    pattern_id = f"reciprocity_{a}_{b}"

                    if pattern_id not in self._emerged_patterns:
                        pattern = EmergedPattern(
                            pattern_id=pattern_id,
                            pattern_type="reciprocity",
                            trigger_signals=['help', 'cooperate'],
                            frequency=mutual_events / self._pattern_window,
                            stability=mutual_events,
                            participating_agents={a, b},
                            created_tick=tick,
                            properties={
                                'mutual_help_count': mutual_events,
                                'relationship_strength': 1.0,
                            }
                        )
                        self._emerged_patterns[pattern_id] = pattern

    def _detect_exchange_pattern(
        self,
        traces: list[InteractionTrace],
        tick: int,
    ) -> None:
        """
        检测交换模式（市场涌现）

        当多个智能体反复以相似比率交换资源时，
        市场机制涌现
        """
        # 收集交换事件
        exchanges: dict[tuple, list] = defaultdict(list)

        for t in traces:
            if 'exchange' in t.signal or 'give' in t.signal:
                if t.target_id:
                    key = (min(t.actor_id, t.target_id), max(t.actor_id, t.target_id))
                    exchanges[key].append(t)

        # 检测交换模式
        for (a, b), events in exchanges.items():
            if len(events) >= self._stability_threshold * 2:
                # 分析交换的资源类型
                resources = Counter()
                for e in events:
                    resources.update([k for k in e.content.keys() if k != 'type'])

                if len(resources) >= 2:
                    # 多资源交换，市场涌现
                    pattern_id = f"market_{a}_{b}"

                    if pattern_id not in self._emerged_patterns:
                        pattern = EmergedPattern(
                            pattern_id=pattern_id,
                            pattern_type="market",
                            trigger_signals=['exchange', 'give', 'take'],
                            frequency=len(events) / self._pattern_window,
                            stability=len(events),
                            participating_agents={a, b},
                            created_tick=tick,
                            properties={
                                'resources': dict(resources.most_common(5)),
                                'exchange_rate': self._calculate_exchange_rate(events),
                            }
                        )
                        self._emerged_patterns[pattern_id] = pattern

    def _detect_norm_pattern(
        self,
        traces: list[InteractionTrace],
        tick: int,
    ) -> None:
        """
        检测规范模式

        当某一行为模式被反复采用且结果正面时，规范涌现
        """
        # 按信号分组
        signal_outcomes: dict[str, list] = defaultdict(list)

        for t in traces:
            signal_outcomes[t.signal].append(t.outcome)

        # 检测高频正面信号
        for signal, outcomes in signal_outcomes.items():
            if len(outcomes) >= self._stability_threshold:
                avg_outcome = sum(outcomes) / len(outcomes)

                if avg_outcome > 0.3:
                    pattern_id = f"norm_{signal}"

                    if pattern_id not in self._emerged_patterns:
                        pattern = EmergedPattern(
                            pattern_id=pattern_id,
                            pattern_type="norm",
                            trigger_signals=[signal],
                            frequency=len(outcomes) / self._pattern_window,
                            stability=len(outcomes),
                            participating_agents=set(),
                            created_tick=tick,
                            properties={
                                'norm_signal': signal,
                                'avg_outcome': avg_outcome,
                                'compliance_rate': sum(1 for o in outcomes if o > 0) / len(outcomes),
                            }
                        )
                        self._emerged_patterns[pattern_id] = pattern

    def _detect_role_pattern(
        self,
        traces: list[InteractionTrace],
        tick: int,
    ) -> None:
        """
        检测社会角色

        当某一智能体反复执行相似行为时，角色涌现
        """
        # 按行动者分组
        actor_signals: dict[str, Counter] = defaultdict(Counter)

        for t in traces:
            actor_signals[t.actor_id][t.signal] += 1

        # 检测专精角色
        for actor, signals in actor_signals.items():
            if len(traces) >= 10:
                total = sum(signals.values())
                most_common = signals.most_common(1)[0]
                specialization = most_common[1] / total

                if specialization > 0.6 and total >= 5:
                    pattern_id = f"role_{actor}_{most_common[0]}"

                    if pattern_id not in self._emerged_patterns:
                        pattern = EmergedPattern(
                            pattern_id=pattern_id,
                            pattern_type="role",
                            trigger_signals=[most_common[0]],
                            frequency=specialization,
                            stability=total,
                            participating_agents={actor},
                            created_tick=tick,
                            properties={
                                'role_type': most_common[0],
                                'specialization': specialization,
                                'actions_performed': total,
                            }
                        )
                        self._emerged_patterns[pattern_id] = pattern

    def _detect_language_pattern(
        self,
        traces: list[InteractionTrace],
        tick: int,
    ) -> None:
        """
        检测语言模式

        当同一信号被多个智能体用于相似情境时，语言涌现
        """
        # 按信号和使用者分组
        signal_users: dict[str, set] = defaultdict(set)
        signal_contexts: dict[str, list] = defaultdict(list)

        for t in traces:
            signal_users[t.signal].add(t.actor_id)
            if t.target_id:
                signal_contexts[t.signal].append(
                    (t.content.get('type'), t.context.get('situation'))
                )

        # 检测共享语言
        for signal, users in signal_users.items():
            if len(users) >= 3 and self._shared_signals.get(signal, 0) > 0.5:
                pattern_id = f"language_{signal}"

                if pattern_id not in self._emerged_patterns:
                    # 检查是否真的是语言（用于相似上下文）
                    contexts = signal_contexts[signal]
                    if len(contexts) >= 3:
                        common_contexts = Counter(contexts).most_common(1)
                        if common_contexts[0][1] / len(contexts) > 0.4:
                            pattern = EmergedPattern(
                                pattern_id=pattern_id,
                                pattern_type="language",
                                trigger_signals=[signal],
                                frequency=self._shared_signals[signal],
                                stability=len(users),
                                participating_agents=users,
                                created_tick=tick,
                                properties={
                                    'vocabulary': signal,
                                    'meaning': self._signal_meanings.get(signal, 'unknown'),
                                    'speaker_count': len(users),
                                    'context_usage': common_contexts[0][0],
                                }
                            )
                            self._emerged_patterns[pattern_id] = pattern

    def _calculate_exchange_rate(self, events: list[InteractionTrace]) -> dict:
        """
        计算涌现的交换比率

        这是市场的核心属性
        """
        resources_given = Counter()
        resources_received = Counter()

        for e in events:
            content = e.content
            # 简化分析
            for k, v in content.items():
                if k != 'type' and isinstance(v, (int, float)):
                    resources_given[k] += abs(v) * 0.5
                    resources_received[k] += abs(v) * 0.5

        # 计算比率
        rates = {}
        all_resources = set(resources_given.keys()) | set(resources_received.keys())
        for r1 in all_resources:
            for r2 in all_resources:
                if r1 != r2 and resources_received[r1] > 0:
                    rate = resources_given[r2] / resources_received[r1]
                    if rate > 0:
                        rates[f"{r1}_per_{r2}"] = rate

        return rates

    def _update_social_norms(self, trace: InteractionTrace) -> None:
        """
        更新社会规范

        基于交互结果调整社会规范
        """
        # 简化：追踪哪些行为被社会接受
        if not hasattr(self.world, '_social_norms'):
            self.world._social_norms = {}

        signal = trace.signal

        if signal not in self.world._social_norms:
            self.world._social_norms[signal] = {
                'positive': 0,
                'negative': 0,
                'total': 0,
            }

        norm = self.world._social_norms[signal]
        norm['total'] += 1

        if trace.outcome > 0:
            norm['positive'] += 1
        elif trace.outcome < 0:
            norm['negative'] += 1

        # 计算社会认可度
        norm['acceptance'] = norm['positive'] / max(norm['total'], 1)

    def _update_causal_chain(self, trace: InteractionTrace) -> None:
        """
        更新因果链

        追踪交互的因果关系
        """
        self._causal_chains.append({
            'tick': trace.tick,
            'actor': trace.actor_id,
            'target': trace.target_id,
            'signal': trace.signal,
            'outcome': trace.outcome,
            'context': trace.context,
        })

        # 限制长度
        if len(self._causal_chains) > 5000:
            self._causal_chains = self._causal_chains[-2500:]

    def get_emerged_patterns(
        self,
        pattern_type: str | None = None,
    ) -> list[EmergedPattern]:
        """获取涌现模式"""
        patterns = list(self._emerged_patterns.values())

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        return patterns

    def get_shared_signals(self, threshold: float = 0.5) -> dict[str, str]:
        """获取共享信号（共同语言）"""
        return {
            signal: self._signal_meanings.get(signal, 'unknown')
            for signal, sharedness in self._shared_signals.items()
            if sharedness >= threshold
        }

    def get_social_norms(self) -> dict:
        """获取社会规范"""
        return getattr(self.world, '_social_norms', {})

    def get_causal_chain(
        self,
        agent_id: str | None = None,
        tick_range: tuple[int, int] | None = None,
    ) -> list[dict]:
        """获取因果链"""
        chains = self._causal_chains

        if agent_id:
            chains = [c for c in chains
                     if c['actor'] == agent_id or c['target'] == agent_id]

        if tick_range:
            chains = [c for c in chains
                     if tick_range[0] <= c['tick'] <= tick_range[1]]

        return chains

    def get_statistics(self) -> dict:
        """获取涌现层统计"""
        patterns_by_type = Counter(p.pattern_type for p in self._emerged_patterns.values())

        return {
            'total_traces': len(self._traces),
            'total_patterns': len(self._emerged_patterns),
            'patterns_by_type': dict(patterns_by_type),
            'signal_vocabulary_size': len(self._signal_space),
            'shared_signals_count': len(self._shared_signals),
            'causal_chain_length': len(self._causal_chains),
        }
