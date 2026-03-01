"""
FastAPI 主应用
电商自动化系统 API
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from api.routers import orders, products

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("🚀 电商自动化系统 API 启动中...")
    
    # 这里可以添加数据库连接池初始化、缓存连接等
    
    yield
    
    # 关闭时执行
    logger.info("🛑 电商自动化系统 API 关闭中...")
    
    # 这里可以添加资源清理


# 创建 FastAPI 应用实例
app = FastAPI(
    title="电商自动化系统 API",
    description="E-commerce Automation System RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }
    )


# 注册路由
app.include_router(
    products.router,
    prefix="/api/v1/products",
    tags=["商品管理"]
)

app.include_router(
    orders.router,
    prefix="/api/v1/orders",
    tags=["订单管理"]
)


@app.get("/", tags=["健康检查"])
async def root() -> dict:
    """根路径 - API 信息"""
    return {
        "name": "电商自动化系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health", tags=["健康检查"])
async def health_check() -> dict:
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "ecommerce-api",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
