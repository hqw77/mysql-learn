USE learn_mysql;

-- 删除旧表
DROP TABLE IF EXISTS big_users;

-- 创建一张大表（注意：先不加任何索引）
CREATE TABLE big_users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, -- id 默认是主键索引
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    city VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

-- 用代码快速插入 10 万条数据（通过 MySQL 的存储过程/循环，或者多行插入）
-- 这里用纯 SQL 快速生成
INSERT INTO
    big_users (username, email, age, city)
SELECT CONCAT('user_', n), CONCAT('user_', n, '@test.com'), FLOOR(18 + (RAND() * 40)), -- 随机 18~58 岁
    ELT(
        1 + FLOOR(RAND() * 5), '北京', '上海', '广州', '深圳', '杭州'
    ) -- 随机城市
FROM (
        SELECT a.n + b.n * 10 + c.n * 100 + d.n * 1000 + e.n * 10000 AS n
        FROM (
                SELECT 0 AS n
                UNION
                SELECT 1
                UNION
                SELECT 2
                UNION
                SELECT 3
                UNION
                SELECT 4
                UNION
                SELECT 5
                UNION
                SELECT 6
                UNION
                SELECT 7
                UNION
                SELECT 8
                UNION
                SELECT 9
            ) a
            CROSS JOIN (
                SELECT 0 AS n
                UNION
                SELECT 1
                UNION
                SELECT 2
                UNION
                SELECT 3
                UNION
                SELECT 4
                UNION
                SELECT 5
                UNION
                SELECT 6
                UNION
                SELECT 7
                UNION
                SELECT 8
                UNION
                SELECT 9
            ) b
            CROSS JOIN (
                SELECT 0 AS n
                UNION
                SELECT 1
                UNION
                SELECT 2
                UNION
                SELECT 3
                UNION
                SELECT 4
                UNION
                SELECT 5
                UNION
                SELECT 6
                UNION
                SELECT 7
                UNION
                SELECT 8
                UNION
                SELECT 9
            ) c
            CROSS JOIN (
                SELECT 0 AS n
                UNION
                SELECT 1
                UNION
                SELECT 2
                UNION
                SELECT 3
                UNION
                SELECT 4
                UNION
                SELECT 5
                UNION
                SELECT 6
                UNION
                SELECT 7
                UNION
                SELECT 8
                UNION
                SELECT 9
            ) d
            CROSS JOIN (
                SELECT 0 AS n
                UNION
                SELECT 1
                UNION
                SELECT 2
                UNION
                SELECT 3
                UNION
                SELECT 4
                UNION
                SELECT 5
                UNION
                SELECT 6
                UNION
                SELECT 7
                UNION
                SELECT 8
                UNION
                SELECT 9
            ) e
    ) t;

-- 验证数据量（应该有 100000 条）
SELECT COUNT(*) FROM big_users;