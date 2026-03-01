# 喵呜商城 API 文档

## 系统信息

- **接口地址**: `https://epay.alizzy.com/outside/{uniacid}/`
- **uniacid**: 25
- **应用 APPID**: 2026021502557128
- **签名方式**: HMAC-SHA256

## 快速开始

```python
from platforms.mall_integration import MallIntegration

# 初始化
integration = MallIntegration(
    app_id="2026021502557128",
    app_secret="E59CA750B7BF3950171C314D83F6995B",
    uniacid="25"
)

# 同步订单
orders = await integration.sync_orders(days=1)

# 处理待发货订单
result = await integration.process_pending_orders()

# 自动创建并支付订单
result = await integration.auto_create_and_pay_order(
    uid=123,
    goods=[{"goods_id": 1, "option_id": 10, "total": 2}]
)
```

## 签名算法

```python
import hmac
import hashlib

# 1. 将所有参数按字典序排序
sorted_params = sorted(params.items())

# 2. 拼接字符串（排除sign参数）
query_string = "&".join([f"{k}={v}" for k, v in sorted_params if k != "sign"])

# 3. HMAC-SHA256 签名
sign = hmac.new(
    app_secret.encode('utf-8'),
    query_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

## 订单状态

| 状态码 | 状态名称 | 说明 |
|--------|----------|------|
| 0 | 待付款 | 订单已创建，等待支付 |
| 1 | 待发货 | 订单已支付，等待发货 |
| 2 | 待收货 | 订单已发货，等待收货 |
| 3 | 已完成 | 订单已完成 |
| -1 | 已关闭 | 订单已关闭 |

## 接口列表

### 订单计算
- **接口**: `POST /outside/{uniacid}/order/buy`
- **功能**: 计算订单价格

### 创建订单
- **接口**: `POST /outside/{uniacid}/order/create`
- **功能**: 创建订单
- **注意**: outside_sn 必须唯一

### 订单列表
- **接口**: `GET /outside/{uniacid}/order/list`
- **功能**: 查询订单列表（不分页）

### 订单分页
- **接口**: `GET /outside/{uniacid}/order/page`
- **功能**: 分页查询订单

### 订单支付
- **接口**: `POST /outside/{uniacid}/order/pay`
- **功能**: 后台支付订单

### 订单发货
- **接口**: `POST /outside/{uniacid}/order/send`
- **功能**: 订单发货

### 订单收货
- **接口**: `POST /outside/{uniacid}/order/receive`
- **功能**: 确认收货

### 退款关闭
- **接口**: `POST /outside/{uniacid}/order/closeRefund`
- **功能**: 退款并关闭订单

## 错误码

| 错误码 | 说明 |
|--------|------|
| ERR000 | 通用错误 |
| - | 订单号已存在 |
| - | 会员不存在 |
| - | 应用不存在 |
| - | 应用已关闭 |
| - | 签名验证失败 |

## 数据库表

### yz_outside_order_trade
第三方订单关系表

### yz_outside_order_has_many_order
第三方订单与商城订单关联表
