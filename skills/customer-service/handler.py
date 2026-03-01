#!/usr/bin/env python3
"""
智能客服 Skill - 核心处理逻辑
"""
import json
import re
from datetime import datetime
from typing import Optional, Dict, List

class CustomerServiceSkill:
    """电商智能客服 Skill"""
    
    def __init__(self, context):
        self.context = context
        self.db = context.get_database("ecommerce")
        self.ai = context.get_model("kimi-coding/k2p5")
        
        # 加载知识库
        self.knowledge_base = self._load_knowledge_base()
        
        # 意图分类器
        self.intent_patterns = {
            "order_status": ["订单.*哪里", "快递.*到哪", "发货.*没", "物流.*查询"],
            "refund_request": ["退货", "退款", "不要了", "取消订单"],
            "product_inquiry": ["有货吗", "库存", "多少钱", "价格"],
            "shipping_issue": ["没收到", "丢件", "破损", "少发"],
            "complaint": ["投诉", "差评", "服务态度", "太差了"],
            "technical_issue": ["打不开", "无法支付", "页面错误", "系统故障"],
            "promotion": ["优惠券", "活动", "折扣", "满减"],
            "account": ["密码", "登录", "注册", "账号"]
        }
    
    def _load_knowledge_base(self) -> Dict:
        """加载知识库"""
        return {
            "shipping_time": "一般 24 小时内发货，3-5 天送达",
            "return_policy": "支持 7 天无理由退货，请确保商品完好",
            "payment_methods": "支持支付宝、微信支付、银行卡",
            "contact": "客服电话 400-xxx-xxxx，工作时间 9:00-21:00"
        }
    
    async def handle_message(self, customer_id: str, message: str, 
                           order_id: Optional[str] = None,
                           platform: str = "taobao") -> Dict:
        """
        处理客户消息
        
        Returns:
            {
                "handled": bool,
                "response": str,
                "confidence": float,
                "escalate": bool,
                "intent": str
            }
        """
        print(f"[{platform}] 收到客户 {customer_id} 消息: {message[:50]}...")
        
        # 1. 意图识别
        intent = self._classify_intent(message)
        print(f"  识别意图: {intent}")
        
        # 2. 获取上下文
        context_info = await self._gather_context(customer_id, order_id)
        
        # 3. 根据意图处理
        if intent == "order_status":
            response = await self._handle_order_query(context_info, order_id)
        elif intent == "refund_request":
            response = await self._handle_refund_request(context_info, order_id, message)
        elif intent == "product_inquiry":
            response = await self._handle_product_inquiry(message)
        elif intent in self.knowledge_base:
            response = self.knowledge_base.get(intent, "")
        else:
            # 使用 AI 生成回复
            response = await self._generate_ai_response(message, intent, context_info)
        
        # 4. 评估置信度
        confidence = self._evaluate_confidence(response, intent)
        
        # 5. 判断是否需要转人工
        escalate = (
            confidence < 0.6 or 
            intent in ["complaint", "technical_issue"] or
            "人工" in message or
            "客服" in message
        )
        
        # 6. 保存对话记录
        await self._save_conversation(customer_id, message, response, intent, not escalate)
        
        return {
            "handled": not escalate,
            "response": response,
            "confidence": confidence,
            "escalate": escalate,
            "intent": intent
        }
    
    def _classify_intent(self, message: str) -> str:
        """基于规则识别意图"""
        message = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    return intent
        
        return "general"
    
    async def _gather_context(self, customer_id: str, order_id: Optional[str]) -> Dict:
        """获取客户上下文信息"""
        context = {
            "customer_id": customer_id,
            "order_id": order_id,
            "recent_orders": [],
            "conversation_history": []
        }
        
        # 查询最近订单
        if order_id:
            order = await self._query_order(order_id)
            context["current_order"] = order
        
        # 查询历史对话
        history = await self._get_conversation_history(customer_id, limit=5)
        context["conversation_history"] = history
        
        return context
    
    async def _query_order(self, order_id: str) -> Optional[Dict]:
        """查询订单信息"""
        # 模拟查询，实际应连接数据库
        return {
            "order_id": order_id,
            "status": "shipped",
            "status_text": "已发货",
            "tracking_no": "SF1234567890",
            "carrier": "顺丰速运",
            "items": [{"name": "示例商品", "quantity": 1}],
            "total": 199.00,
            "created_at": "2026-03-01 10:00:00"
        }
    
    async def _handle_order_query(self, context: Dict, order_id: Optional[str]) -> str:
        """处理订单查询"""
        if not order_id and context.get("recent_orders"):
            order_id = context["recent_orders"][0]["order_id"]
        
        if not order_id:
            return "请提供订单号，我可以帮您查询物流状态。"
        
        order = await self._query_order(order_id)
        if not order:
            return f"未找到订单 {order_id}，请确认订单号是否正确。"
        
        return (
            f"订单 {order_id} 当前状态：{order['status_text']}\n"
            f"快递公司：{order['carrier']}\n"
            f"运单号：{order['tracking_no']}\n"
            f"您可以通过快递公司官网或支付宝查询详细物流信息。"
        )
    
    async def _handle_refund_request(self, context: Dict, order_id: Optional[str], 
                                    reason: str) -> str:
        """处理退款申请"""
        if not order_id:
            return "请提供需要退款的订单号，我将为您处理。"
        
        # 这里应调用退款流程
        return (
            f"已收到您的退款申请（订单：{order_id}）。\n"
            f"退款原因：{reason[:50]}...\n"
            f"我们将在 1-2 个工作日内处理，退款将原路返回。\n"
            f"如有疑问请联系人工客服。"
        )
    
    async def _handle_product_inquiry(self, message: str) -> str:
        """处理商品咨询"""
        # 提取商品信息
        return (
            "感谢您的咨询！该商品目前有现货，24 小时内发货。\n"
            "现在购买可享受满 199 减 20 优惠。\n"
            "如需了解更多详情，请查看商品详情页或咨询人工客服。"
        )
    
    async def _generate_ai_response(self, message: str, intent: str, 
                                   context: Dict) -> str:
        """使用 AI 生成回复"""
        
        prompt = f"""你是一位专业的电商客服助手。请根据以下信息回复客户：

客户问题：{message}
问题类型：{intent}
客户ID：{context.get('customer_id')}

回复要求：
1. 语气友好、专业、耐心
2. 直接回答客户问题
3. 如涉及订单，提供具体信息
4. 必要时给出解决方案或下一步操作
5. 控制回复在 200 字以内

请生成回复："""
        
        try:
            response = await self.ai.generate(prompt, temperature=0.7, max_tokens=300)
            return response.strip()
        except Exception as e:
            print(f"AI 生成回复失败: {e}")
            return "感谢您的咨询，我已记录您的问题，稍后会有专员联系您。"
    
    def _evaluate_confidence(self, response: str, intent: str) -> float:
        """评估回复置信度"""
        # 简单规则评估
        confidence = 0.7
        
        # 如果有具体信息，提高置信度
        if any(x in response for x in ["订单", "快递", "已发货", "退款"]):
            confidence += 0.1
        
        # 如果回复太短，降低置信度
        if len(response) < 20:
            confidence -= 0.2
        
        return min(max(confidence, 0.0), 1.0)
    
    async def _save_conversation(self, customer_id: str, message: str, 
                                response: str, intent: str, ai_handled: bool):
        """保存对话记录"""
        print(f"  保存对话记录: customer={customer_id}, intent={intent}, ai_handled={ai_handled}")
        # 实际应写入数据库
    
    async def _get_conversation_history(self, customer_id: str, limit: int = 5) -> List[Dict]:
        """获取历史对话"""
        return []

# Skill 入口点
skill = CustomerServiceSkill
