#!/usr/bin/env python3
"""
电商自动化系统测试脚本
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills'))

# 动态导入
import importlib.util

def load_skill(skill_name):
    skill_path = os.path.join(os.path.dirname(__file__), '..', 'skills', skill_name, 'handler.py')
    spec = importlib.util.spec_from_file_location(f"{skill_name}_handler", skill_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

customer_service_module = load_skill('customer-service')
order_automation_module = load_skill('order-automation')

CustomerServiceSkill = customer_service_module.skill
OrderAutomationSkill = order_automation_module.skill

class MockContext:
    """模拟 OpenClaw 上下文"""
    def __init__(self):
        self.config = {
            "auto_fulfill": True,
            "risk_threshold": 0.8
        }
    
    def get_database(self, name):
        return None
    
    def get_model(self, name):
        class MockModel:
            async def generate(self, prompt, **kwargs):
                return f"[AI回复] 收到您的问题，我已为您记录，稍后会有专员联系您。"
        return MockModel()

async def test_customer_service():
    """测试智能客服"""
    print("=" * 50)
    print("🧪 测试智能客服 Skill")
    print("=" * 50)
    
    context = MockContext()
    skill = CustomerServiceSkill(context)
    
    test_cases = [
        {
            "customer_id": "CUST001",
            "message": "我的订单到哪了？",
            "order_id": "ORD12345",
            "platform": "taobao"
        },
        {
            "customer_id": "CUST002",
            "message": "我要退货",
            "order_id": "ORD67890",
            "platform": "jd"
        },
        {
            "customer_id": "CUST003",
            "message": "这个商品有货吗？",
            "platform": "pdd"
        },
        {
            "customer_id": "CUST004",
            "message": "你们服务太差了，我要投诉！",
            "platform": "taobao"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"  客户: {test['customer_id']}")
        print(f"  消息: {test['message']}")
        
        result = await skill.handle_message(
            test['customer_id'],
            test['message'],
            test.get('order_id'),
            test['platform']
        )
        
        print(f"  意图: {result['intent']}")
        print(f"  置信度: {result['confidence']:.2f}")
        print(f"  转人工: {result['escalate']}")
        print(f"  回复: {result['response'][:100]}...")
    
    print("\n✅ 智能客服测试完成")

async def test_order_automation():
    """测试订单自动化"""
    print("\n" + "=" * 50)
    print("🧪 测试订单自动化 Skill")
    print("=" * 50)
    
    context = MockContext()
    skill = OrderAutomationSkill(context)
    
    print("\n测试批量处理订单...")
    result = await skill.process_pending_orders()
    
    print(f"  处理订单数: {result['processed']}")
    print(f"  审核通过: {result['approved']}")
    print(f"  审核拒绝: {result['rejected']}")
    print(f"  转人工: {result['escalated']}")
    
    if result['errors']:
        print(f"  错误数: {len(result['errors'])}")
    
    print("\n✅ 订单自动化测试完成")

async def main():
    """主测试函数"""
    print("\n🚀 电商自动化系统测试")
    print("=" * 50)
    
    try:
        await test_customer_service()
        await test_order_automation()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
