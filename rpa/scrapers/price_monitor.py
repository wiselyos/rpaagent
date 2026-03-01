"""
Price Monitor - 价格监控爬虫
支持淘宝、京东、拼多多等平台的价格监控
"""

import asyncio
import re
import json
import logging
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from playwright.async_api import Page, ElementHandle

from ..playwright_helper import PlaywrightHelper, BrowserConfig
from ..utils.anti_detection import (
    AntiDetectionManager, 
    create_anti_detection_manager,
    get_random_viewport
)

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """价格数据"""
    platform: str
    product_id: str
    product_name: str
    current_price: float
    original_price: Optional[float] = None
    currency: str = "CNY"
    url: str = ""
    timestamp: datetime = None
    additional_info: Dict = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.additional_info is None:
            self.additional_info = {}
            
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class BasePriceScraper:
    """基础价格爬虫"""
    
    PLATFORM = "base"
    
    def __init__(
        self,
        anti_detection: Optional[AntiDetectionManager] = None,
        headless: bool = True
    ):
        self.anti_detection = anti_detection or create_anti_detection_manager()
        self.headless = headless
        self._helper: Optional[PlaywrightHelper] = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """启动爬虫"""
        config = await self.anti_detection.get_session_config()
        browser_config = BrowserConfig(
            headless=self.headless,
            user_agent=config.get("user_agent"),
            proxy=config.get("proxy"),
            viewport=get_random_viewport()
        )
        self._helper = PlaywrightHelper(browser_config)
        await self._helper.start()
        await self._helper.launch_browser()
        
    async def close(self):
        """关闭爬虫"""
        if self._helper:
            await self._helper.close()
            self._helper = None
            
    async def scrape_price(self, url: str) -> Optional[PriceData]:
        """抓取价格 - 子类需要实现"""
        raise NotImplementedError
        
    def _extract_price(self, text: str) -> Optional[float]:
        """从文本中提取价格"""
        if not text:
            return None
        # 匹配价格格式: ¥100, 100元, 100.00等
        patterns = [
            r'[¥￥]\s*(\d+(?:\.\d{1,2})?)',
            r'(\d+(?:\.\d{1,2})?)\s*[元¥￥]',
            r'price["\']?\s*[:=]\s*["\']?(\d+(?:\.\d{1,2})?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None


class TaobaoScraper(BasePriceScraper):
    """淘宝价格爬虫"""
    
    PLATFORM = "taobao"
    
    async def scrape_price(self, url: str) -> Optional[PriceData]:
        """抓取淘宝商品价格"""
        try:
            product_id = self._extract_product_id(url)
            if not product_id:
                logger.error(f"无法从URL提取商品ID: {url}")
                return None
                
            page = await self._helper.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 尝试多种选择器获取价格
            price_selectors = [
                '.tb-rmb-num',  # 普通商品
                '[class*="price"]',
                '[class*="Price"]',
                '.notranslate',
                '[data-spm="price"]',
            ]
            
            current_price = None
            for selector in price_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        price_text = await element.text_content()
                        current_price = self._extract_price(price_text)
                        if current_price:
                            break
                except:
                    continue
                    
            # 获取商品标题
            title_selectors = [
                'h1[data-spm="1000983"]',
                '.tb-detail-hd h1',
                '[class*="title"]',
                'h1',
            ]
            
            product_name = ""
            for selector in title_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        product_name = await element.text_content()
                        product_name = product_name.strip()
                        if product_name:
                            break
                except:
                    continue
                    
            # 获取原价
            original_price = None
            try:
                # 尝试从页面数据中获取
                original_price_text = await page.evaluate('''() => {
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const text = script.textContent;
                        if (text.includes('price') || text.includes('Price')) {
                            return text;
                        }
                    }
                    return '';
                }''')
                # 尝试解析 JSON 数据
                price_match = re.search(r'"reservePrice["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)', original_price_text)
                if price_match:
                    original_price = float(price_match.group(1))
            except:
                pass
                
            if current_price:
                return PriceData(
                    platform=self.PLATFORM,
                    product_id=product_id,
                    product_name=product_name or "未知商品",
                    current_price=current_price,
                    original_price=original_price,
                    url=url
                )
                
            logger.warning(f"无法获取商品价格: {url}")
            return None
            
        except Exception as e:
            logger.error(f"抓取淘宝价格失败: {url}, 错误: {e}")
            return None
            
    def _extract_product_id(self, url: str) -> Optional[str]:
        """从淘宝URL提取商品ID"""
        patterns = [
            r'id=(\d+)',
            r'item/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class JDScraper(BasePriceScraper):
    """京东价格爬虫"""
    
    PLATFORM = "jd"
    
    async def scrape_price(self, url: str) -> Optional[PriceData]:
        """抓取京东商品价格"""
        try:
            product_id = self._extract_product_id(url)
            if not product_id:
                logger.error(f"无法从URL提取商品ID: {url}")
                return None
                
            page = await self._helper.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 获取价格 - 京东价格通常在特定元素中
            price_selectors = [
                '.price-now .p-price .price',
                '.p-price .price',
                '[class*="price-now"]',
                '#jd-price',
                '.summary-price .price',
            ]
            
            current_price = None
            for selector in price_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        price_text = await element.text_content()
                        current_price = self._extract_price(price_text)
                        if current_price:
                            break
                except:
                    continue
                    
            # 尝试从页面脚本获取价格
            if not current_price:
                try:
                    price_data = await page.evaluate('''() => {
                        if (window.pageConfig && window.pageConfig.product) {
                            return window.pageConfig.product;
                        }
                        return null;
                    }''')
                    if price_data and 'price' in price_data:
                        current_price = float(price_data['price'])
                except:
                    pass
                    
            # 获取商品标题
            title_selectors = [
                '.sku-name',
                '.product-intro .name',
                'h1',
                '[class*="sku-name"]',
            ]
            
            product_name = ""
            for selector in title_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        product_name = await element.text_content()
                        product_name = product_name.strip()
                        if product_name:
                            break
                except:
                    continue
                    
            # 获取原价
            original_price = None
            try:
                original_element = await page.query_selector('.p-price .del')
                if original_element:
                    original_text = await original_element.text_content()
                    original_price = self._extract_price(original_text)
            except:
                pass
                
            if current_price:
                return PriceData(
                    platform=self.PLATFORM,
                    product_id=product_id,
                    product_name=product_name or "未知商品",
                    current_price=current_price,
                    original_price=original_price,
                    url=url
                )
                
            logger.warning(f"无法获取商品价格: {url}")
            return None
            
        except Exception as e:
            logger.error(f"抓取京东价格失败: {url}, 错误: {e}")
            return None
            
    def _extract_product_id(self, url: str) -> Optional[str]:
        """从京东URL提取商品ID"""
        # 京东商品ID通常是数字
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)
        # 尝试其他格式
        match = re.search(r'sku[Ii]d=(\d+)', url)
        if match:
            return match.group(1)
        return None


class PDDScraper(BasePriceScraper):
    """拼多多价格爬虫"""
    
    PLATFORM = "pdd"
    
    async def scrape_price(self, url: str) -> Optional[PriceData]:
        """抓取拼多多商品价格"""
        try:
            product_id = self._extract_product_id(url)
            if not product_id:
                logger.error(f"无法从URL提取商品ID: {url}")
                return None
                
            page = await self._helper.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载 - 拼多多页面加载较慢
            await asyncio.sleep(3)
            
            # 获取价格
            price_selectors = [
                '[class*="price"]',
                '[class*="_price"]',
                '.goods-price',
                '[data-testid="price"]',
            ]
            
            current_price = None
            for selector in price_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        price_text = await element.text_content()
                        current_price = self._extract_price(price_text)
                        if current_price:
                            break
                except:
                    continue
                    
            # 尝试从页面脚本获取
            if not current_price:
                try:
                    page_data = await page.evaluate('''() => {
                        const scripts = document.querySelectorAll('script');
                        for (const script of scripts) {
                            const text = script.textContent;
                            if (text.includes('goods') || text.includes('price')) {
                                const match = text.match(/price["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)/);
                                if (match) return parseFloat(match[1]);
                            }
                        }
                        return null;
                    }''')
                    if page_data:
                        current_price = page_data
                except:
                    pass
                    
            # 获取商品标题
            title_selectors = [
                '[class*="goods-name"]',
                '[class*="title"]',
                'h1',
            ]
            
            product_name = ""
            for selector in title_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        product_name = await element.text_content()
                        product_name = product_name.strip()
                        if product_name:
                            break
                except:
                    continue
                    
            if current_price:
                return PriceData(
                    platform=self.PLATFORM,
                    product_id=product_id,
                    product_name=product_name or "未知商品",
                    current_price=current_price,
                    url=url
                )
                
            logger.warning(f"无法获取商品价格: {url}")
            return None
            
        except Exception as e:
            logger.error(f"抓取拼多多价格失败: {url}, 错误: {e}")
            return None
            
    def _extract_product_id(self, url: str) -> Optional[str]:
        """从拼多多URL提取商品ID"""
        # 拼多多商品ID
        match = re.search(r'goods_id=(\d+)', url)
        if match:
            return match.group(1)
        return None


class PriceMonitor:
    """价格监控器 - 统一管理多个平台的监控任务"""
    
    def __init__(
        self,
        anti_detection: Optional[AntiDetectionManager] = None,
        headless: bool = True,
        on_price_change: Optional[Callable[[PriceData, PriceData], None]] = None
    ):
        self.anti_detection = anti_detection or create_anti_detection_manager()
        self.headless = headless
        self.on_price_change = on_price_change
        self._scrapers: Dict[str, BasePriceScraper] = {}
        self._price_history: Dict[str, List[PriceData]] = {}
        self._running = False
        
    def _get_scraper(self, platform: str) -> BasePriceScraper:
        """获取或创建爬虫实例"""
        if platform not in self._scrapers:
            if platform == "taobao":
                self._scrapers[platform] = TaobaoScraper(
                    self.anti_detection, 
                    self.headless
                )
            elif platform == "jd":
                self._scrapers[platform] = JDScraper(
                    self.anti_detection, 
                    self.headless
                )
            elif platform == "pdd":
                self._scrapers[platform] = PDDScraper(
                    self.anti_detection, 
                    self.headless
                )
            else:
                raise ValueError(f"不支持的平台: {platform}")
        return self._scrapers[platform]
        
    def _detect_platform(self, url: str) -> Optional[str]:
        """从URL检测平台"""
        if "taobao.com" in url or "tmall.com" in url:
            return "taobao"
        elif "jd.com" in url:
            return "jd"
        elif "pinduoduo.com" in url or "yangkeduo.com" in url:
            return "pdd"
        return None
        
    async def check_price(self, url: str) -> Optional[PriceData]:
        """检查单个商品价格"""
        platform = self._detect_platform(url)
        if not platform:
            logger.error(f"无法识别平台: {url}")
            return None
            
        scraper = self._get_scraper(platform)
        
        # 确保爬虫已启动
        if not scraper._helper:
            await scraper.start()
            
        price_data = await scraper.scrape_price(url)
        
        if price_data:
            # 保存到历史记录
            product_key = f"{price_data.platform}:{price_data.product_id}"
            if product_key not in self._price_history:
                self._price_history[product_key] = []
            
            history = self._price_history[product_key]
            if history:
                last_price = history[-1]
                if last_price.current_price != price_data.current_price:
                    logger.info(
                        f"价格变动: {price_data.product_name} "
                        f"{last_price.current_price} -> {price_data.current_price}"
                    )
                    if self.on_price_change:
                        self.on_price_change(last_price, price_data)
                        
            history.append(price_data)
            
        return price_data
        
    async def check_prices(self, urls: List[str]) -> List[PriceData]:
        """批量检查价格"""
        results = []
        for url in urls:
            try:
                price_data = await self.check_price(url)
                if price_data:
                    results.append(price_data)
            except Exception as e:
                logger.error(f"检查价格失败: {url}, 错误: {e}")
        return results
        
    async def start_monitoring(
        self,
        url: str,
        interval_minutes: int = 60,
        callback: Optional[Callable[[PriceData], None]] = None
    ):
        """开始持续监控价格"""
        self._running = True
        while self._running:
            try:
                price_data = await self.check_price(url)
                if price_data and callback:
                    callback(price_data)
            except Exception as e:
                logger.error(f"监控异常: {e}")
                
            await asyncio.sleep(interval_minutes * 60)
            
    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        
    async def close(self):
        """关闭所有爬虫"""
        for scraper in self._scrapers.values():
            await scraper.close()
        self._scrapers.clear()
        
    def get_price_history(self, platform: str, product_id: str) -> List[PriceData]:
        """获取价格历史"""
        product_key = f"{platform}:{product_id}"
        return self._price_history.get(product_key, [])
        
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "monitored_products": len(self._price_history),
            "total_records": sum(len(h) for h in self._price_history.values()),
            "anti_detection": self.anti_detection.get_stats()
        }
