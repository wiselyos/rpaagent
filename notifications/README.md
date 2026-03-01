# 消息通知系统

支持多渠道消息推送：钉钉、飞书、企业微信、邮件、短信

## 配置

```json
{
  "notifications": {
    "dingtalk": {
      "enabled": true,
      "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
      "secret": "your-secret"
    },
    "feishu": {
      "enabled": true,
      "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    },
    "email": {
      "enabled": true,
      "smtp_host": "smtp.company.com",
      "smtp_port": 587,
      "username": "notify@company.com",
      "password": "your-password"
    }
  }
}
```

## 使用

```python
from notifications import NotificationManager

notifier = NotificationManager()

# 发送订单通知
await notifier.send_order_notification(
    order_id="ORD12345",
    status="shipped",
    channels=["dingtalk", "email"]
)

# 发送库存预警
await notifier.send_low_stock_alert(
    product_name="iPhone 15",
    stock=5,
    threshold=10
)

# 发送价格变动通知
await notifier.send_price_change_alert(
    product_name="无线耳机",
    old_price=199,
    new_price=149,
    competitor="京东"
)
```
