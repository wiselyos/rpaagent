#!/usr/bin/env python3
"""
用户管理 API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str
    phone: Optional[str] = None
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: str

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """创建用户"""
    return {
        "id": 1,
        "username": user.username,
        "email": user.email,
        "status": "active"
    }

@router.get("/{user_id}")
async def get_user(user_id: int):
    """获取用户信息"""
    return {
        "id": user_id,
        "username": "test_user",
        "email": "test@example.com",
        "status": "active"
    }
