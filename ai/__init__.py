"""
AI 模块初始化文件
电商自动化系统 - AI 模块

包含：
- 智能选品 (Product Selector)
- 价格预测 (Price Predictor)
- 意图分类 (Intent Classifier)
- 情感分析 (Sentiment Analyzer)
"""

from .product_selector import (
    ProductSelector,
    ProductMetrics,
    SelectionResult,
    create_selector,
    quick_select
)

from .price_predictor import (
    PricePredictor,
    PricePoint,
    PricePrediction,
    PricingStrategy,
    PriceTrend,
    quick_predict
)

from .intent_classifier import (
    IntentClassifier,
    Intent,
    IntentType,
    IntentRule,
    quick_classify,
    batch_classify
)

from .sentiment_analyzer import (
    SentimentAnalyzer,
    SentimentResult,
    ReviewBatch,
    SentimentType,
    AlertLevel,
    quick_analyze,
    batch_analyze
)

__version__ = "1.0.0"
__all__ = [
    # 智能选品
    "ProductSelector",
    "ProductMetrics",
    "SelectionResult",
    "create_selector",
    "quick_select",
    
    # 价格预测
    "PricePredictor",
    "PricePoint",
    "PricePrediction",
    "PricingStrategy",
    "PriceTrend",
    "quick_predict",
    
    # 意图分类
    "IntentClassifier",
    "Intent",
    "IntentType",
    "IntentRule",
    "quick_classify",
    "batch_classify",
    
    # 情感分析
    "SentimentAnalyzer",
    "SentimentResult",
    "ReviewBatch",
    "SentimentType",
    "AlertLevel",
    "quick_analyze",
    "batch_analyze",
]
