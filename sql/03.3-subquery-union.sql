USE learn_mysql;

-- 需求：查找买了“机械键盘”的用户名
SELECT username
FROM users
WHERE
    id IN (
        -- 第一层子查询：从订单表里找出买过键盘的 user_id
        SELECT user_id
        FROM orders
        WHERE
            id IN (
                -- 第二层子查询：从明细表里找出 product_id 为 1（键盘）的 order_id
                SELECT order_id
                FROM order_items
                WHERE
                    product_id = 1
            )
    );

-- 需求：把 ID 为 1 的用户 和 ID 为 2 的用户拼在一起查出来
SELECT username, phone
FROM users
WHERE
    id = 1
UNION
SELECT username, phone
FROM users
WHERE
    id = 2;