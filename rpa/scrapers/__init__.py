"""
RPA Scrapers Module
"""

from .price_monitor import (
    PriceData,
    BasePriceScraper,
    TaobaoScraper,
    JDScraper,
    PDDScraper,
    PriceMonitor
)

from .product_info import (
    ProductImage,
    ProductSpec,
    ProductInfo,
    BaseProductScraper,
    TaobaoProductScraper,
    JDProductScraper,
    PDDProductScraper,
    ProductInfoManager
)

__all__ = [
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
