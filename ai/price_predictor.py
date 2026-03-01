"""
价格预测模块 - Price Predictor
基于历史价格趋势分析，提供最优定价建议
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import pickle
from pathlib import Path

from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, mean_squared_error


class PriceTrend(Enum):
    """价格趋势枚举"""
    RISING = "上涨"
    FALLING = "下跌"
    STABLE = "稳定"
    VOLATILE = "波动"


@dataclass
class PricePoint:
    """价格数据点"""
    date: datetime
    price: float
    volume: int = 0  # 当日销量
    competitor_price: Optional[float] = None  # 竞品价格


@dataclass
class PricePrediction:
    """价格预测结果"""
    product_id: str
    current_price: float
    predicted_price: float
    confidence_interval: Tuple[float, float]
    trend: PriceTrend
    trend_strength: float  # 趋势强度 0-1
    optimal_price: float
    expected_profit: float
    recommendation: str
    forecast_days: int


@dataclass
class PricingStrategy:
    """定价策略"""
    product_id: str
    suggested_price: float
    min_price: float
    max_price: float
    strategy_type: str  # "penetration", "skimming", "competitive", "premium"
    rationale: str
    expected_margin: float
    price_elasticity: float


class PricePredictor:
    """
    价格预测器
    
    功能：
    1. 基于历史价格数据进行趋势预测
    2. 分析价格弹性
    3. 提供最优定价建议
    4. 支持多种定价策略
    """
    
    def __init__(self, forecast_days: int = 7):
        self.forecast_days = forecast_days
        self.models: Dict[str, any] = {}
        self.price_elasticity: Dict[str, float] = {}
        self.competitor_weights = 0.3  # 竞品价格权重
        
    def fit(
        self, 
        product_id: str, 
        price_history: List[PricePoint]
    ) -> 'PricePredictor':
        """
        训练价格预测模型
        
        Args:
            product_id: 产品ID
            price_history: 历史价格数据
            
        Returns:
            self
        """
        if len(price_history) < 7:
            raise ValueError("需要至少7天的历史价格数据")
        
        # 准备数据
        df = pd.DataFrame([
            {
                'day': i,
                'price': p.price,
                'volume': p.volume,
                'competitor_price': p.competitor_price or p.price,
                'day_of_week': p.date.weekday(),
                'month': p.date.month
            }
            for i, p in enumerate(price_history)
        ])
        
        # 特征工程
        df['price_ma7'] = df['price'].rolling(window=7, min_periods=1).mean()
        df['price_ma3'] = df['price'].rolling(window=3, min_periods=1).mean()
        df['price_change'] = df['price'].pct_change().fillna(0)
        df['volume_ma7'] = df['volume'].rolling(window=7, min_periods=1).mean()
        
        # 计算价格弹性
        self._calculate_elasticity(product_id, df)
        
        # 训练趋势预测模型
        X = df[['day', 'day_of_week', 'price_ma7', 'volume_ma7']].values
        y = df['price'].values
        
        # 使用多项式回归捕捉非线性趋势
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_poly = poly.fit_transform(X)
        
        model = Ridge(alpha=1.0)
        model.fit(X_poly, y)
        
        self.models[product_id] = {
            'model': model,
            'poly': poly,
            'last_price': price_history[-1].price,
            'price_std': df['price'].std(),
            'data': df
        }
        
        return self
    
    def _calculate_elasticity(self, product_id: str, df: pd.DataFrame) -> None:
        """计算价格弹性"""
        if len(df) < 2 or df['price'].std() == 0:
            self.price_elasticity[product_id] = -1.0  # 默认值
            return
        
        # 价格弹性 = (销量变化%) / (价格变化%)
        price_changes = df['price_change'].replace(0, np.nan).dropna()
        if len(price_changes) > 0:
            volume_changes = df['volume'].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
            if len(volume_changes) == len(price_changes):
                elasticities = volume_changes / price_changes
                elasticities = elasticities.replace([np.inf, -np.inf], np.nan).dropna()
                if len(elasticities) > 0:
                    self.price_elasticity[product_id] = np.median(elasticities)
                    return
        
        self.price_elasticity[product_id] = -1.0
    
    def predict(self, product_id: str) -> PricePrediction:
        """
        预测未来价格
        
        Args:
            product_id: 产品ID
            
        Returns:
            价格预测结果
        """
        if product_id not in self.models:
            raise ValueError(f"产品 {product_id} 未训练，请先调用 fit()")
        
        model_data = self.models[product_id]
        model = model_data['model']
        poly = model_data['poly']
        df = model_data['data']
        
        # 预测未来N天
        last_day = len(df)
        future_days = np.arange(last_day, last_day + self.forecast_days)
        
        predictions = []
        for day in future_days:
            features = np.array([[
                day,
                day % 7,  # day_of_week
                df['price_ma7'].iloc[-1],  # 使用最新的MA
                df['volume_ma7'].iloc[-1]
            ]])
            features_poly = poly.transform(features)
            pred = model.predict(features_poly)[0]
            predictions.append(pred)
        
        predicted_price = np.mean(predictions)
        price_std = model_data['price_std']
        
        # 计算置信区间
        confidence_interval = (
            predicted_price - 1.96 * price_std,
            predicted_price + 1.96 * price_std
        )
        
        # 判断趋势
        current_price = model_data['last_price']
        price_change = (predicted_price - current_price) / current_price
        
        if abs(price_change) < 0.02:
            trend = PriceTrend.STABLE
            trend_strength = 0.0
        elif price_change > 0:
            trend = PriceTrend.RISING
            trend_strength = min(abs(price_change) * 5, 1.0)
        else:
            trend = PriceTrend.FALLING
            trend_strength = min(abs(price_change) * 5, 1.0)
        
        # 计算最优价格
        optimal_price = self._calculate_optimal_price(product_id, current_price)
        
        # 计算预期利润
        elasticity = self.price_elasticity.get(product_id, -1.0)
        expected_profit = self._estimate_profit(product_id, optimal_price, elasticity)
        
        # 生成建议
        recommendation = self._generate_recommendation(
            current_price, optimal_price, trend, trend_strength
        )
        
        return PricePrediction(
            product_id=product_id,
            current_price=round(current_price, 2),
            predicted_price=round(predicted_price, 2),
            confidence_interval=(round(confidence_interval[0], 2), round(confidence_interval[1], 2)),
            trend=trend,
            trend_strength=round(trend_strength, 3),
            optimal_price=round(optimal_price, 2),
            expected_profit=round(expected_profit, 2),
            recommendation=recommendation,
            forecast_days=self.forecast_days
        )
    
    def _calculate_optimal_price(self, product_id: str, current_price: float) -> float:
        """计算最优价格"""
        elasticity = abs(self.price_elasticity.get(product_id, 1.0))
        
        # 简化的最优价格公式
        # 假设成本为当前价格的60%
        cost = current_price * 0.6
        
        if elasticity > 1:
            # 弹性大，适当降价
            optimal = cost * (1 + 1 / elasticity)
        else:
            # 弹性小，可适当提价
            optimal = current_price * 1.05
        
        # 限制在合理范围内 (成本价的1.2倍到3倍)
        optimal = max(optimal, cost * 1.2)
        optimal = min(optimal, cost * 3)
        
        return optimal
    
    def _estimate_profit(
        self, 
        product_id: str, 
        price: float, 
        elasticity: float
    ) -> float:
        """估算利润"""
        model_data = self.models[product_id]
        df = model_data['data']
        
        avg_volume = df['volume_ma7'].iloc[-1]
        cost = price * 0.6  # 假设成本60%
        
        # 根据弹性调整销量预期
        price_change = (price - model_data['last_price']) / model_data['last_price']
        volume_change = elasticity * price_change
        adjusted_volume = avg_volume * (1 + volume_change)
        
        return (price - cost) * adjusted_volume
    
    def _generate_recommendation(
        self,
        current_price: float,
        optimal_price: float,
        trend: PriceTrend,
        trend_strength: float
    ) -> str:
        """生成定价建议"""
        price_diff = (optimal_price - current_price) / current_price
        
        if trend == PriceTrend.RISING and trend_strength > 0.5:
            return f"市场价格上涨趋势明显，建议上调价格至 {optimal_price:.2f} 元"
        elif trend == PriceTrend.FALLING and trend_strength > 0.5:
            return f"市场价格下跌趋势，建议降价至 {optimal_price:.2f} 元以保持竞争力"
        elif abs(price_diff) > 0.05:
            direction = "上调" if price_diff > 0 else "下调"
            return f"建议{direction}价格至 {optimal_price:.2f} 元以优化利润"
        else:
            return "当前价格合理，建议维持"
    
    def get_pricing_strategy(
        self, 
        product_id: str,
        strategy_type: Optional[str] = None
    ) -> PricingStrategy:
        """
        获取定价策略
        
        Args:
            product_id: 产品ID
            strategy_type: 策略类型 (penetration/skimming/competitive/premium)
            
        Returns:
            定价策略
        """
        if product_id not in self.models:
            raise ValueError(f"产品 {product_id} 未训练")
        
        model_data = self.models[product_id]
        current_price = model_data['last_price']
        elasticity = abs(self.price_elasticity.get(product_id, 1.0))
        
        # 自动选择策略
        if strategy_type is None:
            if elasticity > 1.5:
                strategy_type = "penetration"  # 渗透定价
            elif elasticity < 0.8:
                strategy_type = "skimming"  # 撇脂定价
            else:
                strategy_type = "competitive"  # 竞争定价
        
        # 计算策略价格
        if strategy_type == "penetration":
            suggested = current_price * 0.9
            rationale = "价格弹性高，采用渗透定价快速占领市场"
        elif strategy_type == "skimming":
            suggested = current_price * 1.15
            rationale = "价格弹性低，可采用撇脂定价获取高利润"
        elif strategy_type == "premium":
            suggested = current_price * 1.25
            rationale = "高端定位，采用溢价策略"
        else:  # competitive
            suggested = current_price
            rationale = "采用竞争性定价保持市场份额"
        
        cost = current_price * 0.6
        
        return PricingStrategy(
            product_id=product_id,
            suggested_price=round(suggested, 2),
            min_price=round(cost * 1.1, 2),
            max_price=round(cost * 3, 2),
            strategy_type=strategy_type,
            rationale=rationale,
            expected_margin=round((suggested - cost) / suggested, 3),
            price_elasticity=round(elasticity, 3)
        )
    
    def batch_predict(
        self, 
        price_data: Dict[str, List[PricePoint]]
    ) -> List[PricePrediction]:
        """
        批量预测
        
        Args:
            price_data: 产品ID到价格历史的映射
            
        Returns:
            预测结果列表
        """
        results = []
        for product_id, history in price_data.items():
            try:
                self.fit(product_id, history)
                prediction = self.predict(product_id)
                results.append(prediction)
            except Exception as e:
                print(f"预测 {product_id} 失败: {e}")
        
        return results
    
    def save(self, path: str) -> None:
        """保存模型"""
        data = {
            'models': self.models,
            'price_elasticity': self.price_elasticity,
            'forecast_days': self.forecast_days,
            'saved_at': datetime.now().isoformat()
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, path: str) -> 'PricePredictor':
        """加载模型 (热更新支持)"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.models = data['models']
        self.price_elasticity = data['price_elasticity']
        self.forecast_days = data['forecast_days']
        return self
    
    def get_model_info(self, product_id: str) -> Dict:
        """获取模型信息"""
        if product_id not in self.models:
            return {"error": "模型未找到"}
        
        return {
            "product_id": product_id,
            "elasticity": round(self.price_elasticity.get(product_id, 0), 3),
            "data_points": len(self.models[product_id]['data']),
            "last_price": self.models[product_id]['last_price']
        }


# 便捷函数
def quick_predict(
    price_history: List[Dict],
    forecast_days: int = 7
) -> Dict:
    """
    快速预测接口
    
    Args:
        price_history: 价格历史数据列表，每项包含:
            - date: 日期字符串 (YYYY-MM-DD)
            - price: 价格
            - volume: 销量 (可选)
            - competitor_price: 竞品价格 (可选)
    """
    points = []
    for item in price_history:
        points.append(PricePoint(
            date=datetime.strptime(item['date'], '%Y-%m-%d'),
            price=item['price'],
            volume=item.get('volume', 0),
            competitor_price=item.get('competitor_price')
        ))
    
    predictor = PricePredictor(forecast_days=forecast_days)
    predictor.fit("PRODUCT_001", points)
    result = predictor.predict("PRODUCT_001")
    
    return {
        "current_price": result.current_price,
        "predicted_price": result.predicted_price,
        "confidence_interval": result.confidence_interval,
        "trend": result.trend.value,
        "optimal_price": result.optimal_price,
        "recommendation": result.recommendation
    }


if __name__ == "__main__":
    # 示例用法
    from datetime import datetime, timedelta
    
    # 生成示例价格历史
    base_date = datetime.now() - timedelta(days=30)
    price_history = []
    
    np.random.seed(42)
    base_price = 100
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        # 模拟价格波动
        price = base_price + np.sin(i / 5) * 10 + np.random.normal(0, 3)
        volume = int(100 + np.random.normal(0, 20))
        competitor = price + np.random.normal(0, 5)
        
        price_history.append(PricePoint(
            date=date,
            price=round(price, 2),
            volume=max(0, volume),
            competitor_price=round(competitor, 2)
        ))
    
    # 训练并预测
    predictor = PricePredictor(forecast_days=7)
    predictor.fit("DEMO_PRODUCT", price_history)
    
    result = predictor.predict("DEMO_PRODUCT")
    
    print("=" * 60)
    print("价格预测结果")
    print("=" * 60)
    print(f"产品ID: {result.product_id}")
    print(f"当前价格: ¥{result.current_price}")
    print(f"预测价格: ¥{result.predicted_price}")
    print(f"置信区间: ¥{result.confidence_interval[0]} - ¥{result.confidence_interval[1]}")
    print(f"价格趋势: {result.trend.value} (强度: {result.trend_strength})")
    print(f"最优定价: ¥{result.optimal_price}")
    print(f"预期利润: ¥{result.expected_profit}")
    print(f"建议: {result.recommendation}")
    
    # 获取定价策略
    strategy = predictor.get_pricing_strategy("DEMO_PRODUCT")
    print("\n" + "=" * 60)
    print("定价策略建议")
    print("=" * 60)
    print(f"策略类型: {strategy.strategy_type}")
    print(f"建议价格: ¥{strategy.suggested_price}")
    print(f"价格区间: ¥{strategy.min_price} - ¥{strategy.max_price}")
    print(f"预期利润率: {strategy.expected_margin * 100:.1f}%")
    print(f"价格弹性: {strategy.price_elasticity}")
    print(f"策略说明: {strategy.rationale}")
