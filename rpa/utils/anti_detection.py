"""
Anti-Detection Utils - 反检测工具模块
提供 User-Agent 轮换、代理 IP 池、请求频率控制等功能
"""

import random
import time
import asyncio
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


# 常用 User-Agent 列表
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class UserAgentRotator:
    """User-Agent 轮换器"""
    
    def __init__(self, user_agents: Optional[List[str]] = None):
        self.user_agents = user_agents or USER_AGENTS.copy()
        self._used_agents: deque = deque(maxlen=10)
        
    def get_random(self) -> str:
        """获取随机 User-Agent"""
        available = [ua for ua in self.user_agents if ua not in self._used_agents]
        if not available:
            available = self.user_agents
            
        ua = random.choice(available)
        self._used_agents.append(ua)
        return ua
        
    def get_by_index(self, index: int) -> str:
        """通过索引获取 User-Agent"""
        return self.user_agents[index % len(self.user_agents)]
        
    def add_user_agent(self, user_agent: str):
        """添加自定义 User-Agent"""
        if user_agent not in self.user_agents:
            self.user_agents.append(user_agent)
            
    def remove_user_agent(self, user_agent: str):
        """移除 User-Agent"""
        if user_agent in self.user_agents:
            self.user_agents.remove(user_agent)


@dataclass
class Proxy:
    """代理配置"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
        
    @property
    def playwright_proxy(self) -> Dict[str, str]:
        """获取 Playwright 格式的代理配置"""
        proxy = {
            "server": self.url,
        }
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy


class ProxyPool:
    """代理 IP 池"""
    
    def __init__(self, proxies: Optional[List[Proxy]] = None):
        self.proxies: List[Proxy] = proxies or []
        self._failed_proxies: set = set()
        self._current_index = 0
        self._lock = asyncio.Lock()
        
    def add_proxy(self, proxy: Proxy):
        """添加代理"""
        self.proxies.append(proxy)
        
    def add_proxies_from_list(self, proxy_list: List[str]):
        """从字符串列表添加代理
        格式: host:port 或 protocol://host:port 或 protocol://user:pass@host:port
        """
        for proxy_str in proxy_list:
            proxy = self._parse_proxy_string(proxy_str)
            if proxy:
                self.add_proxy(proxy)
                
    def _parse_proxy_string(self, proxy_str: str) -> Optional[Proxy]:
        """解析代理字符串"""
        try:
            # protocol://user:pass@host:port
            if "://" in proxy_str:
                protocol, rest = proxy_str.split("://", 1)
                if "@" in rest:
                    auth, host_port = rest.split("@", 1)
                    username, password = auth.split(":", 1)
                else:
                    username = password = None
                    host_port = rest
            else:
                protocol = "http"
                username = password = None
                host_port = proxy_str
                
            host, port = host_port.rsplit(":", 1)
            return Proxy(
                host=host,
                port=int(port),
                username=username,
                password=password,
                protocol=protocol
            )
        except Exception as e:
            logger.warning(f"Failed to parse proxy string: {proxy_str}, error: {e}")
            return None
            
    async def get_proxy(self) -> Optional[Proxy]:
        """获取一个可用代理"""
        async with self._lock:
            available = [p for p in self.proxies if p not in self._failed_proxies]
            if not available:
                # 重置失败列表
                self._failed_proxies.clear()
                available = self.proxies
                
            if not available:
                return None
                
            proxy = available[self._current_index % len(available)]
            self._current_index += 1
            return proxy
            
    def mark_failed(self, proxy: Proxy):
        """标记代理为失败"""
        self._failed_proxies.add(proxy)
        logger.warning(f"Proxy marked as failed: {proxy.host}:{proxy.port}")
        
    def get_proxy_count(self) -> int:
        """获取代理数量"""
        return len(self.proxies)
        
    def get_available_count(self) -> int:
        """获取可用代理数量"""
        return len(self.proxies) - len(self._failed_proxies)


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(
        self,
        requests_per_second: float = 1.0,
        burst_size: int = 1,
        min_delay: float = 1.0,
        max_delay: float = 5.0
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        self._tokens = burst_size
        self._last_update = time.time()
        self._lock = asyncio.Lock()
        self._request_times: deque = deque(maxlen=100)
        
    async def acquire(self):
        """获取请求许可"""
        async with self._lock:
            now = time.time()
            
            # 更新令牌
            elapsed = now - self._last_update
            self._tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.requests_per_second
            )
            self._last_update = now
            
            # 等待直到有可用令牌
            while self._tokens < 1:
                wait_time = (1 - self._tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)
                
                now = time.time()
                elapsed = now - self._last_update
                self._tokens = min(
                    self.burst_size,
                    self._tokens + elapsed * self.requests_per_second
                )
                self._last_update = now
                
            self._tokens -= 1
            self._request_times.append(now)
            
    async def wait(self):
        """等待随机延迟"""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        
    def get_stats(self) -> Dict:
        """获取统计信息"""
        now = time.time()
        recent_requests = sum(1 for t in self._request_times if now - t < 60)
        return {
            "recent_requests_per_minute": recent_requests,
            "available_tokens": self._tokens,
            "total_requests": len(self._request_times)
        }


class AntiDetectionManager:
    """反检测管理器 - 整合所有反检测功能"""
    
    def __init__(
        self,
        user_agents: Optional[List[str]] = None,
        proxies: Optional[List[Proxy]] = None,
        requests_per_second: float = 1.0,
        min_delay: float = 1.0,
        max_delay: float = 5.0
    ):
        self.ua_rotator = UserAgentRotator(user_agents)
        self.proxy_pool = ProxyPool(proxies)
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            min_delay=min_delay,
            max_delay=max_delay
        )
        
    async def get_session_config(self) -> Dict:
        """获取会话配置"""
        await self.rate_limiter.acquire()
        await self.rate_limiter.wait()
        
        config = {
            "user_agent": self.ua_rotator.get_random(),
        }
        
        proxy = await self.proxy_pool.get_proxy()
        if proxy:
            config["proxy"] = proxy.playwright_proxy
            
        return config
        
    def mark_proxy_failed(self, proxy_config: Dict):
        """标记代理失败"""
        # 从配置中查找对应的代理对象
        server = proxy_config.get("server", "")
        for proxy in self.proxy_pool.proxies:
            if proxy.url == server or f"{proxy.host}:{proxy.port}" in server:
                self.proxy_pool.mark_failed(proxy)
                break
                
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "user_agents_count": len(self.ua_rotator.user_agents),
            "proxies_total": self.proxy_pool.get_proxy_count(),
            "proxies_available": self.proxy_pool.get_available_count(),
            "rate_limiter": self.rate_limiter.get_stats()
        }


# 浏览器指纹随机化
def get_random_viewport() -> Dict[str, int]:
    """获取随机视口尺寸"""
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1280, "height": 720},
        {"width": 1680, "height": 1050},
    ]
    return random.choice(viewports)


def get_random_timezone() -> str:
    """获取随机时区"""
    timezones = [
        "Asia/Shanghai",
        "Asia/Hong_Kong",
        "Asia/Tokyo",
        "Asia/Seoul",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
    ]
    return random.choice(timezones)


def get_random_locale() -> str:
    """获取随机语言环境"""
    locales = [
        "zh-CN",
        "zh-HK",
        "en-US",
        "en-GB",
        "ja-JP",
        "ko-KR",
    ]
    return random.choice(locales)


# 便捷函数
def create_anti_detection_manager(
    proxy_list: Optional[List[str]] = None,
    requests_per_second: float = 1.0
) -> AntiDetectionManager:
    """创建反检测管理器的便捷函数"""
    manager = AntiDetectionManager(
        requests_per_second=requests_per_second
    )
    
    if proxy_list:
        manager.proxy_pool.add_proxies_from_list(proxy_list)
        
    return manager
