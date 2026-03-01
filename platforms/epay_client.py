#!/usr/bin/env python3
"""
电商系统 API 客户端
对接 https://epay.alizzy.com/outside/25/
"""
import hashlib
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class APIConfig:
    """API 配置"""
    base_url: str = "https://epay.alizzy.com/outside/25"
    app_id: str = ""
    app_secret: str = ""
    timeout: int = 30

class EPayAPIClient:
    """电商支付系统 API 客户端"""
    
    def __init__(self, config: APIConfig):
        self.config = config
    
    def _generate_sign(self, params: Dict) -> str:
        """生成 API 签名"""
        # 按 key 排序
        sorted_params = sorted(params.items())
        
        # 拼接字符串
        sign_str = self.config.app_secret
        for k, v in sorted_params:
            sign_str += f"{k}{v}"
        sign_str += self.config.app_secret
        
        # MD5 加密
        return hashlib.md5(sign_str.encode()).hexdigest().upper()
    
    def _build_params(self, **kwargs) -> Dict:
        """构建请求参数"""
        params = {
            "app_id": self.config.app_id,
            "timestamp": str(int(time.time())),
            "nonce": hashlib.md5(str(time.time()).encode()).hexdigest()[:16],
            **kwargs
        }
        
        # 添加签名
        params["sign"] = self._generate_sign(params)
        
        return params
    
    async def _request(self, endpoint: str, params: Dict = None, method: str = "POST") -> Dict:
        """发送 HTTP 请求"""
        url = f"{self.config.base_url}/{endpoint}"
        
        if params is None:
            params = {}
        
        # 构建完整参数
        request_params = self._build_params(**params)
        
        try:
            if method == "GET":
                query_string = urllib.parse.urlencode(request_params)
                full_url = f"{url}?{query_string}"
                req = urllib.request.Request(full_url, method="GET")
            else:
                data = json.dumps(request_params).encode('utf-8')
                req = urllib.request.Request(
                    url,
                    data=data,
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
    
    # ============ 订单相关接口 ============
    
    async def get_orders(self, start_time: str, end_time: str, 
                        page: int = 1, page_size: int = 20) -> Dict:
        """
        获取订单列表
        
        Args:
            start_time: 开始时间，格式：2026-03-01 00:00:00
            end_time: 结束时间，格式：2026-03-01 23:59:59
            page: 页码
            page_size: 每页数量
        """
        return await self._request("order/list", {
            "start_time": start_time,
            "end_time": end_time,
            "page": page,
            "page_size": page_size
        })
    
    async def get_order_detail(self, order_no: str) -> Dict:
        """获取订单详情"""
        return await self._request("order/detail", {
            "order_no": order_no
        })
    
    async def update_order_status(self, order_no: str, status: str, 
                                  remark: str = "") -> Dict:
        """
        更新订单状态
        
        Args:
            order_no: 订单号
            status: 状态（paid/shipped/completed/cancelled）
            remark: 备注
        """
        return await self._request("order/update_status", {
            "order_no": order_no,
            "status": status,
            "remark": remark
        })
    
    async def ship_order(self, order_no: str, tracking_no: str, 
                        carrier: str, carrier_name: str = "") -> Dict:
        """
        订单发货
        
        Args:
            order_no: 订单号
            tracking_no: 快递单号
            carrier: 快递公司代码（sf/jd/yto/zto/ems）
            carrier_name: 快递公司名称
        """
        return await self._request("order/ship", {
            "order_no": order_no,
            "tracking_no": tracking_no,
            "carrier": carrier,
            "carrier_name": carrier_name
        })
    
    # ============ 商品相关接口 ============
    
    async def get_products(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取商品列表"""
        return await self._request("product/list", {
            "page": page,
            "page_size": page_size
        })
    
    async def get_product_detail(self, sku: str) -> Dict:
        """获取商品详情"""
        return await self._request("product/detail", {
            "sku": sku
        })
    
    async def update_stock(self, sku: str, quantity: int, 
                          warehouse_id: str = "") -> Dict:
        """
        更新库存
        
        Args:
            sku: 商品 SKU
            quantity: 库存数量
            warehouse_id: 仓库 ID（可选）
        """
        params = {
            "sku": sku,
            "quantity": quantity
        }
        if warehouse_id:
            params["warehouse_id"] = warehouse_id
        
        return await self._request("product/update_stock", params)
    
    async def update_price(self, sku: str, price: float, 
                          original_price: float = None) -> Dict:
        """
        更新价格
        
        Args:
            sku: 商品 SKU
            price: 售价
            original_price: 原价（可选）
        """
        params = {
            "sku": sku,
            "price": price
        }
        if original_price:
            params["original_price"] = original_price
        
        return await self._request("product/update_price", params)
    
    # ============ 退款相关接口 ============
    
    async def refund_order(self, order_no: str, amount: float, 
                          reason: str, refund_type: str = "full") -> Dict:
        """
        申请退款
        
        Args:
            order_no: 订单号
            amount: 退款金额
            reason: 退款原因
            refund_type: 退款类型（full-全额/partial-部分）
        """
        return await self._request("refund/apply", {
            "order_no": order_no,
            "amount": amount,
            "reason": reason,
            "refund_type": refund_type
        })
    
    async def get_refund_list(self, start_time: str, end_time: str,
                             status: str = "", page: int = 1) -> Dict:
        """获取退款列表"""
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "page": page
        }
        if status:
            params["status"] = status
        
        return await self._request("refund/list", params)
    
    # ============ 数据统计接口 ============
    
    async def get_daily_report(self, date: str) -> Dict:
        """
        获取日报数据
        
        Args:
            date: 日期，格式：2026-03-01
        """
        return await self._request("report/daily", {
            "date": date
        })
    
    async def get_order_statistics(self, start_time: str, end_time: str) -> Dict:
        """获取订单统计"""
        return await self._request("report/order_stats", {
            "start_time": start_time,
            "end_time": end_time
        })
    
    async def get_sales_ranking(self, start_time: str, end_time: str,
                                top: int = 10) -> Dict:
        """获取销售排行"""
        return await self._request("report/sales_ranking", {
            "start_time": start_time,
            "end_time": end_time,
            "top": top
        })

# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def test():
        # 配置
        config = APIConfig(
            app_id="2026021502557128",
            app_secret="E59CA750B7BF3950171C314D83F6995B"
        )
        
        # 创建客户端
        client = EPayAPIClient(config)
        
        # 测试获取订单列表
        result = await client.get_orders(
            start_time="2026-03-01 00:00:00",
            end_time="2026-03-01 23:59:59"
        )
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
