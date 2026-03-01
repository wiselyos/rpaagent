"""
商品管理 API 路由
"""
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Query, Path, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

router = APIRouter()


# ============================================
# Pydantic 模型定义
# ============================================

class CategoryResponse(BaseModel):
    """分类响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    parent_id: Optional[int] = None
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class ProductVariantResponse(BaseModel):
    """商品规格响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sku: str
    variant_name: str
    attributes: dict
    price: Decimal
    original_price: Optional[Decimal] = None
    stock_quantity: int
    image: Optional[str] = None
    status: int


class ProductResponse(BaseModel):
    """商品响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    category_id: Optional[int] = None
    sku: str
    name: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    main_image: Optional[str] = None
    images: Optional[List[str]] = None
    stock_quantity: int
    status: str
    is_featured: bool
    sales_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    variants: Optional[List[ProductVariantResponse]] = None
    category: Optional[CategoryResponse] = None


class ProductListResponse(BaseModel):
    """商品列表响应"""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProductCreateRequest(BaseModel):
    """创建商品请求"""
    category_id: Optional[int] = None
    sku: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., gt=0)
    original_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    main_image: Optional[str] = Field(None, max_length=500)
    images: Optional[List[str]] = None
    stock_quantity: int = Field(default=0, ge=0)
    stock_alert_threshold: int = Field(default=10, ge=0)
    status: str = Field(default="draft")
    is_featured: bool = False
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)


class ProductUpdateRequest(BaseModel):
    """更新商品请求"""
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: Optional[Decimal] = Field(None, gt=0)
    original_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    main_image: Optional[str] = Field(None, max_length=500)
    images: Optional[List[str]] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    stock_alert_threshold: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)


class StockUpdateRequest(BaseModel):
    """库存更新请求"""
    quantity: int = Field(..., description="变动数量(正数增加,负数减少)")
    reason: Optional[str] = Field(None, max_length=255, description="变动原因")


class StockUpdateResponse(BaseModel):
    """库存更新响应"""
    product_id: int
    before_quantity: int
    after_quantity: int
    change_quantity: int


# ============================================
# 模拟数据 (实际项目中应从数据库获取)
# ============================================

MOCK_PRODUCTS = [
    {
        "id": 1,
        "category_id": 6,
        "sku": "PHONE-001",
        "name": "iPhone 15 Pro Max 256GB",
        "slug": "iphone-15-pro-max-256gb",
        "description": "Apple iPhone 15 Pro Max，搭载A17 Pro芯片，钛金属设计，支持USB-C。",
        "short_description": "旗舰手机，A17 Pro芯片",
        "price": Decimal("9999.00"),
        "original_price": Decimal("10999.00"),
        "main_image": "https://example.com/images/iphone15.jpg",
        "images": ["https://example.com/images/iphone15-1.jpg", "https://example.com/images/iphone15-2.jpg"],
        "stock_quantity": 100,
        "status": "active",
        "is_featured": True,
        "sales_count": 1250,
        "view_count": 50000,
        "created_at": datetime(2024, 1, 15, 10, 0, 0),
        "updated_at": datetime(2024, 3, 1, 8, 30, 0),
        "variants": [
            {
                "id": 1,
                "sku": "PHONE-001-BLACK-256",
                "variant_name": "黑色-256GB",
                "attributes": {"color": "黑色", "storage": "256GB"},
                "price": Decimal("9999.00"),
                "original_price": Decimal("10999.00"),
                "stock_quantity": 50,
                "image": "https://example.com/images/iphone15-black.jpg",
                "status": 1
            },
            {
                "id": 2,
                "sku": "PHONE-001-WHITE-256",
                "variant_name": "白色-256GB",
                "attributes": {"color": "白色", "storage": "256GB"},
                "price": Decimal("9999.00"),
                "original_price": Decimal("10999.00"),
                "stock_quantity": 50,
                "image": "https://example.com/images/iphone15-white.jpg",
                "status": 1
            }
        ],
        "category": {
            "id": 6,
            "parent_id": 1,
            "name": "手机通讯",
            "slug": "mobile-phones",
            "description": "智能手机、功能手机",
            "sort_order": 1,
            "is_active": True
        }
    },
    {
        "id": 2,
        "category_id": 6,
        "sku": "PHONE-002",
        "name": "Samsung Galaxy S24 Ultra",
        "slug": "samsung-galaxy-s24-ultra",
        "description": "三星Galaxy S24 Ultra，AI智能手机，2亿像素相机。",
        "short_description": "AI旗舰，2亿像素",
        "price": Decimal("9699.00"),
        "original_price": Decimal("9999.00"),
        "main_image": "https://example.com/images/s24.jpg",
        "images": None,
        "stock_quantity": 80,
        "status": "active",
        "is_featured": True,
        "sales_count": 890,
        "view_count": 35000,
        "created_at": datetime(2024, 2, 1, 9, 0, 0),
        "updated_at": datetime(2024, 3, 1, 8, 30, 0),
        "variants": [],
        "category": None
    },
    {
        "id": 3,
        "category_id": 7,
        "sku": "PC-001",
        "name": "MacBook Pro 14英寸 M3",
        "slug": "macbook-pro-14-m3",
        "description": "Apple MacBook Pro 14英寸，M3芯片，18小时续航。",
        "short_description": "M3芯片，专业性能",
        "price": Decimal("14999.00"),
        "original_price": Decimal("15999.00"),
        "main_image": "https://example.com/images/macbook.jpg",
        "images": None,
        "stock_quantity": 50,
        "status": "active",
        "is_featured": True,
        "sales_count": 450,
        "view_count": 28000,
        "created_at": datetime(2024, 1, 20, 14, 0, 0),
        "updated_at": datetime(2024, 3, 1, 8, 30, 0),
        "variants": [],
        "category": None
    },
    {
        "id": 4,
        "category_id": 9,
        "sku": "SHOE-001",
        "name": "Nike Air Max 90",
        "slug": "nike-air-max-90",
        "description": "经典耐克气垫跑鞋，舒适透气，时尚百搭。",
        "short_description": "经典气垫，舒适百搭",
        "price": Decimal("799.00"),
        "original_price": Decimal("899.00"),
        "main_image": "https://example.com/images/nike.jpg",
        "images": None,
        "stock_quantity": 200,
        "status": "active",
        "is_featured": False,
        "sales_count": 3200,
        "view_count": 15000,
        "created_at": datetime(2024, 1, 10, 11, 0, 0),
        "updated_at": datetime(2024, 3, 1, 8, 30, 0),
        "variants": [],
        "category": None
    }
]


# ============================================
# API 路由
# ============================================

@router.get("", response_model=ProductListResponse, summary="获取商品列表")
async def get_products(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    status: Optional[str] = Query(None, description="状态: draft/active/inactive/out_of_stock"),
    is_featured: Optional[bool] = Query(None, description="是否推荐"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="最低价格"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="最高价格"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc")
) -> ProductListResponse:
    """
    获取商品列表，支持分页、筛选和排序
    
    - **page**: 页码，从1开始
    - **page_size**: 每页数量，默认20，最大100
    - **category_id**: 按分类筛选
    - **status**: 按状态筛选
    - **is_featured**: 按是否推荐筛选
    - **min_price/max_price**: 按价格范围筛选
    - **keyword**: 按名称搜索
    - **sort_by**: 排序字段 (created_at/price/sales_count/view_count)
    - **sort_order**: 排序方向 (asc/desc)
    """
    # 模拟筛选
    filtered_products = MOCK_PRODUCTS.copy()
    
    if category_id:
        filtered_products = [p for p in filtered_products if p["category_id"] == category_id]
    
    if status:
        filtered_products = [p for p in filtered_products if p["status"] == status]
    
    if is_featured is not None:
        filtered_products = [p for p in filtered_products if p["is_featured"] == is_featured]
    
    if min_price is not None:
        filtered_products = [p for p in filtered_products if p["price"] >= min_price]
    
    if max_price is not None:
        filtered_products = [p for p in filtered_products if p["price"] <= max_price]
    
    if keyword:
        filtered_products = [p for p in filtered_products if keyword.lower() in p["name"].lower()]
    
    # 排序
    reverse = sort_order.lower() == "desc"
    filtered_products.sort(key=lambda x: x.get(sort_by, x["created_at"]), reverse=reverse)
    
    # 分页
    total = len(filtered_products)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered_products[start:end]
    
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{product_id}", response_model=ProductResponse, summary="获取商品详情")
async def get_product(
    product_id: int = Path(..., ge=1, description="商品ID")
) -> ProductResponse:
    """
    根据ID获取商品详细信息
    
    - **product_id**: 商品唯一标识
    """
    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"商品ID {product_id} 不存在"
        )
    
    # 增加浏览量（模拟）
    product["view_count"] += 1
    
    return ProductResponse(**product)


@router.get("/sku/{sku}", response_model=ProductResponse, summary="根据SKU获取商品")
async def get_product_by_sku(
    sku: str = Path(..., description="商品SKU")
) -> ProductResponse:
    """
    根据SKU获取商品详细信息
    
    - **sku**: 商品SKU编码
    """
    product = next((p for p in MOCK_PRODUCTS if p["sku"] == sku), None)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SKU {sku} 不存在"
        )
    
    return ProductResponse(**product)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="创建商品")
async def create_product(
    request: ProductCreateRequest
) -> ProductResponse:
    """
    创建新商品
    
    - **sku**: 商品SKU，必须唯一
    - **name**: 商品名称
    - **slug**: URL别名，必须唯一
    - **price**: 售价，必须大于0
    """
    # 检查SKU是否已存在
    if any(p["sku"] == request.sku for p in MOCK_PRODUCTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SKU {request.sku} 已存在"
        )
    
    # 检查slug是否已存在
    if any(p["slug"] == request.slug for p in MOCK_PRODUCTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug {request.slug} 已存在"
        )
    
    new_product = {
        "id": len(MOCK_PRODUCTS) + 1,
        **request.model_dump(),
        "sales_count": 0,
        "view_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "variants": [],
        "category": None
    }
    
    MOCK_PRODUCTS.append(new_product)
    
    return ProductResponse(**new_product)


@router.put("/{product_id}", response_model=ProductResponse, summary="更新商品")
async def update_product(
    request: ProductUpdateRequest,
    product_id: int = Path(..., ge=1, description="商品ID")
) -> ProductResponse:
    """
    更新商品信息
    
    - **product_id**: 商品ID
    - 所有字段均为可选，只更新提供的字段
    """
    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"商品ID {product_id} 不存在"
        )
    
    # 更新字段
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            product[key] = value
    
    product["updated_at"] = datetime.now()
    
    return ProductResponse(**product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除商品")
async def delete_product(
    product_id: int = Path(..., ge=1, description="商品ID")
) -> None:
    """
    删除商品（软删除）
    
    - **product_id**: 商品ID
    """
    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"商品ID {product_id} 不存在"
        )
    
    # 软删除：将状态改为inactive
    product["status"] = "inactive"
    product["updated_at"] = datetime.now()
    
    return None


@router.post("/{product_id}/stock", response_model=StockUpdateResponse, summary="更新库存")
async def update_stock(
    request: StockUpdateRequest,
    product_id: int = Path(..., ge=1, description="商品ID")
) -> StockUpdateResponse:
    """
    更新商品库存
    
    - **product_id**: 商品ID
    - **quantity**: 变动数量（正数增加，负数减少）
    - **reason**: 变动原因
    """
    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"商品ID {product_id} 不存在"
        )
    
    before_quantity = product["stock_quantity"]
    after_quantity = before_quantity + request.quantity
    
    if after_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="库存不足，无法减少"
        )
    
    product["stock_quantity"] = after_quantity
    product["updated_at"] = datetime.now()
    
    return StockUpdateResponse(
        product_id=product_id,
        before_quantity=before_quantity,
        after_quantity=after_quantity,
        change_quantity=request.quantity
    )


@router.get("/categories/list", response_model=List[CategoryResponse], summary="获取分类列表")
async def get_categories(
    parent_id: Optional[int] = Query(None, description="父分类ID")
) -> List[CategoryResponse]:
    """
    获取商品分类列表
    
    - **parent_id**: 父分类ID，不传则返回顶级分类
    """
    # 模拟分类数据
    categories = [
        {"id": 1, "parent_id": None, "name": "电子产品", "slug": "electronics", "description": "手机、电脑、数码配件等", "sort_order": 1, "is_active": True},
        {"id": 2, "parent_id": None, "name": "服装鞋帽", "slug": "clothing", "description": "男装、女装、童装、鞋靴等", "sort_order": 2, "is_active": True},
        {"id": 6, "parent_id": 1, "name": "手机通讯", "slug": "mobile-phones", "description": "智能手机、功能手机", "sort_order": 1, "is_active": True},
        {"id": 7, "parent_id": 1, "name": "电脑办公", "slug": "computers", "description": "笔记本、台式机、配件", "sort_order": 2, "is_active": True},
        {"id": 9, "parent_id": 2, "name": "鞋靴", "slug": "shoes", "description": "运动鞋、休闲鞋、皮鞋", "sort_order": 3, "is_active": True},
    ]
    
    if parent_id is not None:
        categories = [c for c in categories if c["parent_id"] == parent_id]
    else:
        categories = [c for c in categories if c["parent_id"] is None]
    
    return [CategoryResponse(**c) for c in categories]


@router.get("/featured/list", response_model=List[ProductResponse], summary="获取推荐商品")
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50, description="数量限制")
) -> List[ProductResponse]:
    """
    获取推荐商品列表
    
    - **limit**: 返回数量，默认10，最大50
    """
    featured = [p for p in MOCK_PRODUCTS if p["is_featured"] and p["status"] == "active"]
    featured = featured[:limit]
    
    return [ProductResponse(**p) for p in featured]
