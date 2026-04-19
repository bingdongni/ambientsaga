"""
History Module - 历史蝴蝶效应系统

确保模拟的唯一性和不可预测性，实现真实的历史分叉。
"""

from ambientsaga.history.butterfly import (
    BifurcationPoint,
    ButterflyEvent,
    HistoricalButterflySystem,
    HistoricalPath,
)

__all__ = [
    "HistoricalButterflySystem",
    "ButterflyEvent",
    "BifurcationPoint",
    "HistoricalPath",
]
