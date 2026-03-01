#!/bin/bash
# ============================================
# 电商自动化系统 - 一键部署脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# 配置变量
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_DIR/docker"
ENV_FILE="$DOCKER_DIR/.env"

# 默认配置
DEFAULT_APP_PORT=8000
DEFAULT_MYSQL_PORT=3306
DEFAULT_REDIS_PORT=6379
DEFAULT_RABBITMQ_PORT=5672
DEFAULT_RABBITMQ_MGMT_PORT=15672
DEFAULT_GRAFANA_PORT=3000
DEFAULT_PROMETHEUS_PORT=9090

# ============================================
# 日志函数
# ============================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================
# 检查依赖
# ============================================
check_dependencies() {
    log_info "检查依赖环境..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        # 检查 docker compose (新格式)
        if ! docker compose version &> /dev/null; then
            missing_deps+=("docker-compose")
        fi
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_info "请安装 Docker 和 Docker Compose 后再运行此脚本"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# ============================================
# 生成环境配置文件
# ============================================
generate_env_file() {
    log_info "生成环境配置文件..."
    
    if [ -f "$ENV_FILE" ]; then
        log_warn "环境文件已存在: $ENV_FILE"
        read -p "是否覆盖? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "保留现有配置文件"
            return
        fi
    fi
    
    # 生成随机密码
    MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
    MYSQL_PASSWORD=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
    REDIS_PASSWORD=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
    RABBITMQ_PASSWORD=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
    SECRET_KEY=$(openssl rand -base64 64 2>/dev/null || head -c 64 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 64)
    
    cat > "$ENV_FILE" << EOF
# ============================================
# 电商自动化系统 - 环境配置
# 生成时间: $(date)
# ============================================

# 应用配置
APP_ENV=production
APP_PORT=${DEFAULT_APP_PORT}
LOG_LEVEL=INFO
SECRET_KEY=${SECRET_KEY}
APP_REPLICAS=1

# MySQL 配置
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
MYSQL_DATABASE=ecommerce
MYSQL_USER=ecommerce_user
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_PORT=${DEFAULT_MYSQL_PORT}

# Redis 配置
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_PORT=${DEFAULT_REDIS_PORT}

# RabbitMQ 配置
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD}
RABBITMQ_VHOST=/ecommerce
RABBITMQ_PORT=${DEFAULT_RABBITMQ_PORT}
RABBITMQ_MANAGEMENT_PORT=${DEFAULT_RABBITMQ_MGMT_PORT}

# Nginx 配置
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# 监控配置
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
GRAFANA_ROOT_URL=http://localhost:${DEFAULT_GRAFANA_PORT}
GRAFANA_PORT=${DEFAULT_GRAFANA_PORT}
PROMETHEUS_PORT=${DEFAULT_PROMETHEUS_PORT}
EOF
    
    log_success "环境配置文件已生成: $ENV_FILE"
    log_info "请根据需要修改配置，特别是密码和端口"
}

# ============================================
# 创建必要目录
# ============================================
setup_directories() {
    log_info "创建必要目录..."
    
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/uploads"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$DOCKER_DIR/init-scripts"
    mkdir -p "$DOCKER_DIR/nginx/conf.d"
    mkdir -p "$DOCKER_DIR/prometheus/rules"
    mkdir -p "$DOCKER_DIR/grafana/dashboards"
    mkdir -p "$DOCKER_DIR/grafana/datasources"
    
    log_success "目录创建完成"
}

# ============================================
# 创建 Nginx 配置
# ============================================
setup_nginx() {
    log_info "配置 Nginx..."
    
    # 主配置文件
    cat > "$DOCKER_DIR/nginx/nginx.conf" << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    include /etc/nginx/conf.d/*.conf;
}
EOF

    # 应用配置
    cat > "$DOCKER_DIR/nginx/conf.d/app.conf" << 'EOF'
upstream app_servers {
    least_conn;
    server app:8000 max_fails=3 fail_timeout=30s;
    # 如需多实例，取消下面注释
    # server app2:8000 max_fails=3 fail_timeout=30s;
    # server app3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 50M;
    
    # 静态文件
    location /static {
        alias /var/www/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 上传文件
    location /uploads {
        alias /var/www/uploads;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # 健康检查
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # API 限流
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # 登录限流
    location /api/auth/login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 默认代理
    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
EOF

    log_success "Nginx 配置完成"
}

# ============================================
# 创建 Grafana 数据源配置
# ============================================
setup_grafana() {
    log_info "配置 Grafana..."
    
    # 数据源配置
    cat > "$DOCKER_DIR/grafana/datasources/datasource.yml" << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: 5s
EOF

    # 仪表板配置
    cat > "$DOCKER_DIR/grafana/dashboards/dashboard.yml" << 'EOF'
apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    # 复制仪表板 JSON
    if [ -f "$PROJECT_DIR/monitoring/grafana-dashboard.json" ]; then
        cp "$PROJECT_DIR/monitoring/grafana-dashboard.json" "$DOCKER_DIR/grafana/dashboards/"
        log_success "Grafana 仪表板已复制"
    fi
    
    log_success "Grafana 配置完成"
}

# ============================================
# 创建告警规则
# ============================================
setup_alerting() {
    log_info "配置告警规则..."
    
    cat > "$DOCKER_DIR/prometheus/rules/alerts.yml" << 'EOF'
groups:
  - name: ecommerce_alerts
    rules:
      # 应用宕机告警
      - alert: EcommerceAppDown
        expr: up{job="ecommerce-app"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "电商应用宕机"
          description: "电商应用已宕机超过 1 分钟"

      # 高 CPU 使用率
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "CPU 使用率超过 80% 持续 5 分钟"

      # 高内存使用率
      - alert: HighMemoryUsage
        expr: (1 - ((node_memory_MemAvailable_bytes or node_memory_MemFree_bytes) / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率超过 85% 持续 5 分钟"

      # 磁盘空间不足
      - alert: LowDiskSpace
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "磁盘空间不足"
          description: "磁盘使用率超过 90%"

      # MySQL 连接数过高
      - alert: MySQLHighConnections
        expr: mysql_global_status_threads_connected / mysql_global_variables_max_connections * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "MySQL 连接数过高"
          description: "MySQL 连接数超过最大值的 80%"

      # Redis 内存使用过高
      - alert: RedisHighMemoryUsage
        expr: (redis_memory_used_bytes / redis_memory_max_bytes) * 100 > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis 内存使用过高"
          description: "Redis 内存使用率超过 90%"

      # HTTP 错误率高
      - alert: HighHTTPErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100 > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "HTTP 错误率过高"
          description: "HTTP 5xx 错误率超过 5%"

      # 响应时间过长
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过长"
          description: "95% 请求响应时间超过 2 秒"
EOF

    log_success "告警规则配置完成"
}

# ============================================
# 构建镜像
# ============================================
build_images() {
    log_info "构建 Docker 镜像..."
    
    cd "$DOCKER_DIR"
    
    # 构建应用镜像
    if [ -f "$PROJECT_DIR/requirements.txt" ] || [ -f "$PROJECT_DIR/main.py" ]; then
        log_info "构建应用镜像..."
        docker-compose build --no-cache app
    else
        log_warn "未找到应用代码，跳过应用镜像构建"
        log_info "请确保项目根目录包含 requirements.txt 和 main.py"
    fi
    
    log_success "镜像构建完成"
}

# ============================================
# 启动服务
# ============================================
start_services() {
    log_info "启动服务..."
    
    cd "$DOCKER_DIR"
    
    # 拉取基础镜像
    docker-compose pull
    
    # 启动服务
    docker-compose up -d
    
    log_success "服务已启动"
}

# ============================================
# 等待服务就绪
# ============================================
wait_for_services() {
    log_info "等待服务就绪..."
    
    local services=("mysql" "redis" "rabbitmq" "app")
    local ports=($DEFAULT_MYSQL_PORT $DEFAULT_REDIS_PORT $DEFAULT_RABBITMQ_MGMT_PORT $DEFAULT_APP_PORT)
    
    for i in "${!services[@]}"; do
        local service=${services[$i]}
        local port=${ports[$i]}
        local max_attempts=30
        local attempt=1
        
        log_info "等待 $service 就绪..."
        
        while [ $attempt -le $max_attempts ]; do
            if docker-compose ps | grep -q "$service.*Up"; then
                log_success "$service 已就绪"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                log_error "$service 启动超时"
                break
            fi
            
            sleep 2
            ((attempt++))
        done
    done
}

# ============================================
# 显示服务状态
# ============================================
show_status() {
    log_info "服务状态:"
    echo
    
    cd "$DOCKER_DIR"
    docker-compose ps
    
    echo
    log_success "部署完成!"
    echo
    echo -e "${BLUE}访问地址:${NC}"
    echo -e "  应用:        http://localhost:${DEFAULT_APP_PORT}"
    echo -e "  Nginx:       http://localhost:80"
    echo -e "  Grafana:     http://localhost:${DEFAULT_GRAFANA_PORT} (admin/admin123)"
    echo -e "  Prometheus:  http://localhost:${DEFAULT_PROMETHEUS_PORT}"
    echo -e "  RabbitMQ:    http://localhost:${DEFAULT_RABBITMQ_MGMT_PORT}"
    echo
    echo -e "${BLUE}常用命令:${NC}"
    echo -e "  查看日志:    docker-compose logs -f [service]"
    echo -e "  停止服务:    docker-compose down"
    echo -e "  重启服务:    docker-compose restart [service]"
    echo -e "  扩展实例:    docker-compose up -d --scale app=3"
    echo
}

# ============================================
# 清理资源
# ============================================
cleanup() {
    log_warn "清理所有资源..."
    
    cd "$DOCKER_DIR"
    docker-compose down -v --remove-orphans
    
    read -p "是否删除数据卷? 这将丢失所有数据! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        log_success "数据卷已清理"
    fi
    
    log_success "清理完成"
}

# ============================================
# 显示帮助
# ============================================
show_help() {
    echo "电商自动化系统部署脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  deploy    完整部署 (默认)"
    echo "  build     仅构建镜像"
    echo "  start     启动服务"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  status    查看状态"
    echo "  logs      查看日志"
    echo "  cleanup   清理所有资源"
    echo "  help      显示帮助"
    echo
}

# ============================================
# 主函数
# ============================================
main() {
    local command=${1:-deploy}
    
    case "$command" in
        deploy)
            check_dependencies
            generate_env_file
            setup_directories
            setup_nginx
            setup_grafana
            setup_alerting
            build_images
            start_services
            wait_for_services
            show_status
            ;;
        build)
            check_dependencies
            build_images
            ;;
        start)
            check_dependencies
            start_services
            show_status
            ;;
        stop)
            cd "$DOCKER_DIR" && docker-compose down
            log_success "服务已停止"
            ;;
        restart)
            cd "$DOCKER_DIR" && docker-compose restart
            log_success "服务已重启"
            ;;
        status)
            cd "$DOCKER_DIR" && docker-compose ps
            ;;
        logs)
            shift
            cd "$DOCKER_DIR" && docker-compose logs -f "$@"
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
