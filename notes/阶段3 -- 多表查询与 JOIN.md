## <font style="color:rgb(15, 17, 21);">1. 核心目标</font>
+ <font style="color:rgb(15, 17, 21);">掌握 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">INNER JOIN</font>`<font style="color:rgb(15, 17, 21);">、</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">LEFT JOIN</font>`<font style="color:rgb(15, 17, 21);"> 的本质区别。</font>
+ <font style="color:rgb(15, 17, 21);">能用 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">GROUP BY</font>`<font style="color:rgb(15, 17, 21);"> + 聚合函数进行业务数据统计。</font>
+ <font style="color:rgb(15, 17, 21);">能用 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">子查询</font>`<font style="color:rgb(15, 17, 21);"> 解决嵌套逻辑，用 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">UNION</font>`<font style="color:rgb(15, 17, 21);"> 合并结果。</font>
+ <font style="color:rgb(15, 17, 21);">掌握 MySQL 8.0 的 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">窗口函数</font>`<font style="color:rgb(15, 17, 21);">，解决排名问题。</font>

## <font style="color:rgb(15, 17, 21);">2. 准备工作：准备测试数据</font>
<font style="color:rgb(15, 17, 21);">为了练手，我们需要往阶段 2 建好的电商四表（</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">users</font>`<font style="color:rgb(15, 17, 21);">、</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">products</font>`<font style="color:rgb(15, 17, 21);">、</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">orders</font>`<font style="color:rgb(15, 17, 21);">、</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">order_items</font>`<font style="color:rgb(15, 17, 21);">）里塞入一些数据。打开 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">sql/03-mock-data.sql</font>`<font style="color:rgb(15, 17, 21);">，执行以下代码：</font>

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

## <font style="color:rgb(15, 17, 21);">3. 核心语法一：JOIN 的三大类型</font>
<font style="color:rgb(15, 17, 21);">把两张表想象成两个集合，</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">JOIN</font>`<font style="color:rgb(15, 17, 21);"> 就是求交集或并集。</font>

### <font style="color:rgb(15, 17, 21);">3.1 INNER JOIN（内连接）</font>
**<font style="color:rgb(15, 17, 21);">只返回两张表中完全匹配的行。</font>**<font style="color:rgb(15, 17, 21);">（最常用，不匹配的数据直接丢弃）。</font>

```plain
-- 查询所有订单，带上对应的用户名（没有下过单的用户不会显示）
SELECT o.order_no, u.username, o.total_amount
FROM orders o
INNER JOIN users u ON o.user_id = u.id;
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793693944955-3a1277e2-b6b0-45b1-98ab-487be719dc59.png)

### <font style="color:rgb(15, 17, 21);">3.2 LEFT JOIN（左连接）</font><font style="color:rgb(15, 17, 21);">⭐⭐⭐</font>
**<font style="color:rgb(15, 17, 21);">以左表为准，左表的数据全部保留。右表如果有匹配的就拼上，没有匹配的显示为 </font>**`**<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">NULL</font>**`**<font style="color:rgb(15, 17, 21);">。</font>**

```plain
-- 查询所有用户，以及他们的订单号（即使没下过单，用户也要显示出来）
SELECT u.username, o.order_no, o.total_amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

_<font style="color:rgb(15, 17, 21);">(结果里会出现“王五”，但他的订单号显示为 </font>_`_<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">NULL</font>_`_<font style="color:rgb(15, 17, 21);">)</font>_

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694055762-bcb64082-824c-4183-9db5-81eccdd3896e.png)

### <font style="color:rgb(15, 17, 21);">3.3 RIGHT JOIN（右连接）</font>
<font style="color:rgb(15, 17, 21);">以右表为准，右表全保留。实际开发中极少用，因为把表换个位置写 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">LEFT JOIN</font>`<font style="color:rgb(15, 17, 21);"> 就完事了。</font>

## <font style="color:rgb(15, 17, 21);">4. 核心语法二：聚合与分组（GROUP BY）</font>
<font style="color:rgb(15, 17, 21);">需求：统计每个用户的总消费金额。</font>

```plain
SELECT u.username, SUM(o.total_amount) AS total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.username;
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694199137-9b9060d6-5d66-4d2f-8d9f-4e6cbd1ebac4.png)

**<font style="color:rgb(15, 17, 21);">⚠️</font>****<font style="color:rgb(15, 17, 21);"> 避坑原则</font>**<font style="color:rgb(15, 17, 21);">：在 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">SELECT</font>`<font style="color:rgb(15, 17, 21);"> 中出现的非聚合列（如 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">u.username</font>`<font style="color:rgb(15, 17, 21);">），必须全部写在 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">GROUP BY</font>`<font style="color:rgb(15, 17, 21);"> 里。</font>

**<font style="color:rgb(15, 17, 21);">WHERE vs HAVING</font>**<font style="color:rgb(15, 17, 21);">：</font>

+ `<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">WHERE</font>`<font style="color:rgb(15, 17, 21);">：在分组前过滤（不能跟聚合函数）。</font>
+ `<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">HAVING</font>`<font style="color:rgb(15, 17, 21);">：在分组后过滤（专门针对聚合结果）。</font>

```plain
-- 找出消费总额大于 500 的用户
SELECT u.username, SUM(o.total_amount) AS total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.username
HAVING total_spent > 500; -- 这里只能用 HAVING，不能用 WHERE
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694255498-f3bb79d1-29e6-4eb3-b9e5-eafb70f88377.png)

## <font style="color:rgb(15, 17, 21);">5. 核心语法三：子查询与 UNION</font>
### <font style="color:rgb(15, 17, 21);">子查询（Subquery）</font>
**<font style="color:rgb(15, 17, 21);">在一个 SQL 语句里面，嵌套另一个 SQL 语句。</font>**<font style="color:rgb(15, 17, 21);"> 就像套娃一样，里面的 SQL 先执行，把结果给外面的 SQL 用。  
</font><font style="color:rgb(15, 17, 21);">需求：查找买了“机械键盘”的用户名。</font>

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

**<font style="color:rgb(15, 17, 21);">运行结果</font>**<font style="color:rgb(15, 17, 21);">：你会查到 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">张三</font>`<font style="color:rgb(15, 17, 21);"> 和 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">李四</font>`<font style="color:rgb(15, 17, 21);">，因为他们俩的订单里都包含了键盘。</font>  
**<font style="color:rgb(15, 17, 21);">原理解释</font>**<font style="color:rgb(15, 17, 21);">：数据库的执行顺序是</font>**<font style="color:rgb(15, 17, 21);">由内向外</font>**<font style="color:rgb(15, 17, 21);">的。它先查 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">order_items</font>`<font style="color:rgb(15, 17, 21);"> 找到订单号，再查 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">orders</font>`<font style="color:rgb(15, 17, 21);"> 找到用户 ID，最后查 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">users</font>`<font style="color:rgb(15, 17, 21);"> 找到名字。</font>

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694433529-bb50c042-5c44-4756-b669-2a5ace45d020.png)

### <font style="color:rgb(15, 17, 21);">UNION（联合查询）</font>
**<font style="color:rgb(15, 17, 21);">把两个查询结果，上下拼接到一起。</font>**<font style="color:rgb(15, 17, 21);"> 要求两次查询的</font>**<font style="color:rgb(15, 17, 21);">列数必须一样</font>**<font style="color:rgb(15, 17, 21);">。</font>

```plain
SELECT username FROM users WHERE id = 1
UNION
SELECT username FROM users WHERE id = 2;
```

**<font style="color:rgb(15, 17, 21);">运行结果</font>**<font style="color:rgb(15, 17, 21);">：查出来两行数据（张三、李四）。  
</font>**<font style="color:rgb(15, 17, 21);">注意</font>**<font style="color:rgb(15, 17, 21);">：</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">UNION</font>`<font style="color:rgb(15, 17, 21);"> 会自动去重。如果你想保留所有数据（哪怕重复），用 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">UNION ALL</font>`<font style="color:rgb(15, 17, 21);">（性能更好，因为不用去重）。</font>

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793694781719-d90c7b95-5c90-4231-b917-67b94cd7d295.png)

## <font style="color:rgb(15, 17, 21);">6. 核心语法四：窗口函数（MySQL 8.0+ 高级特性）</font>
<font style="color:rgb(15, 17, 21);">窗口函数的核心就是这句万能的公式：</font>

```plain
函数名() OVER (PARTITION BY 分组字段 ORDER BY 排序字段)
```

1. `**<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">OVER (...)</font>**`<font style="color:rgb(15, 17, 21);">：划出一个“窗口”（就是数据范围），告诉 MySQL 在这个窗口里做计算。</font>
2. `**<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">ORDER BY</font>**`<font style="color:rgb(15, 17, 21);">：在窗口里怎么排序。</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">DESC</font>`<font style="color:rgb(15, 17, 21);"> 就是降序。</font>
3. `**<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">PARTITION BY</font>**`**<font style="color:rgb(15, 17, 21);">（可选）</font>**<font style="color:rgb(15, 17, 21);">：相当于在这个窗口里再次分组。比如 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">PARTITION BY category_id</font>`<font style="color:rgb(15, 17, 21);">，就是按分类分别排名，各排各的。</font>



<font style="color:rgb(15, 17, 21);">需求：给所有商品的销售总数量</font>**<font style="color:rgb(15, 17, 21);">排名</font>**<font style="color:rgb(15, 17, 21);">。  
</font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">GROUP BY</font>`<font style="color:rgb(15, 17, 21);"> 只能统计，很难保留明细。窗口函数可以在保留明细的同时进行聚合。</font>

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

+ `<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">ROW_NUMBER()</font>`<font style="color:rgb(15, 17, 21);">：生成 1, 2, 3, 4 严格序号。</font>
+ `<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">RANK()</font>`<font style="color:rgb(15, 17, 21);">：如果有并列第一，会生成 1, 1, 3（并列占位）。</font>

## <font style="color:rgb(15, 17, 21);">7. Python 实战：在代码里做多表查询</font>
<font style="color:rgb(15, 17, 21);">在 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">practice/phase3/</font>`<font style="color:rgb(15, 17, 21);"> 新建 </font>`<font style="color:rgb(15, 17, 21);background-color:rgb(235, 238, 242);">multi_table_query.py</font>`<font style="color:rgb(15, 17, 21);">（如果没有文件夹请新建）。</font>

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

<font style="color:rgb(15, 17, 21);">  
</font><font style="color:rgb(15, 17, 21);"> </font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

<font style="color:rgb(15, 17, 21);"></font>

