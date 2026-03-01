#!/usr/bin/env python3
"""
简单的 API 连接测试 - 不使用签名
用于验证网络连接和应用配置
"""
import urllib.request
import urllib.parse
import json

# 基础配置
BASE_URL = "https://epay.alizzy.com/outside/25"
APP_ID = "2026021502557128"

def test_connection():
    """测试基础连接"""
    print("=" * 60)
    print("🌐 API 连接测试")
    print("=" * 60)
    
    # 测试 1: 基础连接
    print("\n1. 测试基础连接...")
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/order/list?app_id={APP_ID}",
            method="GET",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"   状态码: {response.status}")
            print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}")
            
            if result.get('msg') == '签名验证失败':
                print("\n   ⚠️  应用配置正确，但需要关闭签名验证或提供正确签名")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 测试 2: 检查应用状态
    print("\n2. 检查应用配置...")
    print(f"   应用ID: {APP_ID}")
    print(f"   接口地址: {BASE_URL}")
    print("\n   请确认:")
    print("   ✅ 应用已在商城后台开启")
    print("   ✅ API接口已开启")
    print("   ✅ 签名验证已关闭（或提供正确签名）")
    
    print("\n" + "=" * 60)
    print("📋 下一步建议")
    print("=" * 60)
    print("\n1. 在商城后台关闭签名验证:")
    print("   系统设置 → 商城设置 → APP应用 → 关闭签名验证")
    print("\n2. 或者提供正确的签名算法:")
    print("   请提供 PHP 端完整的签名代码示例")
    print("\n3. 联系商城技术支持:")
    print("   确认签名算法细节")

if __name__ == "__main__":
    test_connection()
