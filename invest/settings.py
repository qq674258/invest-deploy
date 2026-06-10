from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(DATA_DIR / 'invest.db').as_posix()}"
    fred_api_key: str = ""
    crawl_user_agent: str = "InvestAnalyzer/1.0"
    log_level: str = "INFO"
    # 行情回溯：默认近 1 年（自然日）；可用 OHLCV_LOOKBACK_DAYS 覆盖
    ohlcv_lookback_years: float = 1.0
    ohlcv_lookback_days: int = 0
    crawl_retry: int = 3
    crawl_retry_interval_sec: int = 20
    price_jump_threshold: float = 0.15
    # 可选：http://127.0.0.1:10808（Clash 等）；留空则自动读 Windows 系统代理
    http_proxy: str = ""
    # 简易管理后台（请在 .env 中修改默认密码）
    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_secret: str = ""
    smtp_password: str = ""


settings = Settings()


def get_ohlcv_lookback_days(override: int | None = None) -> int:
    """交易日历自然日跨度，供 yfinance / FRED 拉历史。"""
    from invest.core.crawl_config import get_ohlcv_lookback_from_config

    return get_ohlcv_lookback_from_config(override)
