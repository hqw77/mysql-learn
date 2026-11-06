USE learn_mysql;

-- 清空旧数据,防止主键冲突
TRUNCATE TABLE order_items;

TRUNCATE TABLE orders;

TRUNCATE TABLE products;

TRUNCATE TABLE users;

-- 1. 插入用户
INSERT INTO
    users (id, username, phone, balance)
VALUES (
        1,
        '张三',
        '13800000001',
        1000.00
    ),
    (
        2,
        '李四',
        '13800000002',
        500.00
    ),
    (3, '王五', '13800000003', 0.00);
-- 王五没钱,也没买过东西

-- 2. 插入商品
INSERT INTO
    products (id, title, price)
VALUES (1, '机械键盘', 299.00),
    (2, '无线鼠标', 99.00),
    (3, '显示器', 1200.00);

-- 3. 插入订单 (张三买了 2 个订单,李四买了 1 个)
INSERT INTO
    orders (
        id,
        order_no,
        user_id,
        total_amount
    )
VALUES (1, 'ORD001', 1, 398.00),
    (2, 'ORD002', 1, 1200.00),
    (3, 'ORD003', 2, 299.00);

-- 4. 插入订单明细
INSERT INTO
    order_items (
        order_id,
        product_id,
        quantity,
        price
    )
VALUES (1, 1, 1, 299.00), -- 订单1 买了键盘
    (1, 2, 1, 99.00), -- 订单1 买了鼠标
    (2, 3, 1, 1200.00), -- 订单2 买了显示器
    (3, 1, 1, 299.00);
-- 订单3 买了键盘