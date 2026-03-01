"""
订单管理 API 路由
"""
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Query, Path, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

router = APIRouter()


# ============================================
# 枚举类型
# ============================================

class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"       # 待付款
    PAID = "paid"             # 已付款
    PROCESSING = "processing" # 处理中
    SHIPPED = "shipped"       # 已发货
    DELIVERED = "delivered"   # 已送达
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"     # 已退款


class PaymentStatus(str, Enum):
    """支付状态"""
    UNPAID = "unpaid"         # 未支付
    PAID = "paid"             # 已支付
    PARTIAL = "partial"       # 部分支付
    REFUNDED = "refunded"     # 已退款
    FAILED = "failed"         # 支付失败


class ShippingStatus(str, Enum):
    """物流状态"""
    UNSHIPPED = "unshipped"   # 未发货
    PARTIAL = "partial"       # 部分发货
    SHIPPED = "shipped"       # 已发货
    DELIVERED = "delivered"   # 已签收


# ============================================
# Pydantic 模型定义
# ============================================

class OrderItemRequest(BaseModel):
    """订单商品请求"""
    product_id: int = Field(..., ge=1, description="商品ID")
    variant_id: Optional[int] = Field(None, ge=1, description="规格ID")
    quantity: int = Field(..., ge=1, le=9999, description="数量")


class OrderItemResponse(BaseModel):
    """订单商品响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    product_image: Optional[str] = None
    variant_name: Optional[str] = None
    sku: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderResponse(BaseModel):
    """订单响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_no: str
    user_id: int
    status: str
    payment_status: str
    shipping_status: str
    
    # 金额信息
    subtotal: Decimal
    shipping_fee: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    
    # 收货信息
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    
    # 物流信息
    shipping_company: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # 支付信息
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    
    # 备注
    customer_note: Optional[str] = None
    admin_note: Optional[str] = None
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 订单商品
    items: List[OrderItemResponse]


class OrderListResponse(BaseModel):
    """订单列表响应"""
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    user_id: int = Field(..., ge=1, description="用户ID")
    items: List[OrderItemRequest] = Field(..., min_length=1, description="订单商品")
    address_id: int = Field(..., ge=1, description="收货地址ID")
    shipping_fee: Decimal = Field(default=Decimal("0.00"), ge=0, description="运费")
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="优惠金额")
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="税费")
    customer_note: Optional[str] = Field(None, max_length=500, description="客户备注")
    payment_method: Optional[str] = Field(None, max_length=50, description="支付方式")


class OrderUpdateRequest(BaseModel):
    """更新订单请求"""
    admin_note: Optional[str] = Field(None, max_length=500, description="管理员备注")


class OrderStatusUpdateRequest(BaseModel):
    """更新订单状态请求"""
    status: OrderStatus = Field(..., description="新状态")
    remark: Optional[str] = Field(None, max_length=255, description="备注")


class ShippingInfoRequest(BaseModel):
    """物流信息请求"""
    shipping_company: str = Field(..., min_length=1, max_length=100, description="物流公司")
    tracking_number: str = Field(..., min_length=1, max_length=100, description="物流单号")


class PaymentRequest(BaseModel):
    """支付请求"""
    payment_method: str = Field(..., min_length=1, max_length=50, description="支付方式")
    amount: Decimal = Field(..., gt=0, description="支付金额")


class PaymentResponse(BaseModel):
    """支付响应"""
    payment_no: str
    order_no: str
    payment_method: str
    amount: Decimal
    status: str
    paid_at: Optional[datetime] = None


class OrderStatisticsResponse(BaseModel):
    """订单统计响应"""
    total_orders: int
    total_amount: Decimal
    pending_orders: int
    paid_orders: int
    shipped_orders: int
    completed_orders: int
    cancelled_orders: int
    today_orders: int
    today_amount: Decimal


# ============================================
# 模拟数据
# ============================================

MOCK_ORDERS = [
    {
        "id": 1,
        "order_no": "202403010001",
        "user_id": 1,
        "status": "completed",
        "payment_status": "paid",
        "shipping_status": "delivered",
        "subtotal": Decimal("9999.00"),
        "shipping_fee": Decimal("0.00"),
        "discount_amount": Decimal("200.00"),
        "tax_amount": Decimal("0.00"),
        "total_amount": Decimal("9799.00"),
        "paid_amount": Decimal("9799.00"),
        "receiver_name": "张三",
        "receiver_phone": "13800138000",
        "receiver_address": "北京市朝阳区xxx街道xxx号",
        "shipping_company": "顺丰速运",
        "tracking_number": "SF1234567890",
        "shipped_at": datetime(2024, 3, 1, 10, 0, 0),
        "delivered_at": datetime(2024, 3, 2, 14, 30, 0),
        "payment_method": "alipay",
        "paid_at": datetime(2024, 3, 1, 9, 0, 0),
        "customer_note": "请尽快发货",
        "admin_note": "VIP客户",
        "created_at": datetime(2024, 3, 1, 8, 0, 0),
        "updated_at": datetime(2024, 3, 2, 14, 30, 0),
        "cancelled_at": None,
        "completed_at": datetime(2024, 3, 2, 14, 30, 0),
        "items": [
            {
                "id": 1,
                "product_id": 1,
                "variant_id": 1,
                "product_name": "iPhone 15 Pro Max 256GB",
                "product_image": "https://example.com/images/iphone15.jpg",
                "variant_name": "黑色-256GB",
                "sku": "PHONE-001-BLACK-256",
                "unit_price": Decimal("9999.00"),
                "quantity": 1,
                "subtotal": Decimal("9999.00")
            }
        ]
    },
    {
        "id": 2,
        "order_no": "202403010002",
        "user_id": 2,
        "status": "shipped",
        "payment_status": "paid",
        "shipping_status": "shipped",
        "subtotal": Decimal("15798.00"),
        "shipping_fee": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "tax_amount": Decimal("0.00"),
        "total_amount": Decimal("15798.00"),
        "paid_amount": Decimal("15798.00"),
        "receiver_name": "李四",
        "receiver_phone": "13900139000",
        "receiver_address": "上海市浦东新区xxx路xxx号",
        "shipping_company": "京东物流",
        "tracking_number": "JD9876543210",
        "shipped_at": datetime(2024, 3, 1, 16, 0, 0),
        "delivered_at": None,
        "payment_method": "wechat",
        "paid_at": datetime(2024, 3, 1, 10, 30, 0),
        "customer_note": None,
        "admin_note": None,
        "created_at": datetime(2024, 3, 1, 10, 0, 0),
        "updated_at": datetime(2024, 3, 1, 16, 0, 0),
        "cancelled_at": None,
        "completed_at": None,
        "items": [
            {
                "id": 2,
                "product_id": 2,
                "variant_id": None,
                "product_name": "Samsung Galaxy S24 Ultra",
                "product_image": "https://example.com/images/s24.jpg",
                "variant_name": None,
                "sku": "PHONE-002",
                "unit_price": Decimal("9699.00"),
                "quantity": 1,
                "subtotal": Decimal("9699.00")
            },
            {
                "id": 3,
                "product_id": 4,
                "variant_id": None,
                "product_name": "Nike Air Max 90",
                "product_image": "https://example.com/images/nike.jpg",
                "variant_name": None,
                "sku": "SHOE-001",
                "unit_price": Decimal("799.00"),
                "quantity": 2,
                "subtotal": Decimal("1598.00")
            }
        ]
    },
    {
        "id": 3,
        "order_no": "202403010003",
        "user_id": 3,
        "status": "pending",
        "payment_status": "unpaid",
        "shipping_status": "unshipped",
        "subtotal": Decimal("14999.00"),
        "shipping_fee": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "tax_amount": Decimal("0.00"),
        "total_amount": Decimal("14999.00"),
        "paid_amount": Decimal("0.00"),
        "receiver_name": "王五",
        "receiver_phone": "13700137000",
        "receiver_address": "广州市天河区xxx大道xxx号",
        "shipping_company": None,
        "tracking_number": None,
        "shipped_at": None,
        "delivered_at": None,
        "payment_method": None,
        "paid_at": None,
        "customer_note": "工作日送货",
        "admin_note": None,
        "created_at": datetime(2024, 3, 1, 12, 0, 0),
        "updated_at": datetime(2024, 3, 1, 12, 0, 0),
        "cancelled_at": None,
        "completed_at": None,
        "items": [
            {
                "id": 4,
                "product_id": 3,
                "variant_id": None,
                "product_name": "MacBook Pro 14英寸 M3",
                "product_image": "https://example.com/images/macbook.jpg",
                "variant_name": None,
                "sku": "PC-001",
                "unit_price": Decimal("14999.00"),
                "quantity": 1,
                "subtotal": Decimal("14999.00")
            }
        ]
    },
    {
        "id": 4,
        "order_no": "202403010004",
        "user_id": 1,
        "status": "cancelled",
        "payment_status": "unpaid",
        "shipping_status": "unshipped",
        "subtotal": Decimal("799.00"),
        "shipping_fee": Decimal("10.00"),
        "discount_amount": Decimal("0.00"),
        "tax_amount": Decimal("0.00"),
        "total_amount": Decimal("809.00"),
        "paid_amount": Decimal("0.00"),
        "receiver_name": "张三",
        "receiver_phone": "13800138000",
        "receiver_address": "北京市朝阳区xxx街道xxx号",
        "shipping_company": None,
        "tracking_number": None,
        "shipped_at": None,
        "delivered_at": None,
        "payment_method": None,
        "paid_at": None,
        "customer_note": None,
        "admin_note": "客户取消",
        "created_at": datetime(2024, 3, 1, 9, 0, 0),
        "updated_at": datetime(2024, 3, 1, 11, 0, 0),
        "cancelled_at": datetime(2024, 3, 1, 11, 0, 0),
        "completed_at": None,
        "items": [
            {
                "id": 5,
                "product_id": 4,
                "variant_id": None,
                "product_name": "Nike Air Max 90",
                "product_image": "https://example.com/images/nike.jpg",
                "variant_name": None,
                "sku": "SHOE-001",
                "unit_price": Decimal("799.00"),
                "quantity": 1,
                "subtotal": Decimal("799.00")
            }
        ]
    }
]


# 模拟商品数据（用于创建订单时计算价格）
MOCK_PRODUCTS = {
    1: {"name": "iPhone 15 Pro Max 256GB", "price": Decimal("9999.00"), "image": "https://example.com/images/iphone15.jpg", "sku": "PHONE-001"},
    2: {"name": "Samsung Galaxy S24 Ultra", "price": Decimal("9699.00"), "image": "https://example.com/images/s24.jpg", "sku": "PHONE-002"},
    3: {"name": "MacBook Pro 14英寸 M3", "price": Decimal("14999.00"), "image": "https://example.com/images/macbook.jpg", "sku": "PC-001"},
    4: {"name": "Nike Air Max 90", "price": Decimal("799.00"), "image": "https://example.com/images/nike.jpg", "sku": "SHOE-001"},
}


# 模拟地址数据
MOCK_ADDRESSES = {
    1: {"receiver_name": "张三", "receiver_phone": "13800138000", "full_address": "北京市朝阳区xxx街道xxx号"},
    2: {"receiver_name": "李四", "receiver_phone": "13900139000", "full_address": "上海市浦东新区xxx路xxx号"},
    3: {"receiver_name": "王五", "receiver_phone": "13700137000", "full_address": "广州市天河区xxx大道xxx号"},
}


# ============================================
# 辅助函数
# ============================================

def generate_order_no() -> str:
    """生成订单号"""
    now = datetime.now()
    return f"{now.strftime('%Y%m%d')}{len(MOCK_ORDERS) + 1:04d}"


def generate_payment_no() -> str:
    """生成支付流水号"""
    now = datetime.now()
    return f"PAY{now.strftime('%Y%m%d%H%M%S')}{len(MOCK_ORDERS) + 1:04d}"


# ============================================
# API 路由
# ============================================

@router.get("", response_model=OrderListResponse, summary="获取订单列表")
async def get_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: Optional[int] = Query(None, ge=1, description="用户ID"),
    status: Optional[OrderStatus] = Query(None, description="订单状态"),
    payment_status: Optional[PaymentStatus] = Query(None, description="支付状态"),
    shipping_status: Optional[ShippingStatus] = Query(None, description="物流状态"),
    order_no: Optional[str] = Query(None, description="订单号"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc")
) -> OrderListResponse:
    """
    获取订单列表，支持分页、筛选和排序
    
    - **page**: 页码，从1开始
    - **page_size**: 每页数量，默认20，最大100
    - **user_id**: 按用户筛选
    - **status**: 按订单状态筛选
    - **payment_status**: 按支付状态筛选
    - **shipping_status**: 按物流状态筛选
    - **order_no**: 按订单号搜索
    - **start_date/end_date**: 按日期范围筛选
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向 (asc/desc)
    """
    # 模拟筛选
    filtered_orders = MOCK_ORDERS.copy()
    
    if user_id:
        filtered_orders = [o for o in filtered_orders if o["user_id"] == user_id]
    
    if status:
        filtered_orders = [o for o in filtered_orders if o["status"] == status.value]
    
    if payment_status:
        filtered_orders = [o for o in filtered_orders if o["payment_status"] == payment_status.value]
    
    if shipping_status:
        filtered_orders = [o for o in filtered_orders if o["shipping_status"] == shipping_status.value]
    
    if order_no:
        filtered_orders = [o for o in filtered_orders if order_no in o["order_no"]]
    
    if start_date:
        filtered_orders = [o for o in filtered_orders if o["created_at"] >= start_date]
    
    if end_date:
        filtered_orders = [o for o in filtered_orders if o["created_at"] <= end_date]
    
    # 排序
    reverse = sort_order.lower() == "desc"
    filtered_orders.sort(key=lambda x: x.get(sort_by, x["created_at"]), reverse=reverse)
    
    # 分页
    total = len(filtered_orders)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered_orders[start:end]
    
    return OrderListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{order_id}", response_model=OrderResponse, summary="获取订单详情")
async def get_order(
    order_id: int = Path(..., ge=1, description="订单ID")
) -> OrderResponse:
    """
    根据ID获取订单详细信息
    
    - **order_id**: 订单唯一标识
    """
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单ID {order_id} 不存在"
        )
    
    return OrderResponse(**order)


@router.get("/number/{order_no}", response_model=OrderResponse, summary="根据订单号获取订单")
async def get_order_by_no(
    order_no: str = Path(..., description="订单号")
) -> OrderResponse:
    """
    根据订单号获取订单详情
    
    - **order_no**: 订单编号
    """
    order = next((o for o in MOCK_ORDERS if o["order_no"] == order_no), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单号 {order_no} 不存在"
        )
    
    return OrderResponse(**order)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="创建订单")
async def create_order(
    request: OrderCreateRequest
) -> OrderResponse:
    """
    创建新订单
    
    - **user_id**: 用户ID
    - **items**: 订单商品列表
    - **address_id**: 收货地址ID
    - **shipping_fee**: 运费
    - **discount_amount**: 优惠金额
    - **tax_amount**: 税费
    - **customer_note**: 客户备注
    - **payment_method**: 支付方式
    """
    # 验证地址
    address = MOCK_ADDRESSES.get(request.address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"地址ID {request.address_id} 不存在"
        )
    
    # 计算订单金额
    order_items = []
    subtotal = Decimal("0.00")
    
    for item_req in request.items:
        product = MOCK_PRODUCTS.get(item_req.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"商品ID {item_req.product_id} 不存在"
            )
        
        item_subtotal = product["price"] * item_req.quantity
        subtotal += item_subtotal
        
        order_items.append({
            "id": len(order_items) + 1,
            "product_id": item_req.product_id,
            "variant_id": item_req.variant_id,
            "product_name": product["name"],
            "product_image": product["image"],
            "variant_name": None,
            "sku": product["sku"],
            "unit_price": product["price"],
            "quantity": item_req.quantity,
            "subtotal": item_subtotal
        })
    
    # 计算总金额
    total_amount = subtotal + request.shipping_fee - request.discount_amount + request.tax_amount
    
    # 创建订单
    new_order = {
        "id": len(MOCK_ORDERS) + 1,
        "order_no": generate_order_no(),
        "user_id": request.user_id,
        "status": "pending",
        "payment_status": "unpaid",
        "shipping_status": "unshipped",
        "subtotal": subtotal,
        "shipping_fee": request.shipping_fee,
        "discount_amount": request.discount_amount,
        "tax_amount": request.tax_amount,
        "total_amount": total_amount,
        "paid_amount": Decimal("0.00"),
        "receiver_name": address["receiver_name"],
        "receiver_phone": address["receiver_phone"],
        "receiver_address": address["full_address"],
        "shipping_company": None,
        "tracking_number": None,
        "shipped_at": None,
        "delivered_at": None,
        "payment_method": request.payment_method,
        "paid_at": None,
        "customer_note": request.customer_note,
        "admin_note": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "cancelled_at": None,
        "completed_at": None,
        "items": order_items
    }
    
    MOCK_ORDERS.append(new_order)
    
    return OrderResponse(**new_order)


@router.put("/{order_id}", response_model=OrderResponse, summary="更新订单")
async def update_order(
    request: OrderUpdateRequest,
    order_id: int = Path(..., ge=1, description="订单ID")
) -> OrderResponse:
    """
    更新订单信息（仅支持更新管理员备注）
    
    - **order_id**: 订单ID
    """
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单ID {order_id} 不存在"
        )
    
    if request.admin_note is not None:
        order["admin_note"] = request.admin_note
    
    order["updated_at"] = datetime.now()
    
    return OrderResponse(**order)


@router.patch("/{order_id}/status", response_model=OrderResponse, summary="更新订单状态")
async def update_order_status(
    request: OrderStatusUpdateRequest,
    order_id: int = Path(..., ge=1, description="订单ID")
) -> OrderResponse:
    """
    更新订单状态
    
    - **order_id**: 订单ID
    - **status**: 新状态
    - **remark**: 状态变更备注
    """
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单ID {order_id} 不存在"
        )
    
    # 状态流转验证
    valid_transitions = {
        "pending": ["paid", "cancelled"],
        "paid": ["processing", "cancelled"],
        "processing": ["shipped", "cancelled"],
        "shipped": ["delivered"],
        "delivered": ["completed"],
        "completed": [],
        "cancelled": [],
        "refunded": []
    }
    
    current_status = order["status"]
    new_status = request.status.value
    
    if new_status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法从状态 '{current_status}' 变更为 '{new_status}'"
        )
    
    order["status"] = new_status
    order["updated_at"] = datetime.now()
    
    # 更新相关状态和时间戳
    if new_status == "paid":
        order["payment_status"] = "paid"
        order["paid_at"] = datetime.now()
    elif new_status == "shipped":
        order["shipping_status"] = "shipped"
        order["shipped_at"] = datetime.now()
    elif new_status == "delivered":
        order["shipping_status"] = "delivered"
        order["delivered_at"] = datetime.now()
    elif new_status == "completed":
        order["completed_at"] = datetime.now()
    elif new_status == "cancelled":
        order["cancelled_at"] = datetime.now()
    elif new_status == "refunded":
        order["payment_status"] = "refunded"
    
    return OrderResponse(**order)


@router.post("/{order_id}/ship", response_model=OrderResponse, summary="订单发货")
async def ship_order(
    request: ShippingInfoRequest,
    order_id: int = Path(..., ge=1, description="订单ID")
) -> OrderResponse:
    """
    订单发货
    
    - **order_id**: 订单ID
    - **shipping_company**: 物流公司
    - **tracking_number**: 物流单号
    """
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单ID {order_id} 不存在"
        )
    
    if order["status"] not in ["paid", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已付款或处理中的订单可以发货"
        )
    
    order["shipping_company"] = request.shipping_company
    order["tracking_number"] = request.tracking_number
    order["status"] = "shipped"
    order["shipping_status"] = "shipped"
    order["shipped_at"] = datetime.now()
    order["updated_at"] = datetime.now()
    
    return OrderResponse(**order)


@router.post("/{order_id}/pay", response_model=PaymentResponse, summary="订单支付")
async def pay_order(
    request: PaymentRequest,
    order_id: int = Path(..., ge=1, description="订单ID")
) -> PaymentResponse:
    """
    订单支付
    
    - **order_id**: 订单ID
    - **payment_method**: 支付方式
    - **amount**: 支付金额
    """
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单ID {order_id} 不存在"
        )
    
    if order["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有待付款订单可以支付"
        )
    
    if request.amount != order["total_amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"支付金额不匹配，应付: {order['total_amount']}"
        )
    
    # 更新订单状态
    order["status"] = "paid"
    order["payment_status"] = "paid"
    order["paid_amount"] = request.amount
    order["payment_method"] = request.payment_method
    order["paid_at"] = datetime.now()
    order["updated_at"] = datetime.now()
    
    return PaymentResponse(
        payment_no=generate_payment_no(),
        order_no=order["order_no"],
        payment_method=request.payment_method,
        amount=request.amount,
        status="success",
        paid_at=order["paid_at"]
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse, summary="取消订单")
async def cancel_order(
    order_id: int = Path(..., ge=1, description="订单ID"),
    reason: Optional[str] = Query(None, description="取消原因")
) -> OrderResponse:
    """
    取消订单
    
    - **order_id**: 订单ID
    - **reason**: 取消原因
    """
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单ID {order_id} 不存在"
        )
    
    if order["status"] not in ["pending", "paid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有待付款或已付款的订单可以取消"
        )
    
    order["status"] = "cancelled"
    order["cancelled_at"] = datetime.now()
    order["updated_at"] = datetime.now()
    
    if reason:
        order["admin_note"] = f"取消原因: {reason}"
    
    return OrderResponse(**order)


@router.get("/user/{user_id}/orders", response_model=OrderListResponse, summary="获取用户订单")
async def get_user_orders(
    user_id: int = Path(..., ge=1, description="用户ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[OrderStatus] = Query(None, description="订单状态")
) -> OrderListResponse:
    """
    获取指定用户的订单列表
    
    - **user_id**: 用户ID
    - **page**: 页码
    - **page_size**: 每页数量
    - **status**: 订单状态筛选
    """
    filtered_orders = [o for o in MOCK_ORDERS if o["user_id"] == user_id]
    
    if status:
        filtered_orders = [o for o in filtered_orders if o["status"] == status.value]
    
    # 按创建时间倒序
    filtered_orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 分页
    total = len(filtered_orders)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered_orders[start:end]
    
    return OrderListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/statistics/overview", response_model=OrderStatisticsResponse, summary="订单统计")
async def get_order_statistics() -> OrderStatisticsResponse:
    """
    获取订单统计数据
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_orders = len(MOCK_ORDERS)
    total_amount = sum(o["total_amount"] for o in MOCK_ORDERS)
    
    pending_orders = len([o for o in MOCK_ORDERS if o["status"] == "pending"])
    paid_orders = len([o for o in MOCK_ORDERS if o["status"] in ["paid", "processing", "shipped"]])
    shipped_orders = len([o for o in MOCK_ORDERS if o["status"] == "shipped"])
    completed_orders = len([o for o in MOCK_ORDERS if o["status"] == "completed"])
    cancelled_orders = len([o for o in MOCK_ORDERS if o["status"] == "cancelled"])
    
    today_orders_list = [o for o in MOCK_ORDERS if o["created_at"] >= today]
    today_orders = len(today_orders_list)
    today_amount = sum(o["total_amount"] for o in today_orders_list)
    
    return OrderStatisticsResponse(
        total_orders=total_orders,
        total_amount=total_amount,
        pending_orders=pending_orders,
        paid_orders=paid_orders,
        shipped_orders=shipped_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        today_orders=today_orders,
        today_amount=today_amount
    )
