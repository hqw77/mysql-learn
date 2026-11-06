-- ==========================================
-- 1. 创建数据库
-- ==========================================
CREATE DATABASE IF NOT EXISTS test_db DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;

USE test_db;

-- ==========================================
-- 2. 删除旧表（注意：会删除原有数据）
-- 按照外键依赖关系,先删除关联表
-- ==========================================
DROP TABLE IF EXISTS orders;

DROP TABLE IF EXISTS user_role;

DROP TABLE IF EXISTS role;

DROP TABLE IF EXISTS user;

-- ==========================================
-- 3. 创建用户表
-- ==========================================
CREATE TABLE user (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码哈希',
    email VARCHAR(100) NOT NULL COMMENT '邮箱',
    age TINYINT UNSIGNED DEFAULT NULL COMMENT '年龄',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1正常,0禁用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    KEY idx_status (status),
    KEY idx_created_at (created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户表';

-- ==========================================
-- 4. 创建角色表
-- ==========================================
CREATE TABLE role (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '角色ID',
    role_name VARCHAR(50) NOT NULL COMMENT '角色名称',
    role_code VARCHAR(50) NOT NULL COMMENT '角色编码',
    description VARCHAR(255) DEFAULT NULL COMMENT '角色描述',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_name (role_name),
    UNIQUE KEY uk_role_code (role_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '角色表';

-- ==========================================
-- 5. 创建用户角色关联表
-- 用户与角色：多对多
-- ==========================================
CREATE TABLE user_role (
    user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    role_id BIGINT UNSIGNED NOT NULL COMMENT '角色ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '关联时间',
    PRIMARY KEY (user_id, role_id),
    KEY idx_role_id (role_id),
    CONSTRAINT fk_user_role_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_user_role_role FOREIGN KEY (role_id) REFERENCES role (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户角色关联表';

-- ==========================================
-- 6. 创建订单表
-- 用户与订单：一对多
-- ==========================================
CREATE TABLE orders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单ID',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '所属用户ID',
    order_no VARCHAR(64) NOT NULL COMMENT '订单编号',
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '订单金额',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '订单状态：0待支付,1已支付,2已取消,3已完成',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_order_no (order_no),
    KEY idx_user_id (user_id),
    KEY idx_status_created_at (status, created_at),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_orders_amount CHECK (total_amount >= 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '订单表';

-- ==========================================
-- 7. 初始化角色数据
-- ==========================================
INSERT INTO
    role (
        role_name,
        role_code,
        description
    )
VALUES ('管理员', 'ADMIN', '系统管理员'),
    ('普通用户', 'USER', '普通用户'),
    ('运营人员', 'OPERATOR', '运营管理人员');

-- ==========================================
-- 8. 初始化用户数据（仅用于学习测试）
-- 实际项目中 password 应存储安全哈希
-- ==========================================
INSERT INTO
    user (
        username,
        password,
        email,
        age
    )
VALUES (
        'admin',
        '请替换为密码哈希',
        'admin@example.com',
        25
    ),
    (
        'zhangsan',
        '请替换为密码哈希',
        'zhangsan@example.com',
        22
    ),
    (
        'lisi',
        '请替换为密码哈希',
        'lisi@example.com',
        28
    );

-- ==========================================
-- 9. 初始化用户角色关联
-- ==========================================
INSERT INTO
    user_role (user_id, role_id)
VALUES (1, 1),
    (2, 2),
    (3, 2),
    (3, 3);

-- ==========================================
-- 10. 初始化订单数据
-- ==========================================
INSERT INTO
    orders (
        user_id,
        order_no,
        total_amount,
        status
    )
VALUES (
        2,
        'ORDER202610010001',
        99.00,
        1
    ),
    (
        2,
        'ORDER202610010002',
        199.00,
        0
    ),
    (
        3,
        'ORDER202610010003',
        299.00,
        3
    );

-- ==========================================
-- 11. 查看建库结果
-- ==========================================
SHOW TABLES;

DESC user;

DESC role;

DESC user_role;

DESC orders;