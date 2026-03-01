#!/usr/bin/env python3
"""
喵呜商城 API 客户端
基于文档: 订单API的功能和接口
接口地址: https://epay.alizzy.com/outside/{uniacid}/
"""
import hashlib
import hmac
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MallAPIConfig:
    """商城 API 配置"""
    base_url: str = "https://epay.alizzy.com"
    uniacid: str = "25"  # 从URL中提取
    app_id: str = ""
    app_secret: str = ""
    timeout: int = 30
    enable_sign: bool = True  # 是否开启签名验证

class MallAPIClient:
    """喵呜商城 API 客户端"""
    
    # 订单状态映射
    ORDER_STATUS = {
        0: "待付款",
        1: "待发货",
        2: "待收货",
        3: "已完成",
        -1: "已关闭"
    }
    
    def __init__(self, config: MallAPIConfig):
        self.config = config
        self.base_url = f"{config.base_url}/outside/{config.uniacid}"
    
    def _generate_sign(self, params: Dict) -> str:
        """
        生成 HMAC-SHA256 签名
        
        算法:
        1. 将所有参数按字典序排序
        2. 拼接参数字符串（排除sign参数）: key1=value1&key2=value2
        3. 使用 HMAC-SHA256 生成签名
        """
        if not self.config.enable_sign:
            return ""
        
        # 过滤参数：排除 sign，将所有值转为字符串
        filtered_params = {}
        for k, v in params.items():
            if k == "sign":
                continue
            if v is not None:
                # 将值转为字符串
                if isinstance(v, (list, dict)):
                    # JSON 数组/对象需要转为 JSON 字符串
                    filtered_params[k] = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
                else:
                    filtered_params[k] = str(v)
        
        # 按 key 排序
        sorted_params = sorted(filtered_params.items())
        
        # 拼接字符串
        query_parts = []
        for k, v in sorted_params:
            query_parts.append(f"{k}={v}")
        
        query_string = "&".join(query_parts)
        
        print(f"  [DEBUG] 签名字符串: {query_string[:200]}...")  # 调试用，限制长度
        
        # HMAC-SHA256 签名
        sign = hmac.new(
            self.config.app_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        print(f"  [DEBUG] 生成签名: {sign[:16]}...")  # 调试用
        
        return sign
    
    def _build_params(self, **kwargs) -> Dict:
        """构建请求参数"""
        params = {
            "app_id": self.config.app_id,
            **kwargs
        }
        
        # 添加签名
        if self.config.enable_sign:
            params["sign"] = self._generate_sign(params)
        
        return params
    
    async def _request(self, endpoint: str, params: Dict = None, 
                      method: str = "POST", data: Dict = None) -> Dict:
        """发送 HTTP 请求"""
        url = f"{self.base_url}/{endpoint}"
        
        # 构建参数
        if params is None:
            params = {}
        
        request_params = self._build_params(**params)
        
        try:
            if method == "GET":
                # GET 请求
                query_string = urllib.parse.urlencode(request_params)
                full_url = f"{url}?{query_string}"
                req = urllib.request.Request(full_url, method="GET")
            else:
                # POST 请求
                if data:
                    # POST JSON 数据
                    post_data = json.dumps({**request_params, **data}).encode('utf-8')
                else:
                    post_data = json.dumps(request_params).encode('utf-8')
                
                req = urllib.request.Request(
                    url,
                    data=post_data,
                    headers={'Content-Type': 'application/json'},
                    method="POST"
                )
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
                
        except urllib.error.HTTPError as e:
            return {
                "result": -1,
                "msg": f"HTTP Error: {e.code}",
                "data": {}
            }
        except Exception as e:
            return {
                "result": -1,
                "msg": f"Request Error: {str(e)}",
                "data": {}
            }
    
    # ============ 订单计算接口 ============
    
    async def calculate_order(self, uid: int, goods: List[Dict]) -> Dict:
        """
        计算订单信息
        
        接口: POST /outside/{uniacid}/order/buy
        功能: 计算订单价格，返回订单详情但不创建订单
        
        Args:
            uid: 会员ID
            goods: 商品列表 [{"goods_id": 1, "option_id": 10, "total": 2}]
        """
        return await self._request("order/buy", data={
            "uid": uid,
            "goods": goods
        })
    
    # ============ 订单创建接口 ============
    
    async def create_order(self, outside_sn: str, uid: int, 
                          goods: List[Dict]) -> Dict:
        """
        创建订单
        
        接口: POST /outside/{uniacid}/order/create
        功能: 创建订单并返回订单信息，支持一个请求创建多个订单
        
        Args:
            outside_sn: 第三方订单号（必须唯一）
            uid: 会员ID
            goods: 商品列表
        
        Returns:
            {
                "result": 1,
                "msg": "成功",
                "data": {
                    "outside_sn": "...",
                    "trade_sn": "...",
                    "pay_link": "...",
                    "orders": [{"order_id": 123, "order_sn": "..."}]
                }
            }
        """
        return await self._request("order/create", data={
            "outside_sn": outside_sn,
            "uid": uid,
            "goods": goods
        })
    
    # ============ 订单查询接口 ============
    
    async def get_order_list(self, uid: Optional[int] = None,
                            create_time: Optional[str] = None,
                            plugin_type: Optional[str] = None) -> Dict:
        """
        获取订单列表（不分页）
        
        接口: GET /outside/{uniacid}/order/list
        
        Args:
            uid: 会员ID（可选）
            create_time: 创建时间，格式：2026-01-01 00:00:00（可选）
            plugin_type: 插件类型，如 "0,1,2"（可选）
        """
        params = {}
        if uid:
            params["uid"] = uid
        if create_time:
            params["create_time"] = create_time
        if plugin_type:
            params["plugin_type"] = plugin_type
        
        return await self._request("order/list", params=params, method="GET")
    
    async def get_order_page(self, uid: Optional[int] = None,
                            mobile: Optional[str] = None,
                            contact_phone: Optional[str] = None,
                            create_time: Optional[str] = None,
                            plugin_type: Optional[str] = None) -> Dict:
        """
        分页查询订单列表
        
        接口: GET /outside/{uniacid}/order/page
        
        Args:
            uid: 会员ID（可选）
            mobile: 手机号（可选）
            contact_phone: 联系电话（可选）
            create_time: 创建时间（可选）
            plugin_type: 插件类型（可选）
        """
        params = {}
        if uid:
            params["uid"] = uid
        if mobile:
            params["mobile"] = mobile
        if contact_phone:
            params["contact_phone"] = contact_phone
        if create_time:
            params["create_time"] = create_time
        if plugin_type:
            params["plugin_type"] = plugin_type
        
        return await self._request("order/page", params=params, method="GET")
    
    # ============ 订单操作接口 ============
    
    async def pay_order(self, outside_sn: str) -> Dict:
        """
        订单支付
        
        接口: POST /outside/{uniacid}/order/pay
        功能: 后台支付订单
        
        Args:
            outside_sn: 第三方订单号
        """
        return await self._request("order/pay", data={
            "outside_sn": outside_sn
        })
    
    async def ship_order(self, outside_sn: str, express_code: str, 
                        express_sn: str) -> Dict:
        """
        订单发货
        
        接口: POST /outside/{uniacid}/order/send
        
        Args:
            outside_sn: 第三方订单号
            express_code: 快递公司编码（如 SF、YTO、ZTO）
            express_sn: 快递单号
        """
        return await self._request("order/send", data={
            "outside_sn": outside_sn,
            "express_code": express_code,
            "express_sn": express_sn
        })
    
    async def receive_order(self, outside_sn: str) -> Dict:
        """
        订单收货确认
        
        接口: POST /outside/{uniacid}/order/receive
        
        Args:
            outside_sn: 第三方订单号
        """
        return await self._request("order/receive", data={
            "outside_sn": outside_sn
        })
    
    async def close_refund(self, outside_sn: str) -> Dict:
        """
        订单退款并关闭
        
        接口: POST /outside/{uniacid}/order/closeRefund
        
        Args:
            outside_sn: 第三方订单号
        """
        return await self._request("order/closeRefund", data={
            "outside_sn": outside_sn
        })
    
    # ============ 辅助方法 ============
    
    def get_status_text(self, status_code: int) -> str:
        """获取订单状态文本"""
        return self.ORDER_STATUS.get(status_code, "未知状态")
    
    def generate_outside_sn(self) -> str:
        """生成第三方订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(int(time.time() * 1000))[-4:]
        return f"OUT{timestamp}{random_suffix}"

# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def test():
        # 配置
        config = MallAPIConfig(
            app_id="2026021502557128",
            app_secret="E59CA750B7BF3950171C314D83F6995B",
            uniacid="25"
        )
        
        # 创建客户端
        client = MallAPIClient(config)
        
        # 1. 计算订单
        calculate_result = await client.calculate_order(
            uid=123,
            goods=[
                {"goods_id": 1, "option_id": 10, "total": 2}
            ]
        )
        print("计算订单:", json.dumps(calculate_result, indent=2, ensure_ascii=False))
        
        # 2. 创建订单
        outside_sn = client.generate_outside_sn()
        create_result = await client.create_order(
            outside_sn=outside_sn,
            uid=123,
            goods=[
                {"goods_id": 1, "option_id": 10, "total": 2}
            ]
        )
        print("创建订单:", json.dumps(create_result, indent=2, ensure_ascii=False))
        
        # 3. 查询订单列表
        list_result = await client.get_order_list()
        print("订单列表:", json.dumps(list_result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
