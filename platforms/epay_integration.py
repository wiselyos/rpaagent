#!/usr/bin/env python3
"""
电商系统 API 集成模块
将 epay API 集成到订单自动化系统
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from platforms.epay_client import EPayAPIClient, APIConfig

class EPayIntegration:
    """电商系统集成"""
    
    def __init__(self, app_id: str, app_secret: str):
        config = APIConfig(
            app_id=app_id,
            app_secret=app_secret
        )
        self.client = EPayAPIClient(config)
    
    async def sync_orders(self, days: int = 1) -> List[Dict]:
        """
        同步订单数据
        
        Args:
            days: 同步最近几天的订单
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 格式化时间
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"同步订单: {start_str} ~ {end_str}")
        
        all_orders = []
        page = 1
        
        while True:
            result = await self.client.get_orders(
                start_time=start_str,
                end_time=end_str,
                page=page,
                page_size=50
            )
            
            if result.get("result") != 0:
                print(f"获取订单失败: {result.get('msg')}")
                break
            
            orders = result.get("data", {}).get("list", [])
            if not orders:
                break
            
            all_orders.extend(orders)
            
            # 检查是否还有下一页
            total = result.get("data", {}).get("total", 0)
            if page * 50 >= total:
                break
            
            page += 1
        
        print(f"同步完成，共 {len(all_orders)} 个订单")
        return all_orders
    
    async def process_pending_orders(self) -> Dict:
        """处理待处理订单"""
        # 1. 获取待发货订单
        orders = await self.sync_orders(days=1)
        
        processed = 0
        shipped = 0
        errors = []
        
        for order in orders:
            try:
                order_no = order.get("order_no")
                status = order.get("status")
                
                # 只处理已付款未发货的订单
                if status != "paid":
                    continue
                
                print(f"处理订单: {order_no}")
                
                # 2. 风控检查（简化版）
                if self._risk_check(order):
                    print(f"  订单 {order_no} 风控通过")
                    
                    # 3. 生成物流单号
                    tracking_no = self._generate_tracking_no()
                    carrier = self._select_carrier(order)
                    
                    # 4. 调用 API 发货
                    result = await self.client.ship_order(
                        order_no=order_no,
                        tracking_no=tracking_no,
                        carrier=carrier
                    )
                    
                    if result.get("result") == 0:
                        print(f"  发货成功: {tracking_no}")
                        shipped += 1
                    else:
                        print(f"  发货失败: {result.get('msg')}")
                        errors.append({
                            "order_no": order_no,
                            "error": result.get("msg")
                        })
                else:
                    print(f"  订单 {order_no} 风控拦截")
                
                processed += 1
                
            except Exception as e:
                print(f"处理订单异常: {e}")
                errors.append({
                    "order_no": order.get("order_no"),
                    "error": str(e)
                })
        
        return {
            "processed": processed,
            "shipped": shipped,
            "errors": errors
        }
    
    def _risk_check(self, order: Dict) -> bool:
        """订单风控检查"""
        # 检查金额
        amount = float(order.get("total_amount", 0))
        if amount > 10000:  # 大额订单
            return False
        
        # 检查收货地址
        address = order.get("receiver_address", "")
        suspicious_keywords = ["测试", "test", "某某"]
        if any(kw in address for kw in suspicious_keywords):
            return False
        
        return True
    
    def _generate_tracking_no(self) -> str:
        """生成物流单号"""
        import random
        prefix = "SF"
        timestamp = datetime.now().strftime("%Y%m%d")
        random_num = random.randint(100000, 999999)
        return f"{prefix}{timestamp}{random_num}"
    
    def _select_carrier(self, order: Dict) -> str:
        """选择快递公司"""
        address = order.get("receiver_address", "")
        
        # 偏远地区用 EMS
        if any(region in address for region in ["新疆", "西藏", "青海"]):
            return "ems"
        
        # 高价值用顺丰
        amount = float(order.get("total_amount", 0))
        if amount > 500:
            return "sf"
        
        # 默认圆通
        return "yto"
    
    async def sync_inventory(self) -> List[Dict]:
        """同步库存数据"""
        print("同步库存...")
        
        all_products = []
        page = 1
        
        while True:
            result = await self.client.get_products(page=page, page_size=50)
            
            if result.get("result") != 0:
                print(f"获取商品失败: {result.get('msg')}")
                break
            
            products = result.get("data", {}).get("list", [])
            if not products:
                break
            
            all_products.extend(products)
            
            total = result.get("data", {}).get("total", 0)
            if page * 50 >= total:
                break
            
            page += 1
        
        print(f"同步完成，共 {len(all_products)} 个商品")
        return all_products
    
    async def check_low_stock(self, threshold: int = 10) -> List[Dict]:
        """检查低库存商品"""
        products = await self.sync_inventory()
        
        low_stock = []
        for product in products:
            stock = product.get("stock", 0)
            if stock <= threshold:
                low_stock.append({
                    "sku": product.get("sku"),
                    "name": product.get("name"),
                    "stock": stock,
                    "threshold": threshold
                })
        
        print(f"发现 {len(low_stock)} 个低库存商品")
        return low_stock
    
    async def generate_daily_report(self) -> Dict:
        """生成日报"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 获取日报数据
        result = await self.client.get_daily_report(today)
        
        if result.get("result") != 0:
            print(f"获取日报失败: {result.get('msg')}")
            return {}
        
        data = result.get("data", {})
        
        report = {
            "date": today,
            "orders": {
                "total": data.get("order_count", 0),
                "amount": data.get("order_amount", 0),
                "paid": data.get("paid_count", 0),
                "shipped": data.get("shipped_count", 0)
            },
            "products": {
                "total": data.get("product_count", 0),
                "low_stock": len(await self.check_low_stock())
            },
            "refunds": {
                "count": data.get("refund_count", 0),
                "amount": data.get("refund_amount", 0)
            }
        }
        
        return report

# 使用示例
if __name__ == "__main__":
    async def main():
        # 初始化集成模块
        integration = EPayIntegration(
            app_id="2026021502557128",
            app_secret="E59CA750B7BF3950171C314D83F6995B"
        )
        
        # 同步订单
        orders = await integration.sync_orders(days=1)
        print(f"获取到 {len(orders)} 个订单")
        
        # 处理待发货订单
        result = await integration.process_pending_orders()
        print(f"处理结果: {result}")
        
        # 检查低库存
        low_stock = await integration.check_low_stock(threshold=10)
        print(f"低库存商品: {low_stock}")
        
        # 生成日报
        report = await integration.generate_daily_report()
        print(f"日报: {report}")
    
    asyncio.run(main())
