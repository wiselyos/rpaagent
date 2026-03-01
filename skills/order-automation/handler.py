#!/usr/bin/env python3
"""
订单自动化 Skill - 核心处理逻辑
"""
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class OrderAutomationSkill:
    """订单自动化处理 Skill"""
    
    def __init__(self, context):
        self.context = context
        self.db = context.get_database("ecommerce")
        
        # 风控规则
        self.risk_rules = {
            "blacklist": [],  # 黑名单用户
            "suspicious_keywords": ["测试", "test", "刷单"],
            "max_amount": 10000,  # 单笔最大金额
            "max_daily_orders": 10  # 单日最大订单数
        }
    
    async def process_pending_orders(self) -> Dict:
        """处理待处理订单 - 定时任务入口"""
        print(f"[{datetime.now()}] 开始处理待处理订单...")
        
        # 1. 获取待处理订单
        orders = await self._get_pending_orders(limit=100)
        print(f"  找到 {len(orders)} 个待处理订单")
        
        results = {
            "processed": 0,
            "approved": 0,
            "rejected": 0,
            "escalated": 0,
            "errors": []
        }
        
        for order in orders:
            try:
                result = await self.process_order(order["order_id"])
                
                if result["status"] == "approved":
                    results["approved"] += 1
                elif result["status"] == "rejected":
                    results["rejected"] += 1
                elif result["status"] == "escalated":
                    results["escalated"] += 1
                
                results["processed"] += 1
                
            except Exception as e:
                print(f"  处理订单 {order['order_id']} 失败: {e}")
                results["errors"].append({
                    "order_id": order["order_id"],
                    "error": str(e)
                })
        
        print(f"  处理完成: {results}")
        return results
    
    async def process_order(self, order_id: str) -> Dict:
        """处理单个订单"""
        print(f"  处理订单: {order_id}")
        
        # 1. 获取订单详情
        order = await self._get_order_detail(order_id)
        if not order:
            return {"status": "error", "message": "订单不存在"}
        
        # 2. 风控检查
        risk_score = await self._risk_assessment(order)
        print(f"    风控评分: {risk_score}")
        
        if risk_score > self.risk_rules["max_amount"]:
            await self._flag_suspicious_order(order, "高风险评分")
            return {"status": "escalated", "reason": "高风险订单"}
        
        # 3. 库存检查
        stock_ok = await self._check_inventory(order["items"])
        if not stock_ok:
            await self._notify_low_stock(order["items"])
            return {"status": "pending", "reason": "库存不足"}
        
        # 4. 自动审核通过
        if risk_score < 0.5 and self.context.config.get("auto_fulfill", True):
            # 5. 生成快递单
            shipping_result = await self._generate_shipping_label(order)
            
            if shipping_result["success"]:
                # 6. 通知仓库
                await self._notify_warehouse(order, shipping_result)
                
                # 7. 更新订单状态
                await self._update_order_status(order_id, "shipped", {
                    "tracking_no": shipping_result["tracking_no"],
                    "carrier": shipping_result["carrier"],
                    "shipped_at": datetime.now().isoformat()
                })
                
                # 8. 通知客户
                await self._notify_customer(order, shipping_result)
                
                return {
                    "status": "approved",
                    "tracking_no": shipping_result["tracking_no"],
                    "carrier": shipping_result["carrier"]
                }
            else:
                return {"status": "pending", "reason": "物流生成失败"}
        
        # 需要人工审核
        await self._create_review_ticket(order, risk_score)
        return {"status": "escalated", "reason": "需要人工审核"}
    
    async def _risk_assessment(self, order: Dict) -> float:
        """订单风控评估"""
        risk_factors = []
        
        # 1. 黑名单检查
        if order["customer_id"] in self.risk_rules["blacklist"]:
            risk_factors.append(0.9)
        
        # 2. 金额异常
        if order["total_amount"] > self.risk_rules["max_amount"]:
            risk_factors.append(0.5)
        
        # 3. 收货地址异常
        if await self._is_suspicious_address(order["shipping_address"]):
            risk_factors.append(0.6)
        
        # 4. 购买行为异常
        recent_orders = await self._get_customer_recent_orders(
            order["customer_id"], 
            days=1
        )
        if len(recent_orders) > self.risk_rules["max_daily_orders"]:
            risk_factors.append(0.4)
        
        # 5. 备注关键词检查
        if any(kw in order.get("remark", "") for kw in self.risk_rules["suspicious_keywords"]):
            risk_factors.append(0.7)
        
        return max(risk_factors) if risk_factors else 0.0
    
    async def _generate_shipping_label(self, order: Dict) -> Dict:
        """生成快递面单"""
        # 选择快递公司
        carrier = self._select_carrier(order)
        
        # 生成运单号（模拟）
        tracking_no = f"{carrier.upper()}{datetime.now().strftime('%Y%m%d')}{random.randint(100000, 999999)}"
        
        print(f"    生成 {carrier} 运单: {tracking_no}")
        
        return {
            "success": True,
            "carrier": carrier,
            "tracking_no": tracking_no,
            "label_url": f"https://api.company.com/labels/{tracking_no}.pdf"
        }
    
    def _select_carrier(self, order: Dict) -> str:
        """选择快递公司"""
        # 根据地址、重量、时效选择
        address = order["shipping_address"]
        
        if "新疆" in address or "西藏" in address:
            return "ems"  # 偏远地区用 EMS
        elif order.get("total_amount", 0) > 500:
            return "sf"  # 高价值用顺丰
        else:
            return random.choice(["yto", "jd", "zto"])  # 其他随机
    
    async def _check_inventory(self, items: List[Dict]) -> bool:
        """检查库存"""
        for item in items:
            stock = await self._get_product_stock(item["sku"])
            if stock < item["quantity"]:
                print(f"    库存不足: {item['sku']} (需要 {item['quantity']}, 库存 {stock})")
                return False
        return True
    
    async def _notify_warehouse(self, order: Dict, shipping: Dict):
        """通知仓库发货"""
        print(f"    通知仓库发货: 订单 {order['order_id']}, 运单 {shipping['tracking_no']}")
        # 调用仓库 API 或发送消息
    
    async def _notify_customer(self, order: Dict, shipping: Dict):
        """通知客户发货"""
        message = (
            f"您的订单 {order['order_no']} 已发货！\n"
            f"快递公司：{shipping['carrier']}\n"
            f"运单号：{shipping['tracking_no']}\n"
            f"预计 3-5 天送达，请注意查收。"
        )
        print(f"    通知客户: {message[:100]}...")
        # 发送短信/站内信
    
    # ============ 数据库操作（模拟）============
    
    async def _get_pending_orders(self, limit: int = 100) -> List[Dict]:
        """获取待处理订单"""
        # 模拟数据
        return [
            {
                "order_id": f"ORD{random.randint(10000, 99999)}",
                "order_no": f"TB{random.randint(100000000, 999999999)}",
                "customer_id": f"CUST{random.randint(1000, 9999)}",
                "total_amount": random.uniform(50, 2000),
                "status": "pending"
            }
            for _ in range(min(limit, 5))  # 模拟 5 个订单
        ]
    
    async def _get_order_detail(self, order_id: str) -> Optional[Dict]:
        """获取订单详情"""
        return {
            "order_id": order_id,
            "order_no": "TB123456789",
            "customer_id": "CUST1001",
            "total_amount": 299.00,
            "shipping_address": "北京市朝阳区xxx街道",
            "items": [
                {"sku": "SKU001", "name": "商品A", "quantity": 1}
            ],
            "remark": ""
        }
    
    async def _update_order_status(self, order_id: str, status: str, extra: Dict):
        """更新订单状态"""
        print(f"    更新订单 {order_id} 状态为: {status}")
    
    async def _is_suspicious_address(self, address: str) -> bool:
        """检查可疑地址"""
        suspicious_patterns = ["测试", "test", "某某"]
        return any(p in address for p in suspicious_patterns)
    
    async def _get_customer_recent_orders(self, customer_id: str, days: int) -> List[Dict]:
        """获取客户最近订单"""
        return []
    
    async def _get_product_stock(self, sku: str) -> int:
        """获取商品库存"""
        return random.randint(0, 100)
    
    async def _notify_low_stock(self, items: List[Dict]):
        """通知库存不足"""
        print(f"    库存不足通知: {[i['sku'] for i in items]}")
    
    async def _flag_suspicious_order(self, order: Dict, reason: str):
        """标记可疑订单"""
        print(f"    ⚠️ 标记可疑订单 {order['order_id']}: {reason}")
    
    async def _create_review_ticket(self, order: Dict, risk_score: float):
        """创建人工审核工单"""
        print(f"    创建审核工单: 订单 {order['order_id']}, 风险分 {risk_score}")

# Skill 入口点
skill = OrderAutomationSkill
