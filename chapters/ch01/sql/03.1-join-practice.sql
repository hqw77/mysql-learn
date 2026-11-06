USE learn_mysql;

-- 查询所有订单,带上对应的用户名
SELECT o.order_no, u.username, o.total_amount
FROM orders o
    INNER JOIN users u ON o.user_id = u.id;

-- 查询所有用户,以及他们的订单号（即使没下过单,用户也要显示出来）
SELECT u.username, o.order_no, o.total_amount
FROM users u
    LEFT JOIN orders o ON u.id = o.user_id;