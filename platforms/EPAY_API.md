# 电商系统 API 集成文档

## 系统信息

- **接口地址**: https://epay.alizzy.com/outside/25/
- **应用 APPID**: 2026021502557128
- **加密方式**: MD5 签名

## 快速开始

```python
from platforms.epay_integration import EPayIntegration

# 初始化
integration = EPayIntegration(
    app_id="2026021502557128",
    app_secret="E59CA750B7BF3950171C314D83F6995B"
)

# 同步订单
orders = await integration.sync_orders(days=1)

# 处理待发货订单
result = await integration.process_pending_orders()

# 检查低库存
low_stock = await integration.check_low_stock(threshold=10)

# 生成日报
report = await integration.generate_daily_report()
```

## 签名算法

```python
import hashlib

# 1. 拼接参数（按 key 排序）
params = {
    "app_id": "2026021502557128",
    "timestamp": "1709289600",
    "nonce": "a1b2c3d4e5f6"
}

# 2. 生成签名字符串
sign_str = app_secret
for k, v in sorted(params.items()):
    sign_str += f"{k}{v}"
sign_str += app_secret

# 3. MD5 加密
sign = hashlib.md5(sign_str.encode()).hexdigest().upper()
```

## 接口列表

### 订单接口

| 接口 | 方法 | 说明 |
|------|------|------|
| order/list | POST | 获取订单列表 |
| order/detail | POST | 获取订单详情 |
| order/update_status | POST | 更新订单状态 |
| order/ship | POST | 订单发货 |

### 商品接口

| 接口 | 方法 | 说明 |
|------|------|------|
| product/list | POST | 获取商品列表 |
| product/detail | POST | 获取商品详情 |
| product/update_stock | POST | 更新库存 |
| product/update_price | POST | 更新价格 |

### 退款接口

| 接口 | 方法 | 说明 |
|------|------|------|
| refund/apply | POST | 申请退款 |
| refund/list | POST | 获取退款列表 |

### 报表接口

| 接口 | 方法 | 说明 |
|------|------|------|
| report/daily | POST | 获取日报 |
| report/order_stats | POST | 订单统计 |
| report/sales_ranking | POST | 销售排行 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| -1 | 系统错误 |
| 1001 | 参数错误 |
| 1002 | 签名错误 |
| 1003 | APPID 无效 |
| 1004 | 订单不存在 |
| 1005 | 库存不足 |

## 集成到订单自动化

修改 `skills/order-automation/handler.py`:

```python
from platforms.epay_integration import EPayIntegration

class OrderAutomationSkill:
    def __init__(self, context):
        self.epay = EPayIntegration(
            app_id="2026021502557128",
            app_secret="E59CA750B7BF3950171C314D83F6995B"
        )
    
    async def process_pending_orders(self):
        # 使用电商系统 API 处理订单
        return await self.epay.process_pending_orders()
```
