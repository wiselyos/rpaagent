# 电商平台对接

支持淘宝、京东、拼多多、抖音等主流电商平台 API 对接

## 支持的平台

| 平台 | 状态 | 功能 |
|------|------|------|
| 淘宝/天猫 | ✅ | 订单同步、商品管理、物流对接 |
| 京东 | ✅ | 订单同步、库存管理、售后处理 |
| 拼多多 | ✅ | 订单同步、商品上架、营销活动 |
| 抖音电商 | ✅ | 订单同步、直播数据、达人对接 |

## 快速开始

```python
from platforms import PlatformManager

# 初始化平台管理器
manager = PlatformManager()

# 添加平台账号
manager.add_account(
    platform="taobao",
    app_key="your-app-key",
    app_secret="your-app-secret",
    session="your-session"
)

# 同步订单
orders = await manager.sync_orders(
    platform="taobao",
    start_time="2026-03-01 00:00:00",
    end_time="2026-03-01 23:59:59"
)

# 同步商品
products = await manager.sync_products(platform="taobao")
```

## 配置

```json
{
  "platforms": {
    "taobao": {
      "app_key": "your-app-key",
      "app_secret": "your-app-secret",
      "sandbox": false
    },
    "jd": {
      "app_key": "your-app-key",
      "app_secret": "your-app-secret"
    }
  }
}
```
