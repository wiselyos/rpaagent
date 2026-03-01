"""
RPA Module - 电商自动化系统 RPA 模块
"""

from .playwright_helper import (
    PlaywrightHelper,
    BrowserConfig,
    PagePool,
    create_browser
)

from .utils.anti_detection import (
    UserAgentRotator,
    Proxy,
    ProxyPool,
    RateLimiter,
    AntiDetectionManager,
    create_anti_detection_manager,
    get_random_viewport,
    get_random_timezone,
    get_random_locale
)

from .scrapers.price_monitor import (
    PriceData,
    BasePriceScraper,
    TaobaoScraper,
    JDScraper,
    PDDScraper,
    PriceMonitor
)

from .scrapers.product_info import (
    ProductImage,
    ProductSpec,
    ProductInfo,
    BaseProductScraper,
    TaobaoProductScraper,
    JDProductScraper,
    PDDProductScraper,
    ProductInfoManager
)

__version__ = "0.1.0"

__all__ = [
    # Playwright Helper
    "PlaywrightHelper",
    "BrowserConfig",
    "PagePool",
    "create_browser",
    
    # Anti-Detection
    "UserAgentRotator",
    "Proxy",
    "ProxyPool",
    "RateLimiter",
    "AntiDetectionManager",
    "create_anti_detection_manager",
    "get_random_viewport",
    "get_random_timezone",
    "get_random_locale",
    
    # Price Monitor
    "PriceData",
    "BasePriceScraper",
    "TaobaoScraper",
    "JDScraper",
    "PDDScraper",
    "PriceMonitor",
    
    # Product Info
    "ProductImage",
    "ProductSpec",
    "ProductInfo",
    "BaseProductScraper",
    "TaobaoProductScraper",
    "JDProductScraper",
    "PDDProductScraper",
    "ProductInfoManager",
]
