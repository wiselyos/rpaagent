"""
SQLAlchemy 数据库模型定义
电商自动化系统
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    String, Text, Integer, BigInteger, Boolean, DateTime, Decimal as SQLDecimal,
    ForeignKey, Index, Enum, JSON, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """基础模型类"""
    pass


# ============================================
# 枚举类型定义
# ============================================

class ProductStatus(str, enum.Enum):
    """商品状态"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 上架
    INACTIVE = "inactive"     # 下架
    OUT_OF_STOCK = "out_of_stock"  # 缺货


class OrderStatus(str, enum.Enum):
    """订单状态"""
    PENDING = "pending"       # 待付款
    PAID = "paid"             # 已付款
    PROCESSING = "processing" # 处理中
    SHIPPED = "shipped"       # 已发货
    DELIVERED = "delivered"   # 已送达
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"     # 已退款


class PaymentStatus(str, enum.Enum):
    """支付状态"""
    UNPAID = "unpaid"         # 未支付
    PAID = "paid"             # 已支付
    PARTIAL = "partial"       # 部分支付
    REFUNDED = "refunded"     # 已退款
    FAILED = "failed"         # 支付失败


class ShippingStatus(str, enum.Enum):
    """物流状态"""
    UNSHIPPED = "unshipped"   # 未发货
    PARTIAL = "partial"       # 部分发货
    SHIPPED = "shipped"       # 已发货
    DELIVERED = "delivered"   # 已签收


class InventoryChangeType(str, enum.Enum):
    """库存变动类型"""
    IN = "in"                 # 入库
    OUT = "out"               # 出库
    ADJUST = "adjust"         # 调整
    RETURN = "return"         # 退货
    DAMAGE = "damage"         # 损坏


class PaymentRecordStatus(str, enum.Enum):
    """支付记录状态"""
    PENDING = "pending"       # 待支付
    PROCESSING = "processing" # 处理中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"     # 已退款


# ============================================
# 模型定义
# ============================================

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系
    addresses: Mapped[List["Address"]] = relationship("Address", back_populates="user", lazy="selectin")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user", lazy="selectin")
    carts: Mapped[List["Cart"]] = relationship("Cart", back_populates="user", lazy="selectin")
    
    __table_args__ = (
        Index("idx_email", "email"),
        Index("idx_phone", "phone"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )


class Category(Base):
    """商品分类模型"""
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # 关系
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side=[id], back_populates="children", lazy="selectin"
    )
    children: Mapped[List["Category"]] = relationship(
        "Category", back_populates="parent", lazy="selectin"
    )
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category", lazy="selectin")
    
    __table_args__ = (
        Index("idx_parent_id", "parent_id"),
        Index("idx_slug", "slug"),
        Index("idx_active_sort", "is_active", "sort_order"),
    )


class Product(Base):
    """商品模型"""
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    original_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(15, 2), nullable=True)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(15, 2), nullable=True)
    weight: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(10, 3), nullable=True)
    main_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    images: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_alert_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.DRAFT, nullable=False
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sales_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products", lazy="selectin")
    variants: Mapped[List["ProductVariant"]] = relationship("ProductVariant", back_populates="product", lazy="selectin")
    inventory_logs: Mapped[List["InventoryLog"]] = relationship("InventoryLog", back_populates="product", lazy="selectin")
    
    __table_args__ = (
        Index("idx_category_id", "category_id"),
        Index("idx_sku", "sku"),
        Index("idx_slug", "slug"),
        Index("idx_status", "status"),
        Index("idx_price", "price"),
        Index("idx_featured", "is_featured", "status"),
        Index("idx_created_at", "created_at"),
    )


class ProductVariant(Base):
    """商品规格模型"""
    __tablename__ = "product_variants"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    variant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False)
    price: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    original_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(15, 2), nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # 关系
    product: Mapped["Product"] = relationship("Product", back_populates="variants", lazy="selectin")
    inventory_logs: Mapped[List["InventoryLog"]] = relationship("InventoryLog", back_populates="variant", lazy="selectin")
    
    __table_args__ = (
        Index("idx_product_id", "product_id"),
        Index("idx_sku", "sku"),
        Index("idx_status", "status"),
    )


class InventoryLog(Base):
    """库存变动记录模型"""
    __tablename__ = "inventory_logs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), nullable=False
    )
    variant_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("product_variants.id"), nullable=True
    )
    change_type: Mapped[InventoryChangeType] = mapped_column(
        Enum(InventoryChangeType), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    before_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    after_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    operator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # 关系
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_logs", lazy="selectin")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", back_populates="inventory_logs", lazy="selectin")
    
    __table_args__ = (
        Index("idx_product_id", "product_id"),
        Index("idx_variant_id", "variant_id"),
        Index("idx_change_type", "change_type"),
        Index("idx_reference", "reference_type", "reference_id"),
        Index("idx_created_at", "created_at"),
    )


class Address(Base):
    """收货地址模型"""
    __tablename__ = "addresses"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    receiver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    district: Mapped[str] = mapped_column(String(50), nullable=False)
    street_address: Mapped[str] = mapped_column(String(255), nullable=False)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="addresses", lazy="selectin")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_default", "is_default"),
    )


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False
    )
    shipping_status: Mapped[ShippingStatus] = mapped_column(
        Enum(ShippingStatus), default=ShippingStatus.UNSHIPPED, nullable=False
    )
    
    # 金额信息
    subtotal: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    shipping_fee: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), default=Decimal("0.00"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), default=Decimal("0.00"), nullable=False)
    
    # 收货信息
    receiver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    receiver_address: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 物流信息
    shipping_company: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 支付信息
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 备注信息
    customer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="selectin")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", lazy="selectin")
    status_history: Mapped[List["OrderStatusHistory"]] = relationship("OrderStatusHistory", back_populates="order", lazy="selectin")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order", lazy="selectin")
    
    __table_args__ = (
        Index("idx_order_no", "order_no"),
        Index("idx_user_id", "user_id"),
        Index("idx_status", "status"),
        Index("idx_payment_status", "payment_status"),
        Index("idx_shipping_status", "shipping_status"),
        Index("idx_created_at", "created_at"),
        Index("idx_status_created", "status", "created_at"),
    )


class OrderItem(Base):
    """订单商品模型"""
    __tablename__ = "order_items"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), nullable=False
    )
    variant_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # 商品快照
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    variant_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 价格数量
    unit_price: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # 关系
    order: Mapped["Order"] = relationship("Order", back_populates="items", lazy="selectin")
    
    __table_args__ = (
        Index("idx_order_id", "order_id"),
        Index("idx_product_id", "product_id"),
        Index("idx_variant_id", "variant_id"),
    )


class OrderStatusHistory(Base):
    """订单状态历史模型"""
    __tablename__ = "order_status_history"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=False
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    operator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    operator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # 关系
    order: Mapped["Order"] = relationship("Order", back_populates="status_history", lazy="selectin")
    
    __table_args__ = (
        Index("idx_order_id", "order_id"),
        Index("idx_created_at", "created_at"),
    )


class Payment(Base):
    """支付记录模型"""
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=False
    )
    payment_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    third_party_no: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(SQLDecimal(15, 2), nullable=False)
    status: Mapped[PaymentRecordStatus] = mapped_column(
        Enum(PaymentRecordStatus), default=PaymentRecordStatus.PENDING, nullable=False
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    gateway_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # 关系
    order: Mapped["Order"] = relationship("Order", back_populates="payments", lazy="selectin")
    
    __table_args__ = (
        Index("idx_order_id", "order_id"),
        Index("idx_payment_no", "payment_no"),
        Index("idx_third_party_no", "third_party_no"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )


class Cart(Base):
    """购物车模型"""
    __tablename__ = "carts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), nullable=False
    )
    variant_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("product_variants.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="carts", lazy="selectin")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", lazy="selectin")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_product_id", "product_id"),
    )
