# Skill: order-automation
# 订单自动化处理系统

name: order-automation
description: 自动处理订单审核、发货、异常检测
version: 1.0.0
author: Kimi Claw

triggers:
  - type: cron
    schedule: "*/10 * * * *"
    action: process_pending_orders
    description: 每10分钟处理待处理订单
  
  - type: webhook
    endpoint: /webhook/new-order
    description: 新订单 webhook

config:
  risk_threshold: 0.8
  auto_fulfill: true
  warehouse_api: "https://warehouse-api.company.com"
  carriers:
    - sf
    - jd
    - yto

actions:
  - name: process_order
    description: 处理单个订单
    params:
      - order_id: string
  
  - name: risk_check
    description: 订单风控检查
    params:
      - order_id: string
  
  - name: generate_shipping_label
    description: 生成快递面单
    params:
      - order_id: string
      - carrier: string
