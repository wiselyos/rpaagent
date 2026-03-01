#!/usr/bin/env python3
"""
消息通知系统 - Notification System
支持多渠道：钉钉、飞书、企业微信、邮件、短信
"""
import json
import hmac
import hashlib
import base64
import urllib.request
from typing import List, Optional, Dict
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class ChannelType(Enum):
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    WECHAT = "wechat"
    EMAIL = "email"
    SMS = "sms"

@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    content: str
    message_type: str  # text, markdown, card
    data: Optional[Dict] = None
    priority: str = "normal"  # low, normal, high, urgent

class DingTalkNotifier:
    """钉钉通知"""
    
    def __init__(self, webhook: str, secret: Optional[str] = None):
        self.webhook = webhook
        self.secret = secret
    
    def _generate_sign(self, timestamp: str) -> str:
        """生成签名"""
        if not self.secret:
            return ""
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return urllib.request.quote(base64.b64encode(hmac_code))
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送钉钉消息"""
        timestamp = str(round(datetime.now().timestamp() * 1000))
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": message.title,
                "text": message.content
            }
        }
        
        # 添加签名
        if self.secret:
            sign = self._generate_sign(timestamp)
            url = f"{self.webhook}&timestamp={timestamp}&sign={sign}"
        else:
            url = self.webhook
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('errcode') == 0
                
        except Exception as e:
            print(f"钉钉发送失败: {e}")
            return False

class FeishuNotifier:
    """飞书通知"""
    
    def __init__(self, webhook: str):
        self.webhook = webhook
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送飞书消息"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": message.title
                    },
                    "template": self._get_template_by_priority(message.priority)
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": message.content
                        }
                    }
                ]
            }
        }
        
        try:
            req = urllib.request.Request(
                self.webhook,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('code') == 0
                
        except Exception as e:
            print(f"飞书发送失败: {e}")
            return False
    
    def _get_template_by_priority(self, priority: str) -> str:
        """根据优先级获取颜色模板"""
        templates = {
            "low": "grey",
            "normal": "blue",
            "high": "orange",
            "urgent": "red"
        }
        return templates.get(priority, "blue")

class EmailNotifier:
    """邮件通知"""
    
    def __init__(self, smtp_host: str, smtp_port: int, 
                 username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    async def send(self, message: NotificationMessage, 
                   recipients: List[str]) -> bool:
        """发送邮件"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = message.title
            
            msg.attach(MIMEText(message.content, 'html', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.notifiers = {}
        self._init_notifiers()
    
    def _init_notifiers(self):
        """初始化通知器"""
        # 钉钉
        dingtalk_config = self.config.get('dingtalk', {})
        if dingtalk_config.get('enabled'):
            self.notifiers[ChannelType.DINGTALK] = DingTalkNotifier(
                webhook=dingtalk_config['webhook'],
                secret=dingtalk_config.get('secret')
            )
        
        # 飞书
        feishu_config = self.config.get('feishu', {})
        if feishu_config.get('enabled'):
            self.notifiers[ChannelType.FEISHU] = FeishuNotifier(
                webhook=feishu_config['webhook']
            )
        
        # 邮件
        email_config = self.config.get('email', {})
        if email_config.get('enabled'):
            self.notifiers[ChannelType.EMAIL] = EmailNotifier(
                smtp_host=email_config['smtp_host'],
                smtp_port=email_config['smtp_port'],
                username=email_config['username'],
                password=email_config['password']
            )
    
    async def send(self, message: NotificationMessage, 
                   channels: Optional[List[ChannelType]] = None) -> Dict[ChannelType, bool]:
        """发送消息到指定渠道"""
        if channels is None:
            channels = list(self.notifiers.keys())
        
        results = {}
        for channel in channels:
            if channel in self.notifiers:
                notifier = self.notifiers[channel]
                success = await notifier.send(message)
                results[channel] = success
            else:
                results[channel] = False
        
        return results
    
    # ===== 业务通知快捷方法 =====
    
    async def send_order_notification(self, order_id: str, status: str,
                                     channels: Optional[List[ChannelType]] = None):
        """发送订单状态通知"""
        status_map = {
            "paid": "订单已支付",
            "shipped": "订单已发货",
            "completed": "订单已完成",
            "cancelled": "订单已取消"
        }
        
        message = NotificationMessage(
            title=f"【订单通知】{status_map.get(status, '订单状态变更')}",
            content=f"订单号: {order_id}\n状态: {status_map.get(status, status)}",
            message_type="markdown",
            priority="normal"
        )
        
        return await self.send(message, channels)
    
    async def send_low_stock_alert(self, product_name: str, stock: int,
                                   threshold: int):
        """发送库存预警"""
        message = NotificationMessage(
            title="⚠️ 库存预警",
            content=f"商品: {product_name}\n当前库存: {stock}\n预警阈值: {threshold}",
            message_type="markdown",
            priority="high" if stock == 0 else "normal"
        )
        
        return await self.send(message)
    
    async def send_price_change_alert(self, product_name: str, 
                                     old_price: float, new_price: float,
                                     competitor: str):
        """发送价格变动通知"""
        change = ((new_price - old_price) / old_price) * 100
        direction = "下降" if change < 0 else "上涨"
        
        message = NotificationMessage(
            title=f"💰 价格变动提醒",
            content=(f"商品: {product_name}\n"
                    f"竞品: {competitor}\n"
                    f"原价: ¥{old_price}\n"
                    f"现价: ¥{new_price}\n"
                    f"变动: {direction} {abs(change):.1f}%"),
            message_type="markdown",
            priority="high" if change < -10 else "normal"
        )
        
        return await self.send(message)
    
    async def send_daily_report(self, report_data: Dict):
        """发送日报"""
        message = NotificationMessage(
            title="📊 每日运营报告",
            content=self._format_daily_report(report_data),
            message_type="markdown",
            priority="normal"
        )
        
        return await self.send(message)
    
    def _format_daily_report(self, data: Dict) -> str:
        """格式化日报"""
        return f"""
**订单统计**
- 今日订单: {data.get('orders_today', 0)}
- 成交额: ¥{data.get('revenue_today', 0):.2f}
- 客单价: ¥{data.get('avg_order_value', 0):.2f}

**客服统计**
- 咨询量: {data.get('conversations', 0)}
- AI 处理率: {data.get('ai_handled_rate', 0):.1f}%
- 满意度: {data.get('satisfaction', 0):.1f}/5.0

**库存预警**
- 低库存商品: {data.get('low_stock_count', 0)} 个
- 缺货商品: {data.get('out_of_stock_count', 0)} 个
"""

# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def test():
        config = {
            "dingtalk": {
                "enabled": True,
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
                "secret": "your-secret"
            }
        }
        
        manager = NotificationManager(config)
        
        # 发送库存预警
        result = await manager.send_low_stock_alert(
            product_name="iPhone 15",
            stock=5,
            threshold=10
        )
        
        print(f"发送结果: {result}")
    
    asyncio.run(test())
