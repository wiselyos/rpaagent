"""
Product Info Scraper - 商品信息抓取
抓取商品标题、图片、详情等信息
"""

import asyncio
import re
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, ElementHandle

from ..playwright_helper import PlaywrightHelper, BrowserConfig, PagePool
from ..utils.anti_detection import (
    AntiDetectionManager,
    create_anti_detection_manager,
    get_random_viewport
)

logger = logging.getLogger(__name__)


@dataclass
class ProductImage:
    """商品图片"""
    url: str
    type: str = "main"  # main, detail, thumbnail
    alt: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ProductSpec:
    """商品规格"""
    name: str
    value: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ProductInfo:
    """商品信息"""
    platform: str
    product_id: str
    url: str
    title: str = ""
    subtitle: str = ""
    price: float = 0.0
    original_price: float = 0.0
    currency: str = "CNY"
    brand: str = ""
    category: str = ""
    shop_name: str = ""
    shop_id: str = ""
    sales_count: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    stock: Optional[int] = None
    images: List[ProductImage] = field(default_factory=list)
    specs: List[ProductSpec] = field(default_factory=list)
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['scraped_at'] = self.scraped_at.isoformat()
        data['images'] = [img.to_dict() for img in self.images]
        data['specs'] = [spec.to_dict() for spec in self.specs]
        return data


class BaseProductScraper:
    """基础商品信息爬虫"""
    
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
            
    async def scrape_product(self, url: str) -> Optional[ProductInfo]:
        """抓取商品信息 - 子类需要实现"""
        raise NotImplementedError
        
    async def _scroll_page(self, page: Page, scroll_delay: float = 0.5):
        """滚动页面加载所有内容"""
        await self._helper.scroll_to_bottom(page, scroll_delay)
        
    def _extract_number(self, text: str) -> Optional[int]:
        """从文本中提取数字"""
        if not text:
            return None
        # 移除逗号、空格等
        text = text.replace(",", "").replace(" ", "")
        # 匹配数字
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        return None
        
    def _extract_price(self, text: str) -> float:
        """从文本中提取价格"""
        if not text:
            return 0.0
        match = re.search(r'[¥￥]?\s*(\d+(?:\.\d{1,2})?)', text)
        if match:
            return float(match.group(1))
        return 0.0


class TaobaoProductScraper(BaseProductScraper):
    """淘宝商品信息爬虫"""
    
    PLATFORM = "taobao"
    
    async def scrape_product(self, url: str) -> Optional[ProductInfo]:
        """抓取淘宝商品信息"""
        try:
            product_id = self._extract_product_id(url)
            if not product_id:
                logger.error(f"无法从URL提取商品ID: {url}")
                return None
                
            page = await self._helper.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            
            product = ProductInfo(
                platform=self.PLATFORM,
                product_id=product_id,
                url=url
            )
            
            # 获取标题
            product.title = await self._get_title(page)
            
            # 获取价格
            product.price = await self._get_price(page)
            product.original_price = await self._get_original_price(page)
            
            # 获取店铺信息
            shop_info = await self._get_shop_info(page)
            product.shop_name = shop_info.get("name", "")
            product.shop_id = shop_info.get("id", "")
            
            # 获取销量
            product.sales_count = await self._get_sales(page)
            
            # 获取图片
            product.images = await self._get_images(page, url)
            
            # 获取规格
            product.specs = await self._get_specs(page)
            
            # 获取详情
            product.description = await self._get_description(page)
            
            return product
            
        except Exception as e:
            logger.error(f"抓取淘宝商品信息失败: {url}, 错误: {e}")
            return None
            
    async def _get_title(self, page: Page) -> str:
        """获取商品标题"""
        selectors = [
            'h1[data-spm="1000983"]',
            '.tb-detail-hd h1',
            '[class*="ItemTitle"]',
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            except:
                continue
        return ""
        
    async def _get_price(self, page: Page) -> float:
        """获取价格"""
        selectors = [
            '.tb-rmb-num',
            '[class*="price"]',
            '.notranslate',
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    price = self._extract_price(text)
                    if price > 0:
                        return price
            except:
                continue
        return 0.0
        
    async def _get_original_price(self, page: Page) -> float:
        """获取原价"""
        try:
            element = await page.query_selector('.original-price')
            if element:
                text = await element.text_content()
                return self._extract_price(text)
        except:
            pass
        return 0.0
        
    async def _get_shop_info(self, page: Page) -> Dict[str, str]:
        """获取店铺信息"""
        result = {"name": "", "id": ""}
        try:
            # 店铺名
            shop_selectors = [
                '.shop-name a',
                '[class*="shop-name"]',
                '.shop-info .name',
            ]
            for selector in shop_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        result["name"] = text.strip()
                        break
        except:
            pass
        return result
        
    async def _get_sales(self, page: Page) -> Optional[int]:
        """获取销量"""
        try:
            selectors = [
                '[class*="sell-count"]',
                '.tb-count',
            ]
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    return self._extract_number(text)
        except:
            pass
        return None
        
    async def _get_images(self, page: Page, base_url: str) -> List[ProductImage]:
        """获取商品图片"""
        images = []
        try:
            # 主图
            img_selectors = [
                '#J_UlThumb li img',
                '.tb-pic img',
                '[class*="gallery"] img',
            ]
            for selector in img_selectors:
                elements = await page.query_selector_all(selector)
                for i, element in enumerate(elements):
                    try:
                        src = await element.get_attribute('src')
                        if src:
                            # 处理淘宝图片URL
                            if src.startswith('//'):
                                src = 'https:' + src
                            elif src.startswith('/'):
                                src = urljoin(base_url, src)
                            # 获取高清图
                            src = src.replace('_50x50.jpg', '')
                            src = src.replace('_60x60q90.jpg', '')
                            images.append(ProductImage(
                                url=src,
                                type="main" if i == 0 else "thumbnail"
                            ))
                    except:
                        continue
                if images:
                    break
        except Exception as e:
            logger.warning(f"获取图片失败: {e}")
        return images
        
    async def _get_specs(self, page: Page) -> List[ProductSpec]:
        """获取商品规格"""
        specs = []
        try:
            # 尝试获取属性列表
            spec_selectors = [
                '.attributes-list li',
                '[class*="attr-list"] li',
            ]
            for selector in spec_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        text = await element.text_content()
                        if ':' in text or '：' in text:
                            parts = re.split(r'[:：]', text, 1)
                            if len(parts) == 2:
                                specs.append(ProductSpec(
                                    name=parts[0].strip(),
                                    value=parts[1].strip()
                                ))
                    except:
                        continue
                if specs:
                    break
        except:
            pass
        return specs
        
    async def _get_description(self, page: Page) -> str:
        """获取商品详情"""
        try:
            # 滚动到详情区域
            await page.evaluate('''() => {
                const desc = document.querySelector('#description');
                if (desc) desc.scrollIntoView();
            }''')
            await asyncio.sleep(1)
            
            desc_selectors = [
                '#description',
                '.description',
                '[class*="detail-content"]',
            ]
            for selector in desc_selectors:
                element = await page.query_selector(selector)
                if element:
                    return await element.inner_html()
        except:
            pass
        return ""
        
    def _extract_product_id(self, url: str) -> Optional[str]:
        """提取商品ID"""
        match = re.search(r'id=(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'item/(\d+)', url)
        if match:
            return match.group(1)
        return None


class JDProductScraper(BaseProductScraper):
    """京东商品信息爬虫"""
    
    PLATFORM = "jd"
    
    async def scrape_product(self, url: str) -> Optional[ProductInfo]:
        """抓取京东商品信息"""
        try:
            product_id = self._extract_product_id(url)
            if not product_id:
                logger.error(f"无法从URL提取商品ID: {url}")
                return None
                
            page = await self._helper.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            
            product = ProductInfo(
                platform=self.PLATFORM,
                product_id=product_id,
                url=url
            )
            
            # 获取标题
            product.title = await self._get_title(page)
            
            # 获取价格
            product.price = await self._get_price(page)
            product.original_price = await self._get_original_price(page)
            
            # 获取店铺信息
            shop_info = await self._get_shop_info(page)
            product.shop_name = shop_info.get("name", "")
            
            # 获取评价信息
            rating_info = await self._get_rating(page)
            product.rating = rating_info.get("rating")
            product.review_count = rating_info.get("review_count")
            
            # 获取图片
            product.images = await self._get_images(page, url)
            
            # 获取规格
            product.specs = await self._get_specs(page)
            
            return product
            
        except Exception as e:
            logger.error(f"抓取京东商品信息失败: {url}, 错误: {e}")
            return None
            
    async def _get_title(self, page: Page) -> str:
        """获取标题"""
        selectors = [
            '.sku-name',
            '.product-intro .name',
            'h1',
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            except:
                continue
        return ""
        
    async def _get_price(self, page: Page) -> float:
        """获取价格"""
        try:
            # 从页面配置获取
            price = await page.evaluate('''() => {
                if (window.pageConfig && window.pageConfig.product) {
                    return window.pageConfig.product.price || 0;
                }
                return 0;
            }''')
            if price > 0:
                return float(price)
        except:
            pass
            
        # 从DOM获取
        selectors = [
            '.p-price .price',
            '.price-now .price',
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    price = self._extract_price(text)
                    if price > 0:
                        return price
            except:
                continue
        return 0.0
        
    async def _get_original_price(self, page: Page) -> float:
        """获取原价"""
        try:
            element = await page.query_selector('.p-price .del')
            if element:
                text = await element.text_content()
                return self._extract_price(text)
        except:
            pass
        return 0.0
        
    async def _get_shop_info(self, page: Page) -> Dict[str, str]:
        """获取店铺信息"""
        result = {"name": ""}
        try:
            selectors = [
                '.shop-name',
                '.seller a',
                '[class*="shop"]',
            ]
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        result["name"] = text.strip()
                        break
        except:
            pass
        return result
        
    async def _get_rating(self, page: Page) -> Dict[str, Any]:
        """获取评价信息"""
        result = {"rating": None, "review_count": None}
        try:
            # 评分
            rating_element = await page.query_selector('.score-num')
            if rating_element:
                text = await rating_element.text_content()
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    result["rating"] = float(match.group(1))
                    
            # 评价数
            comment_element = await page.query_selector('#comment-count a')
            if comment_element:
                text = await comment_element.text_content()
                result["review_count"] = self._extract_number(text)
        except:
            pass
        return result
        
    async def _get_images(self, page: Page, base_url: str) -> List[ProductImage]:
        """获取图片"""
        images = []
        try:
            img_selectors = [
                '#spec-list img',
                '.lh img',
            ]
            for selector in img_selectors:
                elements = await page.query_selector_all(selector)
                for i, element in enumerate(elements):
                    try:
                        src = await element.get_attribute('src')
                        if src:
                            if src.startswith('//'):
                                src = 'https:' + src
                            elif src.startswith('/'):
                                src = urljoin(base_url, src)
                            # 获取大图
                            src = src.replace('/n5/', '/n1/')
                            src = src.replace('/s54x54_', '/s450x450_')
                            images.append(ProductImage(
                                url=src,
                                type="main" if i == 0 else "thumbnail"
                            ))
                    except:
                        continue
                if images:
                    break
        except:
            pass
        return images
        
    async def _get_specs(self, page: Page) -> List[ProductSpec]:
        """获取规格"""
        specs = []
        try:
            spec_elements = await page.query_selector_all('#detail .Ptable .Ptable-item')
            for element in spec_elements:
                try:
                    name_el = await element.query_selector('.name')
                    value_el = await element.query_selector('.value')
                    if name_el and value_el:
                        name = await name_el.text_content()
                        value = await value_el.text_content()
                        specs.append(ProductSpec(
                            name=name.strip(),
                            value=value.strip()
                        ))
                except:
                    continue
        except:
            pass
        return specs
        
    def _extract_product_id(self, url: str) -> Optional[str]:
        """提取商品ID"""
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)
        match = re.search(r'sku[Ii]d=(\d+)', url)
        if match:
            return match.group(1)
        return None


class PDDProductScraper(BaseProductScraper):
    """拼多多商品信息爬虫"""
    
    PLATFORM = "pdd"
    
    async def scrape_product(self, url: str) -> Optional[ProductInfo]:
        """抓取拼多多商品信息"""
        try:
            product_id = self._extract_product_id(url)
            if not product_id:
                logger.error(f"无法从URL提取商品ID: {url}")
                return None
                
            page = await self._helper.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)  # 拼多多加载较慢
            
            product = ProductInfo(
                platform=self.PLATFORM,
                product_id=product_id,
                url=url
            )
            
            # 获取标题
            product.title = await self._get_title(page)
            
            # 获取价格
            product.price = await self._get_price(page)
            
            # 获取销量
            product.sales_count = await self._get_sales(page)
            
            # 获取图片
            product.images = await self._get_images(page, url)
            
            return product
            
        except Exception as e:
            logger.error(f"抓取拼多多商品信息失败: {url}, 错误: {e}")
            return None
            
    async def _get_title(self, page: Page) -> str:
        """获取标题"""
        selectors = [
            '[class*="goods-name"]',
            '[class*="title"]',
            'h1',
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            except:
                continue
        return ""
        
    async def _get_price(self, page: Page) -> float:
        """获取价格"""
        selectors = [
            '[class*="price"]',
            '[class*="_price"]',
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    price = self._extract_price(text)
                    if price > 0:
                        return price
            except:
                continue
        return 0.0
        
    async def _get_sales(self, page: Page) -> Optional[int]:
        """获取销量"""
        try:
            selectors = [
                '[class*="sales"]',
            ]
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    return self._extract_number(text)
        except:
            pass
        return None
        
    async def _get_images(self, page: Page, base_url: str) -> List[ProductImage]:
        """获取图片"""
        images = []
        try:
            img_selectors = [
                '[class*="gallery"] img',
                '[class*="swiper"] img',
            ]
            for selector in img_selectors:
                elements = await page.query_selector_all(selector)
                for i, element in enumerate(elements):
                    try:
                        src = await element.get_attribute('src')
                        if src:
                            if src.startswith('//'):
                                src = 'https:' + src
                            images.append(ProductImage(
                                url=src,
                                type="main" if i == 0 else "thumbnail"
                            ))
                    except:
                        continue
                if images:
                    break
        except:
            pass
        return images
        
    def _extract_product_id(self, url: str) -> Optional[str]:
        """提取商品ID"""
        match = re.search(r'goods_id=(\d+)', url)
        if match:
            return match.group(1)
        return None


class ProductInfoManager:
    """商品信息管理器"""
    
    def __init__(
        self,
        anti_detection: Optional[AntiDetectionManager] = None,
        headless: bool = True
    ):
        self.anti_detection = anti_detection or create_anti_detection_manager()
        self.headless = headless
        self._scrapers: Dict[str, BaseProductScraper] = {}
        
    def _get_scraper(self, platform: str) -> BaseProductScraper:
        """获取或创建爬虫"""
        if platform not in self._scrapers:
            if platform == "taobao":
                self._scrapers[platform] = TaobaoProductScraper(
                    self.anti_detection,
                    self.headless
                )
            elif platform == "jd":
                self._scrapers[platform] = JDProductScraper(
                    self.anti_detection,
                    self.headless
                )
            elif platform == "pdd":
                self._scrapers[platform] = PDDProductScraper(
                    self.anti_detection,
                    self.headless
                )
            else:
                raise ValueError(f"不支持的平台: {platform}")
        return self._scrapers[platform]
        
    def _detect_platform(self, url: str) -> Optional[str]:
        """检测平台"""
        if "taobao.com" in url or "tmall.com" in url:
            return "taobao"
        elif "jd.com" in url:
            return "jd"
        elif "pinduoduo.com" in url or "yangkeduo.com" in url:
            return "pdd"
        return None
        
    async def scrape_product(self, url: str) -> Optional[ProductInfo]:
        """抓取单个商品"""
        platform = self._detect_platform(url)
        if not platform:
            logger.error(f"无法识别平台: {url}")
            return None
            
        scraper = self._get_scraper(platform)
        
        if not scraper._helper:
            await scraper.start()
            
        return await scraper.scrape_product(url)
        
    async def scrape_products(self, urls: List[str]) -> List[ProductInfo]:
        """批量抓取商品"""
        results = []
        for url in urls:
            try:
                product = await self.scrape_product(url)
                if product:
                    results.append(product)
            except Exception as e:
                logger.error(f"抓取商品失败: {url}, 错误: {e}")
        return results
        
    async def close(self):
        """关闭所有爬虫"""
        for scraper in self._scrapers.values():
            await scraper.close()
        self._scrapers.clear()
