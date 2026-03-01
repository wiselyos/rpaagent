# RPA 模块使用示例

## 1. 价格监控

```python
import asyncio
from rpa.scrapers.price_monitor import PriceMonitor, PriceData

async def main():
    # 创建价格监控器
    monitor = PriceMonitor(headless=True)
    
    # 检查单个商品价格
    url = "https://item.jd.com/100012043978.html"
    price_data = await monitor.check_price(url)
    
    if price_data:
        print(f"商品: {price_data.product_name}")
        print(f"当前价格: ¥{price_data.current_price}")
        print(f"原价: ¥{price_data.original_price}")
    
    # 批量检查
    urls = [
        "https://item.jd.com/100012043978.html",
        "https://detail.tmall.com/item.htm?id=123456",
    ]
    results = await monitor.check_prices(urls)
    
    # 关闭
    await monitor.close()

asyncio.run(main())
```

## 2. 商品信息抓取

```python
import asyncio
from rpa.scrapers.product_info import ProductInfoManager

async def main():
    # 创建商品信息管理器
    manager = ProductInfoManager(headless=True)
    
    # 抓取商品信息
    url = "https://item.jd.com/100012043978.html"
    product = await manager.scrape_product(url)
    
    if product:
        print(f"标题: {product.title}")
        print(f"价格: ¥{product.price}")
        print(f"店铺: {product.shop_name}")
        print(f"图片数: {len(product.images)}")
        
        # 保存为字典
        data = product.to_dict()
    
    await manager.close()

asyncio.run(main())
```

## 3. 使用反检测功能

```python
from rpa.utils.anti_detection import (
    AntiDetectionManager,
    Proxy,
    UserAgentRotator
)

# 创建反检测管理器
anti_detection = AntiDetectionManager(
    requests_per_second=0.5,  # 每秒最多0.5个请求
    min_delay=2.0,            # 最小延迟2秒
    max_delay=5.0             # 最大延迟5秒
)

# 添加代理
proxy = Proxy(
    host="proxy.example.com",
    port=8080,
    username="user",
    password="pass"
)
anti_detection.proxy_pool.add_proxy(proxy)

# 获取会话配置
config = await anti_detection.get_session_config()
# config 包含随机的 User-Agent 和代理
```

## 4. 使用 Playwright Helper

```python
from rpa.playwright_helper import PlaywrightHelper, BrowserConfig

async def main():
    # 创建配置
    config = BrowserConfig(
        headless=False,  # 有头模式，方便调试
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0..."
    )
    
    # 创建 helper
    async with PlaywrightHelper(config) as helper:
        # 导航到页面
        page = await helper.goto("https://www.example.com")
        
        # 安全点击
        await helper.safe_click(page, "#button")
        
        # 安全填充
        await helper.safe_fill(page, "#input", "value")
        
        # 滚动页面
        await helper.scroll_to_bottom(page)

asyncio.run(main())
```

## 5. 持续价格监控

```python
async def on_price_change(old_price: PriceData, new_price: PriceData):
    print(f"价格变动! {old_price.current_price} -> {new_price.current_price}")
    # 发送通知等

monitor = PriceMonitor(
    headless=True,
    on_price_change=on_price_change
)

# 开始监控
await monitor.start_monitoring(
    url="https://item.jd.com/100012043978.html",
    interval_minutes=30,  # 每30分钟检查一次
)
```
