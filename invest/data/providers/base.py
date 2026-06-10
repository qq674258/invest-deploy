from dataclasses import dataclass
from datetime import date


@dataclass
class OhlcvBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class MacroPoint:
    trade_date: date
    value: float
