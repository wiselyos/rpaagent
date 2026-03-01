#!/bin/bash
# 电商自动化系统 - 完整启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║         🚀 电商自动化系统 - 启动脚本                         ║"
echo "║                                                              ║"
echo "║         RPA + AI + OpenClaw 智能电商运营平台                 ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查命令行参数
COMMAND=${1:-help}

case $COMMAND in
    start)
        echo -e "${GREEN}▶ 启动服务...${NC}"
        
        # 1. 检查环境
        echo -e "${YELLOW}📋 检查环境...${NC}"
        
        if ! command -v python3 &> /dev/null; then
            echo -e "${RED}❌ Python3 未安装${NC}"
            exit 1
        fi
        
        if ! command -v docker &> /dev/null; then
            echo -e "${YELLOW}⚠️ Docker 未安装，跳过容器检查${NC}"
        fi
        
        # 2. 检查配置文件
        echo -e "${YELLOW}📋 检查配置文件...${NC}"
        if [ ! -f "$PROJECT_DIR/.env" ]; then
            echo -e "${YELLOW}⚠️ .env 文件不存在，从示例创建...${NC}"
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            echo -e "${YELLOW}⚠️ 请编辑 .env 文件配置数据库等信息${NC}"
        fi
        
        # 3. 启动 API 服务
        echo -e "${YELLOW}🚀 启动 API 服务...${NC}"
        cd "$PROJECT_DIR/api"
        
        # 后台启动
        nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/ecommerce-api.log 2>&1 &
echo $! > /tmp/ecommerce-api.pid
        
        sleep 2
        
        # 检查是否启动成功
        if curl -s http://localhost:8000/health > /dev/null; then
            echo -e "${GREEN}✅ API 服务已启动: http://localhost:8000${NC}"
            echo -e "${GREEN}📚 API 文档: http://localhost:8000/docs${NC}"
        else
            echo -e "${YELLOW}⚠️ API 服务启动中，请稍后检查${NC}"
        fi
        
        # 4. 启动 Celery Worker
        echo -e "${YELLOW}🚀 启动任务队列...${NC}"
        cd "$PROJECT_DIR"
        
        nohup celery -A tasks.scheduler worker --loglevel=info > /tmp/ecommerce-worker.log 2>&1 &
echo $! > /tmp/ecommerce-worker.pid
        
        echo -e "${GREEN}✅ Celery Worker 已启动${NC}"
        
        # 5. 启动 Celery Beat（定时任务）
        nohup celery -A tasks.scheduler beat --loglevel=info > /tmp/ecommerce-beat.log 2>&1 &
echo $! > /tmp/ecommerce-beat.pid
        
        echo -e "${GREEN}✅ Celery Beat 已启动${NC}"
        
        echo ""
        echo -e "${GREEN}🎉 所有服务已启动！${NC}"
        echo ""
        echo "服务状态:"
        echo "  - API:      http://localhost:8000"
        echo "  - 文档:     http://localhost:8000/docs"
        echo "  - 日志:     /tmp/ecommerce-*.log"
        ;;
    
    stop)
        echo -e "${YELLOW}⏹ 停止服务...${NC}"
        
        # 停止 API
        if [ -f /tmp/ecommerce-api.pid ]; then
            kill $(cat /tmp/ecommerce-api.pid) 2>/dev/null || true
            rm /tmp/ecommerce-api.pid
            echo -e "${GREEN}✅ API 服务已停止${NC}"
        fi
        
        # 停止 Celery
        if [ -f /tmp/ecommerce-worker.pid ]; then
            kill $(cat /tmp/ecommerce-worker.pid) 2>/dev/null || true
            rm /tmp/ecommerce-worker.pid
            echo -e "${GREEN}✅ Celery Worker 已停止${NC}"
        fi
        
        if [ -f /tmp/ecommerce-beat.pid ]; then
            kill $(cat /tmp/ecommerce-beat.pid) 2>/dev/null || true
            rm /tmp/ecommerce-beat.pid
            echo -e "${GREEN}✅ Celery Beat 已停止${NC}"
        fi
        
        echo -e "${GREEN}🎉 所有服务已停止${NC}"
        ;;
    
    status)
        echo -e "${BLUE}📊 服务状态${NC}"
        echo ""
        
        # 检查 API
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API 服务: 运行中${NC}"
            curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || true
        else
            echo -e "${RED}❌ API 服务: 未运行${NC}"
        fi
        
        echo ""
        
        # 检查 Celery
        if pgrep -f "celery.*scheduler" > /dev/null; then
            echo -e "${GREEN}✅ Celery: 运行中${NC}"
        else
            echo -e "${RED}❌ Celery: 未运行${NC}"
        fi
        
        echo ""
        
        # 检查端口
        echo "端口占用:"
        ss -tlnp 2>/dev/null | grep -E ":8000|:6379|:3306" || netstat -tlnp 2>/dev/null | grep -E ":8000|:6379|:3306" || echo "  无法获取端口信息"
        ;;
    
    restart)
        echo -e "${YELLOW}🔄 重启服务...${NC}"
        $0 stop
        sleep 2
        $0 start
        ;;
    
    test)
        echo -e "${BLUE}🧪 运行测试...${NC}"
        cd "$PROJECT_DIR"
        python3 tests/test_integration.py
        ;;
    
    logs)
        SERVICE=${2:-api}
        LOG_FILE="/tmp/ecommerce-${SERVICE}.log"
        
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo -e "${RED}❌ 日志文件不存在: $LOG_FILE${NC}"
            echo "可用日志: api, worker, beat"
        fi
        ;;
    
    deploy)
        echo -e "${BLUE}🚀 部署到生产环境...${NC}"
        "$PROJECT_DIR/scripts/deploy.sh" deploy
        ;;
    
    help|*)
        echo "用法: $0 {start|stop|restart|status|test|logs|deploy|help}"
        echo ""
        echo "命令:"
        echo "  start   - 启动所有服务"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        echo "  test    - 运行测试"
        echo "  logs    - 查看日志 (api/worker/beat)"
        echo "  deploy  - 部署到生产环境"
        echo "  help    - 显示帮助"
        echo ""
        echo "示例:"
        echo "  $0 start          # 启动服务"
        echo "  $0 logs api       # 查看 API 日志"
        echo "  $0 status         # 查看状态"
        ;;
esac
