-- 电商自动化系统数据库表结构
-- MySQL 8.0

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    status ENUM('active', 'inactive', 'banned') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 商品分类表
CREATE TABLE IF NOT EXISTS categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL COMMENT '分类名称',
    parent_id INT UNSIGNED DEFAULT 0 COMMENT '父分类ID',
    level TINYINT UNSIGNED DEFAULT 1 COMMENT '层级',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id),
    INDEX idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 商品表
CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE COMMENT 'SKU编码',
    name VARCHAR(255) NOT NULL COMMENT '商品名称',
    category_id INT UNSIGNED COMMENT '分类ID',
    description TEXT COMMENT '商品描述',
    price DECIMAL(10, 2) NOT NULL COMMENT '售价',
    cost_price DECIMAL(10, 2) COMMENT '成本价',
    stock INT UNSIGNED DEFAULT 0 COMMENT '库存数量',
    stock_warning INT UNSIGNED DEFAULT 10 COMMENT '库存预警值',
    status ENUM('active', 'inactive', 'deleted') DEFAULT 'active' COMMENT '状态',
    platform ENUM('taobao', 'jd', 'pdd', 'douyin', 'all') DEFAULT 'all' COMMENT '适用平台',
    ai_optimized BOOLEAN DEFAULT FALSE COMMENT '是否AI优化',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sku (sku),
    INDEX idx_category (category_id),
    INDEX idx_status (status),
    INDEX idx_platform (platform),
    FOREIGN KEY (category_id) REFERENCES categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(32) NOT NULL UNIQUE COMMENT '订单编号',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    platform ENUM('taobao', 'jd', 'pdd', 'douyin') NOT NULL COMMENT '平台',
    status ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded') DEFAULT 'pending' COMMENT '状态',
    total_amount DECIMAL(10, 2) NOT NULL COMMENT '订单总金额',
    discount_amount DECIMAL(10, 2) DEFAULT 0 COMMENT '优惠金额',
    shipping_fee DECIMAL(10, 2) DEFAULT 0 COMMENT '运费',
    pay_amount DECIMAL(10, 2) NOT NULL COMMENT '实付金额',
    receiver_name VARCHAR(50) COMMENT '收货人姓名',
    receiver_phone VARCHAR(20) COMMENT '收货人电话',
    receiver_address TEXT COMMENT '收货地址',
    tracking_no VARCHAR(50) COMMENT '快递单号',
    carrier VARCHAR(20) COMMENT '快递公司',
    risk_score DECIMAL(3, 2) DEFAULT 0 COMMENT '风控评分',
    remark TEXT COMMENT '备注',
    paid_at TIMESTAMP NULL COMMENT '支付时间',
    shipped_at TIMESTAMP NULL COMMENT '发货时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_no (order_no),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_platform (platform),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 订单商品表
CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
    product_id BIGINT UNSIGNED NOT NULL COMMENT '商品ID',
    sku VARCHAR(50) NOT NULL COMMENT 'SKU',
    product_name VARCHAR(255) NOT NULL COMMENT '商品名称',
    quantity INT UNSIGNED NOT NULL COMMENT '数量',
    unit_price DECIMAL(10, 2) NOT NULL COMMENT '单价',
    total_price DECIMAL(10, 2) NOT NULL COMMENT '总价',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单商品表';

-- 库存记录表
CREATE TABLE IF NOT EXISTS inventory_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL COMMENT '商品ID',
    type ENUM('in', 'out', 'adjust') NOT NULL COMMENT '类型：入库/出库/调整',
    quantity INT NOT NULL COMMENT '数量（正数入库，负数出库）',
    before_stock INT UNSIGNED COMMENT '变动前库存',
    after_stock INT UNSIGNED COMMENT '变动后库存',
    reference_type VARCHAR(50) COMMENT '关联类型：order/purchase/adjust',
    reference_id VARCHAR(50) COMMENT '关联ID',
    operator VARCHAR(50) COMMENT '操作人',
    remark TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id),
    INDEX idx_type (type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存记录表';

-- 客服对话表
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
    customer_id VARCHAR(50) NOT NULL COMMENT '客户ID',
    platform ENUM('taobao', 'jd', 'pdd', 'douyin') NOT NULL COMMENT '平台',
    message TEXT NOT NULL COMMENT '客户消息',
    response TEXT COMMENT '回复内容',
    intent VARCHAR(50) COMMENT '意图分类',
    confidence DECIMAL(3, 2) COMMENT '置信度',
    ai_handled BOOLEAN DEFAULT TRUE COMMENT '是否AI处理',
    escalated BOOLEAN DEFAULT FALSE COMMENT '是否转人工',
    satisfaction INT COMMENT '满意度评分 1-5',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_platform (platform),
    INDEX idx_created_at (created_at),
    INDEX idx_ai_handled (ai_handled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客服对话表';

-- 价格监控表
CREATE TABLE IF NOT EXISTS price_monitor (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL COMMENT '商品ID',
    platform ENUM('taobao', 'jd', 'pdd', 'douyin') NOT NULL COMMENT '平台',
    competitor_url VARCHAR(500) COMMENT '竞品链接',
    competitor_price DECIMAL(10, 2) COMMENT '竞品价格',
    our_price DECIMAL(10, 2) COMMENT '我们的价格',
    price_diff DECIMAL(10, 2) COMMENT '价格差',
    price_diff_percent DECIMAL(5, 2) COMMENT '价格差百分比',
    recommend_price DECIMAL(10, 2) COMMENT '建议价格',
    is_lower BOOLEAN DEFAULT FALSE COMMENT '我们是否更低',
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
    INDEX idx_product_id (product_id),
    INDEX idx_platform (platform),
    INDEX idx_checked_at (checked_at),
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='价格监控表';

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_configs (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(50) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '描述',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO system_configs (config_key, config_value, description) VALUES
('auto_fulfill', 'true', '是否自动发货'),
('risk_threshold', '0.8', '风控阈值'),
('stock_warning', '10', '库存预警值'),
('price_monitor_interval', '3600', '价格监控间隔（秒）'),
('ai_temperature', '0.7', 'AI 温度参数');

-- 插入默认分类
INSERT INTO categories (name, parent_id, level) VALUES
('数码家电', 0, 1),
('手机通讯', 1, 2),
('电脑办公', 1, 2),
('服装鞋包', 0, 1),
('男装', 4, 2),
('女装', 4, 2),
('美妆护肤', 0, 1),
('家居日用', 0, 1);
