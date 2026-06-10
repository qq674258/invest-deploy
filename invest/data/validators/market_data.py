from __future__ import annotations

from invest.data.providers.base import MacroPoint, OhlcvBar


class ValidationError(Exception):
    pass


def validate_ohlcv_bar(bar: OhlcvBar) -> None:
    if bar.low > bar.high:
        raise ValidationError(f"low > high: {bar.trade_date}")
    if not (bar.low <= bar.open <= bar.high):
        raise ValidationError(f"open out of range: {bar.trade_date}")
    if not (bar.low <= bar.close <= bar.high):
        raise ValidationError(f"close out of range: {bar.trade_date}")
    if bar.volume < 0:
        raise ValidationError(f"negative volume: {bar.trade_date}")
    if bar.close <= 0:
        raise ValidationError(f"non-positive close: {bar.trade_date}")


def validate_macro_point(point: MacroPoint) -> None:
    if point.value != point.value:  # NaN
        raise ValidationError(f"NaN macro value: {point.trade_date}")


def validate_price_jump(prev_close: float, close: float, threshold: float) -> None:
    if prev_close <= 0:
        return
    change = abs(close / prev_close - 1.0)
    if change > threshold:
        raise ValidationError(
            f"abnormal jump {change:.1%}: {prev_close} -> {close}"
        )


def should_write(new_status: str, existing_status: str | None) -> bool:
    if existing_status is None:
        return True
    if existing_status == "official" and new_status == "provisional":
        return False
    return True
