USE learn_mysql;

-- 先删除（注意顺序：先删子表,再删父表）
DROP TABLE IF EXISTS borrows;

DROP TABLE IF EXISTS books;

DROP TABLE IF EXISTS readers;

DROP TABLE IF EXISTS authors;

-- 1. 作者表 (authors)
CREATE TABLE authors (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '作者主键',
    name VARCHAR(50) NOT NULL COMMENT '作者姓名',
    bio TEXT COMMENT '作者简介'
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '作者表';

-- 2. 图书表 (books)
CREATE TABLE books (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '图书主键',
    title VARCHAR(100) NOT NULL COMMENT '书名',
    author_id INT UNSIGNED NOT NULL COMMENT '关联作者ID',
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '价格',
    publish_date DATE COMMENT '出版日期',
    stock INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '库存',
    -- 使用 CHECK 约束保证库存不为负数 (MySQL 8.0.16+ 生效)
    CONSTRAINT chk_stock CHECK (stock >= 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '图书表';

-- 3. 读者表 (readers)
CREATE TABLE readers (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '读者主键',
    name VARCHAR(50) NOT NULL COMMENT '读者姓名',
    phone CHAR(11) NOT NULL UNIQUE COMMENT '手机号,唯一约束',
    join_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册日期'
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '读者表';

-- 4. 借阅记录表 (borrows)
CREATE TABLE borrows (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '借阅主键',
    reader_id INT UNSIGNED NOT NULL COMMENT '关联读者ID',
    book_id INT UNSIGNED NOT NULL COMMENT '关联图书ID',
    borrow_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '借出时间',
    return_date DATETIME DEFAULT NULL COMMENT '归还时间,可空（NULL表示还没还）'
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '借阅记录表';