# Skill: customer-service
# 电商智能客服系统

name: customer-service
description: 电商智能客服系统，自动处理客户咨询、订单查询、售后问题
version: 1.0.0
author: Kimi Claw

# 触发方式
triggers:
  - type: webhook
    endpoint: /webhook/customer-message
    description: 接收客户消息 webhook
  
  - type: cron
    schedule: "*/5 * * * *"
    action: check_pending_messages
    description: 每5分钟检查待处理消息

# 依赖
dependencies:
  - database-operations
  - ai-model-kimi

# 配置
config:
  database:
    host: localhost
    port: 3306
    name: ecommerce
  
  ai:
    model: kimi-coding/k2p5
    temperature: 0.7
    max_tokens: 500
  
  escalation:
    confidence_threshold: 0.6
    human_agents: ["support@company.com"]

# 动作定义
actions:
  - name: handle_message
    description: 处理客户消息
    params:
      - customer_id: string
      - message: string
      - order_id: string (optional)
      - platform: enum[taobao,jd,pdd,douyin]
  
  - name: query_order
    description: 查询订单状态
    params:
      - order_id: string
  
  - name: process_refund
    description: 处理退款申请
    params:
      - order_id: string
      - reason: string
  
  - name: escalate_to_human
    description: 转人工处理
    params:
      - conversation_id: string
      - reason: string
