USE learn_mysql;

-- 插入单条（指定所有列）
INSERT INTO students (name, age, score) VALUES ('张三', 20, 85.5);
-- 插入单条（不指定列，必须按表结构顺序给全）
INSERT INTO students VALUES (NULL, '李四', 19, 92.0, NOW());
-- 批量插入（性能更好，推荐用）
INSERT INTO
    students (name, age, score)
VALUES ('王五', 21, 78.0),
    ('赵六', 22, 88.5);

-- 查所有
SELECT * FROM students;
-- 条件查（找分数大于 80 的）
SELECT name, score FROM students WHERE score > 80;
-- 排序 + 分页（按分数降序，取前 2 个）
SELECT * FROM students ORDER BY score DESC LIMIT 2;

-- 把张三的分数改成 90（一定要带 WHERE，否则全表都被改）
UPDATE students SET score = 90.0 WHERE name = '张三';

-- 删除名字叫李四的记录（同样一定要带 WHERE）
DELETE FROM students WHERE name = '李四';