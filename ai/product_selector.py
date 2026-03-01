"""
智能选品模块 - Product Selector
基于销量、竞争度、利润率进行产品评分和选品建议
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import pickle
from pathlib import Path


@dataclass
class ProductMetrics:
    """产品指标数据类"""
    product_id: str
    name: str
    sales_volume: float  # 销量
    competition_score: float  # 竞争度 (0-1, 越低越好)
    profit_margin: float  # 利润率 (0-1)
    price: float
    category: str
    rating: float = 0.0  # 评分
    review_count: int = 0  # 评论数
    trend_score: float = 0.0  # 趋势分


@dataclass
class SelectionResult:
    """选品结果"""
    product_id: str
    name: str
    category: str
    overall_score: float
    sales_score: float
    competition_score: float
    profit_score: float
    trend_score: float
    recommendation: str
    confidence: float


class ProductSelector:
    """
    智能选品器
    
    使用多维度评分模型评估产品潜力：
    - 销量评分 (30%): 基于历史销量数据
    - 竞争评分 (25%): 基于市场竞争程度
    - 利润评分 (25%): 基于利润率
    - 趋势评分 (20%): 基于增长趋势
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.weights = {
            'sales': 0.30,
            'competition': 0.25,
            'profit': 0.25,
            'trend': 0.20
        }
        self.thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        self.category_stats: Dict[str, Dict] = {}
        self.is_fitted = False
        
    def fit(self, products: List[ProductMetrics]) -> 'ProductSelector':
        """
        基于历史数据计算类别统计信息
        
        Args:
            products: 产品指标列表
            
        Returns:
            self
        """
        df = pd.DataFrame([
            {
                'category': p.category,
                'sales_volume': p.sales_volume,
                'competition_score': p.competition_score,
                'profit_margin': p.profit_margin,
                'trend_score': p.trend_score
            }
            for p in products
        ])
        
        # 按类别计算统计信息
        for category in df['category'].unique():
            cat_data = df[df['category'] == category]
            self.category_stats[category] = {
                'sales_mean': cat_data['sales_volume'].mean(),
                'sales_std': cat_data['sales_volume'].std() or 1.0,
                'profit_mean': cat_data['profit_margin'].mean(),
                'profit_std': cat_data['profit_margin'].std() or 0.1,
                'count': len(cat_data)
            }
        
        self.is_fitted = True
        return self
    
    def _normalize_sales(self, sales: float, category: str) -> float:
        """标准化销量分数 (0-1)"""
        if category in self.category_stats:
            stats = self.category_stats[category]
            z_score = (sales - stats['sales_mean']) / stats['sales_std']
            # 转换为 0-1 分数
            return min(max(0.5 + z_score * 0.3, 0), 1)
        return min(sales / 1000, 1.0)  # 默认归一化
    
    def _normalize_competition(self, competition: float) -> float:
        """
        标准化竞争分数 (0-1)
        竞争度越低，分数越高
        """
        return 1 - min(max(competition, 0), 1)
    
    def _normalize_profit(self, profit: float, category: str) -> float:
        """标准化利润分数 (0-1)"""
        if category in self.category_stats:
            stats = self.category_stats[category]
            if stats['profit_std'] > 0:
                z_score = (profit - stats['profit_mean']) / stats['profit_std']
                return min(max(0.5 + z_score * 0.3, 0), 1)
        return min(max(profit, 0), 1)
    
    def _calculate_trend_score(self, trend: float) -> float:
        """计算趋势分数 (0-1)"""
        return min(max((trend + 1) / 2, 0), 1)  # 假设趋势范围 -1 到 1
    
    def evaluate(self, product: ProductMetrics) -> SelectionResult:
        """
        评估单个产品
        
        Args:
            product: 产品指标
            
        Returns:
            选品结果
        """
        # 计算各维度分数
        sales_score = self._normalize_sales(product.sales_volume, product.category)
        competition_score = self._normalize_competition(product.competition_score)
        profit_score = self._normalize_profit(product.profit_margin, product.category)
        trend_score = self._calculate_trend_score(product.trend_score)
        
        # 加权计算总分
        overall_score = (
            sales_score * self.weights['sales'] +
            competition_score * self.weights['competition'] +
            profit_score * self.weights['profit'] +
            trend_score * self.weights['trend']
        )
        
        # 确定推荐等级
        if overall_score >= self.thresholds['high']:
            recommendation = "强烈推荐"
        elif overall_score >= self.thresholds['medium']:
            recommendation = "推荐"
        elif overall_score >= self.thresholds['low']:
            recommendation = "谨慎考虑"
        else:
            recommendation = "不推荐"
        
        # 计算置信度 (基于数据完整度)
        confidence = min(1.0, (product.review_count / 100) + 0.5)
        
        return SelectionResult(
            product_id=product.product_id,
            name=product.name,
            category=product.category,
            overall_score=round(overall_score, 3),
            sales_score=round(sales_score, 3),
            competition_score=round(competition_score, 3),
            profit_score=round(profit_score, 3),
            trend_score=round(trend_score, 3),
            recommendation=recommendation,
            confidence=round(confidence, 3)
        )
    
    def select_products(
        self, 
        products: List[ProductMetrics],
        top_k: int = 10,
        min_score: float = 0.5
    ) -> List[SelectionResult]:
        """
        批量选品
        
        Args:
            products: 产品列表
            top_k: 返回前K个产品
            min_score: 最低分数阈值
            
        Returns:
            排序后的选品结果
        """
        if not self.is_fitted:
            self.fit(products)
        
        results = []
        for product in products:
            result = self.evaluate(product)
            if result.overall_score >= min_score:
                results.append(result)
        
        # 按总分排序
        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results[:top_k]
    
    def get_category_insights(self, category: str) -> Dict:
        """获取类别洞察"""
        if category not in self.category_stats:
            return {"error": f"类别 {category} 无数据"}
        
        stats = self.category_stats[category]
        return {
            "category": category,
            "sample_count": stats['count'],
            "avg_sales": round(stats['sales_mean'], 2),
            "avg_profit_margin": round(stats['profit_mean'] * 100, 2),
            "sales_volatility": "高" if stats['sales_std'] > stats['sales_mean'] else "低"
        }
    
    def update_weights(self, weights: Dict[str, float]) -> None:
        """热更新权重"""
        if abs(sum(weights.values()) - 1.0) > 0.01:
            raise ValueError("权重总和必须等于1")
        self.weights = weights
    
    def save(self, path: str) -> None:
        """保存模型"""
        data = {
            'weights': self.weights,
            'thresholds': self.thresholds,
            'category_stats': self.category_stats,
            'is_fitted': self.is_fitted,
            'saved_at': datetime.now().isoformat()
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, path: str) -> 'ProductSelector':
        """加载模型 (热更新支持)"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.weights = data['weights']
        self.thresholds = data['thresholds']
        self.category_stats = data['category_stats']
        self.is_fitted = data['is_fitted']
        return self
    
    def export_report(self, results: List[SelectionResult], output_path: str) -> None:
        """导出选品报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_products": len(results),
            "summary": {
                "highly_recommended": len([r for r in results if r.recommendation == "强烈推荐"]),
                "recommended": len([r for r in results if r.recommendation == "推荐"]),
                "caution": len([r for r in results if r.recommendation == "谨慎考虑"]),
                "not_recommended": len([r for r in results if r.recommendation == "不推荐"])
            },
            "products": [
                {
                    "id": r.product_id,
                    "name": r.name,
                    "category": r.category,
                    "score": r.overall_score,
                    "recommendation": r.recommendation,
                    "confidence": r.confidence
                }
                for r in results
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# 便捷函数
def create_selector(model_path: Optional[str] = None) -> ProductSelector:
    """创建选品器实例"""
    selector = ProductSelector(model_path)
    if model_path and Path(model_path).exists():
        selector.load(model_path)
    return selector


def quick_select(
    products_data: List[Dict],
    top_k: int = 10
) -> List[SelectionResult]:
    """
    快速选品接口
    
    Args:
        products_data: 产品数据列表，每项包含:
            - product_id: 产品ID
            - name: 产品名称
            - sales_volume: 销量
            - competition_score: 竞争度 (0-1)
            - profit_margin: 利润率 (0-1)
            - price: 价格
            - category: 类别
            - trend_score: 趋势分 (可选)
    """
    products = []
    for data in products_data:
        products.append(ProductMetrics(
            product_id=data['product_id'],
            name=data['name'],
            sales_volume=data['sales_volume'],
            competition_score=data.get('competition_score', 0.5),
            profit_margin=data['profit_margin'],
            price=data['price'],
            category=data['category'],
            rating=data.get('rating', 0),
            review_count=data.get('review_count', 0),
            trend_score=data.get('trend_score', 0)
        ))
    
    selector = ProductSelector()
    return selector.select_products(products, top_k=top_k)


if __name__ == "__main__":
    # 示例用法
    sample_products = [
        ProductMetrics(
            product_id="P001",
            name="无线蓝牙耳机",
            sales_volume=5000,
            competition_score=0.7,
            profit_margin=0.35,
            price=299,
            category="电子产品",
            rating=4.5,
            review_count=1200,
            trend_score=0.6
        ),
        ProductMetrics(
            product_id="P002",
            name="智能手环",
            sales_volume=8000,
            competition_score=0.8,
            profit_margin=0.25,
            price=199,
            category="电子产品",
            rating=4.2,
            review_count=800,
            trend_score=0.3
        ),
        ProductMetrics(
            product_id="P003",
            name="便携充电宝",
            sales_volume=12000,
            competition_score=0.5,
            profit_margin=0.40,
            price=89,
            category="电子产品",
            rating=4.7,
            review_count=2500,
            trend_score=0.5
        ),
    ]
    
    selector = ProductSelector()
    results = selector.select_products(sample_products, top_k=5)
    
    print("=" * 60)
    print("智能选品结果")
    print("=" * 60)
    for r in results:
        print(f"\n产品: {r.name} ({r.product_id})")
        print(f"  综合评分: {r.overall_score}")
        print(f"  销量评分: {r.sales_score} | 竞争评分: {r.competition_score}")
        print(f"  利润评分: {r.profit_score} | 趋势评分: {r.trend_score}")
        print(f"  推荐等级: {r.recommendation} (置信度: {r.confidence})")
