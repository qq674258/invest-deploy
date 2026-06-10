from datetime import date

import pytest

from invest.data.providers.base import OhlcvBar
from invest.data.validators.market_data import (
    ValidationError,
    should_write,
    validate_ohlcv_bar,
    validate_price_jump,
)


def test_validate_ohlcv_ok():
    bar = OhlcvBar(date(2024, 1, 2), 100, 105, 99, 103, 1e6)
    validate_ohlcv_bar(bar)


def test_validate_ohlcv_bad_low():
    bar = OhlcvBar(date(2024, 1, 2), 100, 105, 110, 103, 1e6)
    with pytest.raises(ValidationError):
        validate_ohlcv_bar(bar)


def test_price_jump():
    validate_price_jump(100, 110, 0.15)
    with pytest.raises(ValidationError):
        validate_price_jump(100, 130, 0.15)


def test_should_write():
    assert should_write("official", None)
    assert not should_write("provisional", "official")
    assert should_write("official", "provisional")
