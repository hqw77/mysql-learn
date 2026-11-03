## 1. 核心目标
+ 掌握 `INNER JOIN`、`LEFT JOIN` 的本质区别。
+ 能用 `GROUP BY` + 聚合函数进行业务数据统计。
+ 能用 `子查询` 解决嵌套逻辑，用 `UNION` 合并结果。
+ 掌握 MySQL 8.0 的 `窗口函数`，解决排名问题。

## 2. 准备工作：准备测试数据
为了练手，我们需要往阶段 2 建好的电商四表（`users`、`products`、`orders`、`order_items`）里塞入一些数据。打开 `sql/03-mock-data.sql`，执行以下代码：

```plain
USE learn_mysql;

-- 清空旧数据，防止主键冲突
TRUNCATE TABLE order_items;
TRUNCATE TABLE orders;
TRUNCATE TABLE products;
TRUNCATE TABLE users;

-- 1. 插入用户
INSERT INTO users (id, username, phone, balance) VALUES 
(1, '张三', '13800000001', 1000.00),
(2, '李四', '13800000002', 500.00),
(3, '王五', '13800000003', 0.00); -- 王五没钱，也没买过东西

-- 2. 插入商品
INSERT INTO products (id, title, price) VALUES 
(1, '机械键盘', 299.00),
(2, '无线鼠标', 99.00),
(3, '显示器', 1200.00);

-- 3. 插入订单 (张三买了 2 个订单，李四买了 1 个)
INSERT INTO orders (id, order_no, user_id, total_amount) VALUES 
(1, 'ORD001', 1, 398.00),
(2, 'ORD002', 1, 1200.00),
(3, 'ORD003', 2, 299.00);

-- 4. 插入订单明细
INSERT INTO order_items (order_id, product_id, quantity, price) VALUES 
(1, 1, 1, 299.00), -- 订单1 买了键盘
(1, 2, 1, 99.00),  -- 订单1 买了鼠标
(2, 3, 1, 1200.00),-- 订单2 买了显示器
(3, 1, 1, 299.00); -- 订单3 买了键盘
```

user

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793693977837-164fbd8f-b26f-4cd8-a188-06b2539d890c.png)

products

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793693992632-7c4c466e-d55c-4599-a439-61a04aaca7d0.png)

orders

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694004121-a5339237-7a05-4501-925a-6559d19dad55.png)

order_items

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694022091-e6e940e2-6e6a-400e-9716-2dfda1ee76fa.png)

## 3. 核心语法一：JOIN 的三大类型
把两张表想象成两个集合，`JOIN` 就是求交集或并集。

### 3.1 INNER JOIN（内连接）
**只返回两张表中完全匹配的行。**（最常用，不匹配的数据直接丢弃）。

```plain
-- 查询所有订单，带上对应的用户名（没有下过单的用户不会显示）
SELECT o.order_no, u.username, o.total_amount
FROM orders o
INNER JOIN users u ON o.user_id = u.id;
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793693944955-3a1277e2-b6b0-45b1-98ab-487be719dc59.png)

### 3.2 LEFT JOIN（左连接）⭐⭐⭐
**以左表为准，左表的数据全部保留。右表如果有匹配的就拼上，没有匹配的显示为 **`NULL`**。**

```plain
-- 查询所有用户，以及他们的订单号（即使没下过单，用户也要显示出来）
SELECT u.username, o.order_no, o.total_amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

_(结果里会出现“王五”，但他的订单号显示为 _`_NULL_`_)_

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694055762-bcb64082-824c-4183-9db5-81eccdd3896e.png)

### 3.3 RIGHT JOIN（右连接）
以右表为准，右表全保留。实际开发中极少用，因为把表换个位置写 `LEFT JOIN` 就完事了。

## 4. 核心语法二：聚合与分组（GROUP BY）
需求：统计每个用户的总消费金额。

```plain
SELECT u.username, SUM(o.total_amount) AS total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.username;
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694199137-9b9060d6-5d66-4d2f-8d9f-4e6cbd1ebac4.png)

**⚠️ 避坑原则**：在 `SELECT` 中出现的非聚合列（如 `u.username`），必须全部写在 `GROUP BY` 里。

**WHERE vs HAVING**：

+ `WHERE`：在分组前过滤（不能跟聚合函数）。
+ `HAVING`：在分组后过滤（专门针对聚合结果）。

```plain
-- 找出消费总额大于 500 的用户
SELECT u.username, SUM(o.total_amount) AS total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.username
HAVING total_spent > 500; -- 这里只能用 HAVING，不能用 WHERE
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694255498-f3bb79d1-29e6-4eb3-b9e5-eafb70f88377.png)

## 5. 核心语法三：子查询与 UNION
### 子查询（Subquery）
**在一个 SQL 语句里面，嵌套另一个 SQL 语句。** 就像套娃一样，里面的 SQL 先执行，把结果给外面的 SQL 用。  
需求：查找买了“机械键盘”的用户名。

```plain
USE learn_mysql;

-- 需求：查找买了“机械键盘”的用户名
SELECT username FROM users 
WHERE id IN (
    -- 第一层子查询：从订单表里找出买过键盘的 user_id
    SELECT user_id FROM orders 
    WHERE id IN (
        -- 第二层子查询：从明细表里找出 product_id 为 1（键盘）的 order_id
        SELECT order_id FROM order_items WHERE product_id = 1
    )
);
```

**运行结果**：你会查到 `张三` 和 `李四`，因为他们俩的订单里都包含了键盘。  
**原理解释**：数据库的执行顺序是**由内向外**的。它先查 `order_items` 找到订单号，再查 `orders` 找到用户 ID，最后查 `users` 找到名字。

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694433529-bb50c042-5c44-4756-b669-2a5ace45d020.png)

### UNION（联合查询）
**把两个查询结果，上下拼接到一起。** 要求两次查询的**列数必须一样**。

```plain
SELECT username FROM users WHERE id = 1
UNION
SELECT username FROM users WHERE id = 2;
```

**运行结果**：查出来两行数据（张三、李四）。  
**注意**：`UNION` 会自动去重。如果你想保留所有数据（哪怕重复），用 `UNION ALL`（性能更好，因为不用去重）。

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694781719-d90c7b95-5c90-4231-b917-67b94cd7d295.png)

## 6. 核心语法四：窗口函数（MySQL 8.0+ 高级特性）
窗口函数的核心就是这句万能的公式：

```plain
函数名() OVER (PARTITION BY 分组字段 ORDER BY 排序字段)
```

1. `OVER (...)`：划出一个“窗口”（就是数据范围），告诉 MySQL 在这个窗口里做计算。
2. `ORDER BY`：在窗口里怎么排序。`DESC` 就是降序。
3. `PARTITION BY`**（可选）**：相当于在这个窗口里再次分组。比如 `PARTITION BY category_id`，就是按分类分别排名，各排各的。



需求：给所有商品的销售总数量**排名**。  
`GROUP BY` 只能统计，很难保留明细。窗口函数可以在保留明细的同时进行聚合。

```plain
-- 统计每个商品的销量并排名
SELECT 
    p.title,
    SUM(oi.quantity) AS total_sold,
    ROW_NUMBER() OVER (ORDER BY SUM(oi.quantity) DESC) AS rank_num
FROM products p
LEFT JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.title;
```

+ `ROW_NUMBER()`：生成 1, 2, 3, 4 严格序号。
+ `RANK()`：如果有并列第一，会生成 1, 1, 3（并列占位）。

## 7. Python 实战：在代码里做多表查询
在 `practice/phase3/` 新建 `multi_table_query.py`（如果没有文件夹请新建）。

```plain
import pymysql
from pymysql.cursors import DictCursor

conn = pymysql.connect(
    host="localhost", user="root", password="你的密码",
    database="learn_mysql", charset="utf8mb4"
)

def query_report():
    with conn.cursor(cursor=DictCursor) as cur:
        # 复杂业务：查询每个用户的姓名、订单数、总消费额（包含没下过单的用户）
        sql = """
        SELECT 
            u.username, 
            COUNT(o.id) AS order_count, 
            IFNULL(SUM(o.total_amount), 0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.username
        ORDER BY total_spent DESC;
        """
        cur.execute(sql)
        results = cur.fetchall()
        
        print(f"{'用户名':<10} | {'订单数':<6} | {'总消费额':<10}")
        print("-" * 35)
        for row in results:
            # IFNULL 处理了 NULL 的情况，所以可以直接打印
            print(f"{row['username']:<10} | {row['order_count']:<8} | {row['total_spent']:<10}")

try:
    query_report()
finally:
    conn.close()
```

  
 























