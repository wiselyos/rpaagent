#!/usr/bin/env python3
"""
喵呜商城 API 集成模块
基于官方 API 文档实现
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from platforms.mall_api_client import MallAPIClient, MallAPIConfig

class MallIntegration:
    """喵呜商城系统集成"""
    
    def __init__(self, app_id: str, app_secret: str, uniacid: str = "25"):
        config = MallAPIConfig(
            app_id=app_id,
            app_secret=app_secret,
            uniacid=uniacid
        )
        self.client = MallAPIClient(config)
    
    async def sync_orders(self, days: int = 1) -> List[Dict]:
        """
        同步订单数据
        
        Args:
            days: 同步最近几天的订单
        """
        create_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")
        
        print(f"同步订单: 从 {create_time} 开始")
        
        result = await self.client.get_order_list(create_time=create_time)
        
        if result.get("result") != 1:
            print(f"获取订单失败: {result.get('msg')}")
            return []
        
        orders = result.get("data", [])
        print(f"同步完成，共 {len(orders)} 个订单")
        return orders
    
    async def process_pending_orders(self) -> Dict:
        """处理待发货订单"""
        # 1. 获取待发货订单
        orders = await self.sync_orders(days=1)
        
        processed = 0
        shipped = 0
        errors = []
        
        for order in orders:
            try:
                # 检查订单状态
                status = order.get("status")
                if status != 1:  # 1 = 待发货
                    continue
                
                outside_sn = order.get("outside_sn")
                print(f"处理订单: {outside_sn}")
                
                # 风控检查
                if self._risk_check(order):
                    print(f"  订单 {outside_sn} 风控通过")
                    
                    # 生成快递信息
                    express_code = self._select_carrier(order)
                    express_sn = self._generate_tracking_no()
                    
                    # 调用发货接口
                    result = await self.client.ship_order(
                        outside_sn=outside_sn,
                        express_code=express_code,
                        express_sn=express_sn
                    )
                    
                    if result.get("result") == 1:
                        print(f"  发货成功: {express_sn}")
                        shipped += 1
                    else:
                        print(f"  发货失败: {result.get('msg')}")
                        errors.append({
                            "outside_sn": outside_sn,
                            "error": result.get("msg")
                        })
                else:
                    print(f"  订单 {outside_sn} 风控拦截")
                
                processed += 1
                
            except Exception as e:
                print(f"处理订单异常: {e}")
                errors.append({
                    "outside_sn": order.get("outside_sn"),
                    "error": str(e)
                })
        
        return {
            "processed": processed,
            "shipped": shipped,
            "errors": errors
        }
    
    async def auto_create_and_pay_order(self, uid: int, goods: List[Dict]) -> Dict:
        """
        自动创建并支付订单
        
        Args:
            uid: 会员ID
            goods: 商品列表
        """
        # 1. 计算订单
        calculate_result = await self.client.calculate_order(uid=uid, goods=goods)
        if calculate_result.get("result") != 1:
            return {
                "success": False,
                "stage": "calculate",
                "error": calculate_result.get("msg")
            }
        
        print(f"订单计算成功: {calculate_result.get('data', {}).get('total_price')}")
        
        # 2. 创建订单
        outside_sn = self.client.generate_outside_sn()
        create_result = await self.client.create_order(
            outside_sn=outside_sn,
            uid=uid,
            goods=goods
        )
        
        if create_result.get("result") != 1:
            return {
                "success": False,
                "stage": "create",
                "error": create_result.get("msg")
            }
        
        print(f"订单创建成功: {outside_sn}")
        
        # 3. 支付订单
        pay_result = await self.client.pay_order(outside_sn=outside_sn)
        if pay_result.get("result") != 1:
            return {
                "success": False,
                "stage": "pay",
                "error": pay_result.get("msg"),
                "outside_sn": outside_sn
            }
        
        print(f"订单支付成功: {outside_sn}")
        
        return {
            "success": True,
            "outside_sn": outside_sn,
            "trade_sn": create_result.get("data", {}).get("trade_sn"),
            "orders": create_result.get("data", {}).get("orders", []),
            "pay_link": create_result.get("data", {}).get("pay_link")
        }
    
    def _risk_check(self, order: Dict) -> bool:
        """订单风控检查"""
        # 检查金额
        price = float(order.get("price", 0))
        if price > 10000:  # 大额订单
            return False
        
        return True
    
    def _select_carrier(self, order: Dict) -> str:
        """选择快递公司"""
        # 默认圆通
        return "YTO"
    
    def _generate_tracking_no(self) -> str:
        """生成快递单号"""
        import random
        timestamp = datetime.now().strftime("%Y%m%d")
        random_num = random.randint(100000, 999999)
        return f"YT{timestamp}{random_num}"
    
    async def get_order_statistics(self, days: int = 7) -> Dict:
        """获取订单统计"""
        start_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")
        
        result = await self.client.get_order_list(create_time=start_time)
        
        if result.get("result") != 1:
            return {}
        
        orders = result.get("data", [])
        
        # 统计各状态订单数
        status_count = {0: 0, 1: 0, 2: 0, 3: 0, -1: 0}
        total_amount = 0.0
        
        for order in orders:
            status = order.get("status", 0)
            status_count[status] = status_count.get(status, 0) + 1
            total_amount += float(order.get("price", 0))
        
        return {
            "total_orders": len(orders),
            "total_amount": round(total_amount, 2),
            "pending_payment": status_count[0],
            "pending_shipment": status_count[1],
            "pending_receipt": status_count[2],
            "completed": status_count[3],
            "closed": status_count[-1],
            "period_days": days
        }

# 使用示例
if __name__ == "__main__":
    async def main():
        # 初始化集成模块
        integration = MallIntegration(
            app_id="2026021502557128",
            app_secret="E59CA750B7BF3950171C314D83F6995B",
            uniacid="25"
        )
        
        # 1. 同步订单
        orders = await integration.sync_orders(days=1)
        print(f"获取到 {len(orders)} 个订单")
        
        # 2. 处理待发货订单
        result = await integration.process_pending_orders()
        print(f"处理结果: {result}")
        
        # 3. 获取订单统计
        stats = await integration.get_order_statistics(days=7)
        print(f"订单统计: {stats}")
    
    asyncio.run(main())
