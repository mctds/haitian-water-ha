"""常量定义。"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "haitian_water"
NAME: Final = "海天水务"
MANUFACTURER: Final = "海天水务"
MODEL: Final = "水费查询"

BASE_URL: Final = "https://tchal.haitianshuiwu.cn"
CLIENT_ID: Final = "WeiXinSmallProg_App"
CLIENT_SECRET: Final = "1q2w3e*"
DEFAULT_TENANT: Final = "cdlz"

USER_AGENT: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT: Final = 20

CONF_TOKEN: Final = "token"
CONF_TENANT: Final = "tenant"
CONF_CUST_ID: Final = "cust_id"
CONF_CUST_CODE: Final = "cust_code"
CONF_CUST_NAME: Final = "cust_name"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL_HOURS: Final = 6
MIN_SCAN_INTERVAL_HOURS: Final = 1
MAX_SCAN_INTERVAL_HOURS: Final = 168

# 令牌保活间隔（秒）。小程序侧令牌较短命，靠 relogin 滚动续期。
TOKEN_KEEPALIVE_SECONDS: Final = 600

BILL_HISTORY_COUNT: Final = 13
