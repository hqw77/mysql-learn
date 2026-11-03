use learn_mysql;

SELECT u.username, SUM(o.total_amount) AS total_spent
FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
GROUP BY
    u.id,
    u.username;

-- 找出消费总额大于 500 的用户
SELECT u.username, SUM(o.total_amount) AS total_spent
FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
GROUP BY
    u.id,
    u.username
HAVING
    total_spent > 500;
-- 这里只能用 HAVING，不能用 WHERE