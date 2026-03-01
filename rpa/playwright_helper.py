"""
Playwright Helper - Playwright 封装模块
提供统一的浏览器实例管理和页面操作封装
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = True
    slow_mo: int = 0
    viewport: Dict[str, int] = None
    user_agent: Optional[str] = None
    proxy: Optional[Dict[str, str]] = None
    locale: str = "zh-CN"
    timezone_id: str = "Asia/Shanghai"
    
    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}


class PlaywrightHelper:
    """Playwright 封装类"""
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pages: List[Page] = []
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """启动 Playwright"""
        self._playwright = await async_playwright().start()
        return self
        
    async def close(self):
        """关闭所有资源"""
        for page in self._pages:
            try:
                await page.close()
            except:
                pass
        self._pages = []
        
        if self._context:
            await self._context.close()
            self._context = None
            
        if self._browser:
            await self._browser.close()
            self._browser = None
            
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            
    async def launch_browser(self, browser_type: str = "chromium") -> Browser:
        """启动浏览器"""
        if not self._playwright:
            await self.start()
            
        browser_launcher = getattr(self._playwright, browser_type)
        
        launch_options = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo,
        }
        
        if self.config.proxy:
            launch_options["proxy"] = self.config.proxy
            
        self._browser = await browser_launcher.launch(**launch_options)
        return self._browser
        
    async def new_context(self, **kwargs) -> BrowserContext:
        """创建新的浏览器上下文"""
        if not self._browser:
            await self.launch_browser()
            
        context_options = {
            "viewport": self.config.viewport,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
        }
        
        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent
            
        context_options.update(kwargs)
        
        self._context = await self._browser.new_context(**context_options)
        
        # 注入反检测脚本
        await self._inject_anti_detection()
        
        return self._context
        
    async def new_page(self, **kwargs) -> Page:
        """创建新页面"""
        if not self._context:
            await self.new_context()
            
        page = await self._context.new_page(**kwargs)
        self._pages.append(page)
        return page
        
    async def _inject_anti_detection(self):
        """注入反检测脚本"""
        if not self._context:
            return
            
        # 覆盖 navigator.webdriver 等检测点
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 覆盖 canvas 指纹
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (this.width === 0 || this.height === 0) {
                    return originalToDataURL.call(this, type);
                }
                const ctx = this.getContext('2d');
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                // 添加轻微噪声
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + (Math.random() - 0.5) * 2));
                }
                ctx.putImageData(imageData, 0, 0);
                return originalToDataURL.call(this, type);
            };
        """)
        
    async def goto(self, url: str, wait_until: str = "networkidle", timeout: int = 30000) -> Page:
        """导航到指定 URL"""
        page = await self.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout)
        return page
        
    async def safe_click(self, page: Page, selector: str, timeout: int = 10000):
        """安全点击元素"""
        await page.wait_for_selector(selector, timeout=timeout)
        await page.click(selector)
        
    async def safe_fill(self, page: Page, selector: str, value: str, timeout: int = 10000):
        """安全填充输入框"""
        await page.wait_for_selector(selector, timeout=timeout)
        await page.fill(selector, value)
        
    async def safe_evaluate(self, page: Page, expression: str, timeout: int = 10000):
        """安全执行 JS"""
        return await page.evaluate(expression)
        
    async def scroll_to_bottom(self, page: Page, delay: float = 0.5):
        """滚动到页面底部"""
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        
                        if (totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        await asyncio.sleep(delay)
        
    async def wait_for_ajax(self, page: Page, timeout: int = 30000):
        """等待 AJAX 请求完成"""
        await page.wait_for_load_state("networkidle", timeout=timeout)
        
    async def intercept_requests(self, page: Page, url_pattern: str, handler: Callable):
        """拦截请求"""
        await page.route(url_pattern, handler)
        
    async def get_cookies(self) -> List[Dict]:
        """获取当前上下文的所有 cookies"""
        if self._context:
            return await self._context.cookies()
        return []
        
    async def set_cookies(self, cookies: List[Dict]):
        """设置 cookies"""
        if self._context:
            await self._context.add_cookies(cookies)
            
    async def save_storage_state(self, path: str):
        """保存存储状态"""
        if self._context:
            await self._context.storage_state(path=path)
            
    async def load_storage_state(self, path: str):
        """加载存储状态"""
        if not self._browser:
            await self.launch_browser()
        self._context = await self._browser.new_context(storage_state=path)


class PagePool:
    """页面池 - 用于并发抓取"""
    
    def __init__(self, helper: PlaywrightHelper, max_pages: int = 5):
        self.helper = helper
        self.max_pages = max_pages
        self._semaphore = asyncio.Semaphore(max_pages)
        self._pages: asyncio.Queue = asyncio.Queue()
        
    async def initialize(self):
        """初始化页面池"""
        for _ in range(self.max_pages):
            page = await self.helper.new_page()
            await self._pages.put(page)
            
    async def acquire(self) -> Page:
        """获取页面"""
        async with self._semaphore:
            return await self._pages.get()
            
    async def release(self, page: Page):
        """释放页面"""
        await self._pages.put(page)
        
    @asynccontextmanager
    async def get_page(self):
        """上下文管理器获取页面"""
        page = await self.acquire()
        try:
            yield page
        finally:
            await self.release(page)
            
    async def close_all(self):
        """关闭所有页面"""
        while not self._pages.empty():
            page = await self._pages.get()
            try:
                await page.close()
            except:
                pass


# 便捷函数
async def create_browser(
    headless: bool = True,
    user_agent: Optional[str] = None,
    proxy: Optional[Dict[str, str]] = None
) -> PlaywrightHelper:
    """创建浏览器实例的便捷函数"""
    config = BrowserConfig(
        headless=headless,
        user_agent=user_agent,
        proxy=proxy
    )
    helper = PlaywrightHelper(config)
    await helper.start()
    await helper.launch_browser()
    return helper
