"""
情感分析模块 - Sentiment Analyzer
分析客户评价情感，识别负面评价预警
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np


class SentimentType(Enum):
    """情感类型枚举"""
    VERY_POSITIVE = "非常正面"
    POSITIVE = "正面"
    NEUTRAL = "中性"
    NEGATIVE = "负面"
    VERY_NEGATIVE = "非常负面"


class AlertLevel(Enum):
    """预警等级枚举"""
    NONE = "无预警"
    LOW = "低危"
    MEDIUM = "中危"
    HIGH = "高危"
    CRITICAL = "紧急"


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    sentiment: SentimentType
    score: float  # -1 到 1
    confidence: float
    aspects: Dict[str, float] = field(default_factory=dict)  # 各方面情感
    keywords: List[str] = field(default_factory=list)
    alert_level: AlertLevel = AlertLevel.NONE
    alert_reason: str = ""


@dataclass
class ReviewBatch:
    """批量评价分析结果"""
    total_reviews: int
    sentiment_distribution: Dict[str, int]
    average_score: float
    negative_reviews: List[SentimentResult]
    alert_count: int
    aspect_summary: Dict[str, float]


class SentimentAnalyzer:
    """
    情感分析器
    
    功能：
    1. 基于词典和规则的情感分析
    2. 细粒度方面情感分析 (产品、服务、物流等)
    3. 负面评价预警
    4. 可扩展为深度学习模型
    """
    
    def __init__(self, model_path: Optional[str] = None):
        # 情感词典
        self.positive_words: Set[str] = set()
        self.negative_words: Set[str] = set()
        self.intensifiers: Dict[str, float] = {}
        self.negations: Set[str] = set()
        
        # 方面关键词
        self.aspect_keywords = {
            "product": ["产品", "商品", "质量", "材质", "做工", "外观", "包装"],
            "service": ["客服", "服务", "态度", "回复", "售后", "处理"],
            "logistics": ["物流", "快递", "配送", "发货", "速度", "送货"],
            "price": ["价格", "性价比", "便宜", "贵", "划算", "值"],
        }
        
        # 预警规则
        self.alert_rules = {
            AlertLevel.CRITICAL: {
                "keywords": ["欺诈", "骗子", "假货", "伪劣", "危险", "爆炸", "中毒"],
                "min_score": -1.0,
                "max_score": -0.8
            },
            AlertLevel.HIGH: {
                "keywords": ["极差", "糟糕", "恶心", "垃圾", "骗人", "损坏", "破损"],
                "min_score": -0.8,
                "max_score": -0.6
            },
            AlertLevel.MEDIUM: {
                "keywords": ["失望", "不满", "差劲", "慢", "贵", "不值"],
                "min_score": -0.6,
                "max_score": -0.4
            },
            AlertLevel.LOW: {
                "keywords": ["一般", "还行", "凑合", "勉强"],
                "min_score": -0.4,
                "max_score": -0.2
            }
        }
        
        # 统计
        self.analysis_stats = {
            "total_analyzed": 0,
            "alert_triggered": 0,
            "sentiment_distribution": defaultdict(int)
        }
        
        self._init_dictionaries()
        
        if model_path and Path(model_path).exists():
            self.load(model_path)
    
    def _init_dictionaries(self) -> None:
        """初始化情感词典"""
        # 正面词
        self.positive_words = {
            "好", "棒", "优秀", "满意", "喜欢", "爱", "完美", "不错", "赞", "推荐",
            "超值", "划算", "便宜", "实惠", "精美", "漂亮", "好看", "舒适", "好用",
            "快速", "及时", "专业", "贴心", "周到", "热情", "耐心", "负责",
            "正品", "全新", "高质量", "耐用", "方便", "简单", "清晰", "准确",
            "惊喜", "感动", "开心", "愉快", "放心", "安心", "值得信赖", "回购",
            "五星", "好评", "给力", "靠谱", "真香", "yyds", "绝绝子", "爱了爱了"
        }
        
        # 负面词
        self.negative_words = {
            "差", "坏", "糟糕", "失望", "后悔", "垃圾", "烂", "恶心", "讨厌", "烦",
            "贵", "不值", "坑", "骗", "假", "伪劣", "劣质", "破损", "损坏", "坏掉",
            "慢", "迟", "拖延", "等太久", "不发货", "失联", "不理", "态度差",
            "难看", "丑", "粗糙", "廉价", "异味", "脏", "旧", "二手", "退货",
            "投诉", "维权", "曝光", "差评", "一星", "避雷", "踩雷", "翻车"
        }
        
        # 程度副词
        self.intensifiers = {
            "非常": 1.5, "特别": 1.4, "十分": 1.4, "很": 1.3, "太": 1.3,
            "相当": 1.3, "真的": 1.2, "比较": 1.1, "有点": 0.8, "稍微": 0.7,
            "略微": 0.7, "一般": 0.6, "不怎么": 0.5, "不太": 0.5, "根本不": 0.3
        }
        
        # 否定词
        self.negations = {
            "不", "没", "无", "非", "莫", "勿", "没有", "不是", "不能", "不会",
            "不可以", "不准", "拒绝", "反对", "否认"
        }
    
    def _segment_words(self, text: str) -> List[str]:
        """简单分词 (基于词典匹配)"""
        words = []
        i = 0
        text_len = len(text)
        
        while i < text_len:
            # 尝试匹配最长词
            matched = False
            for length in range(min(5, text_len - i), 0, -1):
                word = text[i:i+length]
                if (word in self.positive_words or 
                    word in self.negative_words or
                    word in self.intensifiers or
                    word in self.negations):
                    words.append(word)
                    i += length
                    matched = True
                    break
            
            if not matched:
                # 单字处理
                words.append(text[i])
                i += 1
        
        return words
    
    def _calculate_sentiment_score(self, text: str) -> Tuple[float, List[str]]:
        """
        计算情感分数
        
        Returns:
            (分数, 关键词列表)
        """
        words = self._segment_words(text)
        score = 0.0
        keywords = []
        
        i = 0
        while i < len(words):
            word = words[i]
            weight = 1.0
            
            # 检查前面的程度副词和否定词
            if i > 0:
                if words[i-1] in self.intensifiers:
                    weight *= self.intensifiers[words[i-1]]
                if words[i-1] in self.negations:
                    weight *= -1
            
            if i > 1 and words[i-2] in self.negations:
                weight *= -1
            
            # 计算情感词分数
            if word in self.positive_words:
                score += 1.0 * weight
                keywords.append(word)
            elif word in self.negative_words:
                score -= 1.0 * weight
                keywords.append(word)
            
            i += 1
        
        # 归一化到 -1 到 1
        if score != 0:
            score = max(-1, min(1, score / (len(words) * 0.1 + 1)))
        
        return score, keywords
    
    def _analyze_aspects(self, text: str) -> Dict[str, float]:
        """分析各方面情感"""
        aspects = {}
        
        for aspect, keywords in self.aspect_keywords.items():
            aspect_score = 0.0
            aspect_count = 0
            
            for keyword in keywords:
                if keyword in text:
                    # 提取关键词周围文本进行分析
                    idx = text.find(keyword)
                    context_start = max(0, idx - 10)
                    context_end = min(len(text), idx + 10)
                    context = text[context_start:context_end]
                    
                    score, _ = self._calculate_sentiment_score(context)
                    aspect_score += score
                    aspect_count += 1
            
            if aspect_count > 0:
                aspects[aspect] = round(aspect_score / aspect_count, 3)
        
        return aspects
    
    def _determine_sentiment_type(self, score: float) -> SentimentType:
        """根据分数确定情感类型"""
        if score >= 0.6:
            return SentimentType.VERY_POSITIVE
        elif score >= 0.2:
            return SentimentType.POSITIVE
        elif score >= -0.2:
            return SentimentType.NEUTRAL
        elif score >= -0.6:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.VERY_NEGATIVE
    
    def _check_alert(self, text: str, score: float) -> Tuple[AlertLevel, str]:
        """
        检查是否需要预警
        
        Returns:
            (预警等级, 原因)
        """
        # 检查关键词匹配
        for level, rules in sorted(
            self.alert_rules.items(), 
            key=lambda x: list(AlertLevel).index(x[0])
        ):
            for keyword in rules["keywords"]:
                if keyword in text:
                    return level, f"匹配敏感词: {keyword}"
        
        # 检查分数
        if score <= -0.8:
            return AlertLevel.HIGH, f"情感分数极低: {score:.2f}"
        elif score <= -0.6:
            return AlertLevel.MEDIUM, f"情感分数较低: {score:.2f}"
        elif score <= -0.4:
            return AlertLevel.LOW, f"情感分数偏低: {score:.2f}"
        
        return AlertLevel.NONE, ""
    
    def analyze(self, text: str) -> SentimentResult:
        """
        分析单条文本情感
        
        Args:
            text: 评价文本
            
        Returns:
            情感分析结果
        """
        # 计算整体情感分数
        score, keywords = self._calculate_sentiment_score(text)
        
        # 分析各方面情感
        aspects = self._analyze_aspects(text)
        
        # 确定情感类型
        sentiment = self._determine_sentiment_type(score)
        
        # 计算置信度 (基于关键词数量和文本长度)
        confidence = min(1.0, len(keywords) / 5 + 0.3)
        
        # 检查预警
        alert_level, alert_reason = self._check_alert(text, score)
        
        # 更新统计
        self.analysis_stats["total_analyzed"] += 1
        self.analysis_stats["sentiment_distribution"][sentiment.name] += 1
        if alert_level != AlertLevel.NONE:
            self.analysis_stats["alert_triggered"] += 1
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            score=round(score, 3),
            confidence=round(confidence, 3),
            aspects=aspects,
            keywords=keywords,
            alert_level=alert_level,
            alert_reason=alert_reason
        )
    
    def analyze_batch(self, texts: List[str]) -> ReviewBatch:
        """
        批量分析评价
        
        Args:
            texts: 评价文本列表
            
        Returns:
            批量分析结果
        """
        results = [self.analyze(text) for text in texts]
        
        # 统计分布
        distribution = defaultdict(int)
        negative_reviews = []
        aspect_scores = defaultdict(list)
        total_score = 0.0
        alert_count = 0
        
        for result in results:
            distribution[result.sentiment.value] += 1
            total_score += result.score
            
            if result.sentiment in [SentimentType.NEGATIVE, SentimentType.VERY_NEGATIVE]:
                negative_reviews.append(result)
            
            if result.alert_level != AlertLevel.NONE:
                alert_count += 1
            
            for aspect, score in result.aspects.items():
                aspect_scores[aspect].append(score)
        
        # 计算各方面平均分
        aspect_summary = {
            aspect: round(np.mean(scores), 3)
            for aspect, scores in aspect_scores.items()
        }
        
        return ReviewBatch(
            total_reviews=len(texts),
            sentiment_distribution=dict(distribution),
            average_score=round(total_score / len(texts), 3) if texts else 0,
            negative_reviews=negative_reviews,
            alert_count=alert_count,
            aspect_summary=aspect_summary
        )
    
    def add_keywords(
        self, 
        positive: Optional[List[str]] = None,
        negative: Optional[List[str]] = None
    ) -> None:
        """添加关键词 (热更新支持)"""
        if positive:
            self.positive_words.update(positive)
        if negative:
            self.negative_words.update(negative)
    
    def update_alert_rules(
        self, 
        level: AlertLevel,
        keywords: List[str],
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> None:
        """更新预警规则 (热更新支持)"""
        if level not in self.alert_rules:
            self.alert_rules[level] = {"keywords": [], "min_score": -1, "max_score": 1}
        
        self.alert_rules[level]["keywords"].extend(keywords)
        
        if min_score is not None:
            self.alert_rules[level]["min_score"] = min_score
        if max_score is not None:
            self.alert_rules[level]["max_score"] = max_score
    
    def get_alerts(
        self, 
        results: List[SentimentResult],
        min_level: AlertLevel = AlertLevel.LOW
    ) -> List[SentimentResult]:
        """
        获取预警列表
        
        Args:
            results: 分析结果列表
            min_level: 最低预警等级
            
        Returns:
            预警结果列表
        """
        level_order = list(AlertLevel)
        min_index = level_order.index(min_level)
        
        alerts = []
        for result in results:
            if result.alert_level != AlertLevel.NONE:
                result_index = level_order.index(result.alert_level)
                if result_index >= min_index:
                    alerts.append(result)
        
        return sorted(alerts, key=lambda x: level_order.index(x.alert_level), reverse=True)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = self.analysis_stats["total_analyzed"]
        alerts = self.analysis_stats["alert_triggered"]
        
        return {
            "total_analyzed": total,
            "alert_triggered": alerts,
            "alert_rate": round(alerts / total, 3) if total > 0 else 0,
            "sentiment_distribution": dict(self.analysis_stats["sentiment_distribution"])
        }
    
    def save(self, path: str) -> None:
        """保存模型"""
        data = {
            "positive_words": list(self.positive_words),
            "negative_words": list(self.negative_words),
            "intensifiers": self.intensifiers,
            "negations": list(self.negations),
            "aspect_keywords": self.aspect_keywords,
            "alert_rules": {
                k.value: v for k, v in self.alert_rules.items()
            },
            "statistics": self.analysis_stats,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str) -> 'SentimentAnalyzer':
        """加载模型 (热更新支持)"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.positive_words = set(data.get("positive_words", []))
        self.negative_words = set(data.get("negative_words", []))
        self.intensifiers = data.get("intensifiers", {})
        self.negations = set(data.get("negations", []))
        self.aspect_keywords = data.get("aspect_keywords", self.aspect_keywords)
        
        # 恢复预警规则
        alert_rules_data = data.get("alert_rules", {})
        for level_name, rules in alert_rules_data.items():
            try:
                level = AlertLevel(level_name)
                self.alert_rules[level] = rules
            except ValueError:
                pass
        
        self.analysis_stats = data.get("statistics", self.analysis_stats)
        
        return self
    
    def export_report(
        self, 
        batch_result: ReviewBatch, 
        output_path: str
    ) -> None:
        """导出分析报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_reviews": batch_result.total_reviews,
                "average_score": batch_result.average_score,
                "alert_count": batch_result.alert_count,
                "negative_rate": round(
                    len(batch_result.negative_reviews) / batch_result.total_reviews, 3
                ) if batch_result.total_reviews > 0 else 0
            },
            "sentiment_distribution": batch_result.sentiment_distribution,
            "aspect_summary": batch_result.aspect_summary,
            "alerts": [
                {
                    "text": r.text[:50] + "..." if len(r.text) > 50 else r.text,
                    "score": r.score,
                    "level": r.alert_level.value,
                    "reason": r.alert_reason
                }
                for r in batch_result.negative_reviews[:10]  # 前10条
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# 便捷函数
def quick_analyze(text: str) -> Dict:
    """快速分析接口"""
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(text)
    
    return {
        "sentiment": result.sentiment.value,
        "score": result.score,
        "confidence": result.confidence,
        "aspects": result.aspects,
        "alert_level": result.alert_level.value,
        "alert_reason": result.alert_reason
    }


def batch_analyze(texts: List[str]) -> Dict:
    """批量分析接口"""
    analyzer = SentimentAnalyzer()
    batch = analyzer.analyze_batch(texts)
    
    return {
        "total": batch.total_reviews,
        "average_score": batch.average_score,
        "distribution": batch.sentiment_distribution,
        "aspect_summary": batch.aspect_summary,
        "alert_count": batch.alert_count,
        "negative_samples": [
            {"text": r.text, "score": r.score}
            for r in batch.negative_reviews[:5]
        ]
    }


if __name__ == "__main__":
    # 示例用法
    analyzer = SentimentAnalyzer()
    
    test_reviews = [
        "产品质量非常好，物流也很快，非常满意！",
        "一般般吧，没有想象中那么好",
        "太差了，完全不值这个价，退货！",
        "客服态度很好，解决问题很及时",
        "物流太慢了，等了一个星期",
        "假货！大家不要买，被骗了！",
        "性价比很高，会回购的",
        "包装破损，产品也有划痕",
    ]
    
    print("=" * 70)
    print("情感分析测试")
    print("=" * 70)
    
    for review in test_reviews:
        result = analyzer.analyze(review)
        
        print(f"\n评价: {review}")
        print(f"  情感: {result.sentiment.value} (分数: {result.score})")
        print(f"  置信度: {result.confidence}")
        print(f"  关键词: {result.keywords}")
        print(f"  方面分析: {result.aspects}")
        if result.alert_level != AlertLevel.NONE:
            print(f"  ⚠️ 预警: {result.alert_level.value} - {result.alert_reason}")
    
    # 批量分析
    print("\n" + "=" * 70)
    print("批量分析结果")
    print("=" * 70)
    
    batch = analyzer.analyze_batch(test_reviews)
    print(f"\n总评价数: {batch.total_reviews}")
    print(f"平均情感分数: {batch.average_score}")
    print(f"情感分布: {batch.sentiment_distribution}")
    print(f"方面评分: {batch.aspect_summary}")
    print(f"预警数量: {batch.alert_count}")
    
    # 统计信息
    print("\n" + "=" * 70)
    print("统计信息")
    print("=" * 70)
    stats = analyzer.get_statistics()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
