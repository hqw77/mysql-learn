-- 增加列
ALTER TABLE users ADD email VARCHAR(100) AFTER phone;
-- 修改列类型
ALTER TABLE users MODIFY phone VARCHAR(20) NOT NULL;
-- 删除列（生产慎用）
ALTER TABLE users DROP email;
-- 修改表名
ALTER TABLE users RENAME TO sys_users;

ALTER TABLE sys_users RENAME TO users;