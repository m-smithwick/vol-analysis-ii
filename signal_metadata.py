"""
Centralized signal metadata used across reports, charts, and backtests.

Keeping emoji + naming in one place prevents the drift that was showing up
between TXT, HTML, and PNG outputs.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SignalMeta:
    key: str
    name: str
    emoji: str
    description: str
    chart_marker: str = ""
    plural_suffix: str = "s"

    @property
    def display(self) -> str:
        return f"{self.emoji} {self.name}".strip()

    @property
    def chart_label(self) -> str:
        return self.display

    @property
    def pluralized(self) -> str:
        suffix = self.plural_suffix or ""
        return f"{self.name}{suffix}"


SIGNAL_METADATA: Dict[str, SignalMeta] = {
    # Entry signals
    "Strong_Buy": SignalMeta(
        key="Strong_Buy",
        name="Strong Buy",
        emoji="🟢",
        description="Score ≥7, near support, above VWAP",
        chart_marker="Large green dots",
    ),
    "Moderate_Buy": SignalMeta(
        key="Moderate_Buy",
        name="Moderate Buy",
        emoji="🟡",
        description="Score 5-7, divergence signals, above VWAP",
        chart_marker="Medium yellow dots",
    ),
    "Stealth_Accumulation": SignalMeta(
        key="Stealth_Accumulation",
        name="Stealth Accumulation",
        emoji="💎",
        description="High score, low volume, accumulation without price move",
        chart_marker="Cyan diamonds",
    ),
    "Confluence_Signal": SignalMeta(
        key="Confluence_Signal",
        name="Multi-Signal Confluence",
        emoji="⭐",
        description="All indicators aligned",
        chart_marker="Magenta stars",
    ),
    "Volume_Breakout": SignalMeta(
        key="Volume_Breakout",
        name="Volume Breakout",
        emoji="🔥",
        description="Volume >2.5x average with price strength",
        chart_marker="Orange triangles",
    ),
    # Exit signals
    "Profit_Taking": SignalMeta(
        key="Profit_Taking",
        name="Profit Taking",
        emoji="🟠",
        description="New highs with waning accumulation",
        chart_marker="Orange dots",
    ),
    "Distribution_Warning": SignalMeta(
        key="Distribution_Warning",
        name="Distribution Warning",
        emoji="⚠️",
        description="Early distribution signs",
        chart_marker="Gold squares",
    ),
    "Sell_Signal": SignalMeta(
        key="Sell_Signal",
        name="Sell Signal",
        emoji="🔴",
        description="Strong distribution below VWAP",
        chart_marker="Red dots",
    ),
    "Momentum_Exhaustion": SignalMeta(
        key="Momentum_Exhaustion",
        name="Momentum Exhaustion",
        emoji="💜",
        description="Rising price with declining volume",
        chart_marker="Purple X's",
    ),
    "Stop_Loss": SignalMeta(
        key="Stop_Loss",
        name="Stop Loss",
        emoji="🛑",
        description="Support breakdown / stop trigger",
        chart_marker="Dark red triangles",
    ),
    "MA_Crossdown": SignalMeta(
        key="MA_Crossdown",
        name="MA Crossdown",
        emoji="📉",
        description="Price crosses below moving average (trend failure)",
        chart_marker="Blue X's",
    ),
}


def get_signal_meta(key: str) -> SignalMeta:
    """Return metadata for a signal, falling back to a sensible default."""
    if key in SIGNAL_METADATA:
        return SIGNAL_METADATA[key]
    return SignalMeta(key=key, name=key.replace("_", " "), emoji="", description="")


def get_display_name(key: str) -> str:
    return get_signal_meta(key).display


def get_chart_label(key: str) -> str:
    return get_signal_meta(key).chart_label


def get_description(key: str) -> str:
    return get_signal_meta(key).description


def get_pluralized_name(key: str) -> str:
    return get_signal_meta(key).pluralized


def get_chart_marker(key: str) -> str:
    return get_signal_meta(key).chart_marker
