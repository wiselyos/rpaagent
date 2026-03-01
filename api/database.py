#!/usr/bin/env python3
"""
数据库连接和模型
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, Boolean
from datetime import datetime

# 数据库配置
DATABASE_URL = "mysql+aiomysql://ecommerce_user:password@localhost:3306/ecommerce"

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=True)

# 会话工厂
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 模型基类
Base = declarative_base()

# 依赖注入
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 初始化数据库
async def init_db():
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库初始化完成")
