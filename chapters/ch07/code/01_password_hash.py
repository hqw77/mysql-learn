"""第七章 · 案例 1：密码为什么要哈希,哈希长什么样。

学到什么：
    1. 同一密码哈希两次,结果不同（因为自带随机盐）
    2. 哈希不可逆,无法从哈希还原出明文
    3. 校验时不比对字符串,而是用 verify 函数

怎么跑：
    python chapters/ch07/code/01_password_hash.py

不连数据库,纯本地计算。
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from app.core.security import hash_password, verify_password  # noqa: E402


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    raw = "secret123"

    show("① 同一个密码,哈希两次")
    h1 = hash_password(raw)
    h2 = hash_password(raw)
    print("    第一次:", h1)
    print("    第二次:", h2)
    print("    两次相同吗:", h1 == h2)
    print("    → 不同。因为 argon2 每次都会生成新的随机盐")

    show("② 哈希串的结构")
    parts = h1.split("$")
    print("    完整格式: $argon2id$v=19$m=65536,t=3,p=4$<盐值>$<哈希>")
    print("    算法    :", parts[1])
    print("    版本    :", parts[2])
    print("    参数    :", parts[3], " (内存 64MB,迭代 3 次,并行 4 路)")
    print("    盐值    :", parts[4])
    print("    哈希值  :", parts[5])
    print("    盐和参数都写在哈希串里,所以不需要单独存盐字段")

    show("③ 校验：正确密码 vs 错误密码")
    print("    正确密码 secret123 →", verify_password("secret123", h1))
    print("    错误密码 secret124 →", verify_password("secret124", h1))
    print("    空密码            →", verify_password("", h1))

    show("④ 哈希不可逆")
    print("    哈希串长度:", len(h1))
    print("    明文长度  :", len(raw))
    print("    → 哈希后长度固定且远大于明文,无法反推出原文")

    show("⑤ 耗时：故意让暴力破解变慢")
    start = time.perf_counter()
    for _ in range(5):
        hash_password(raw)
    cost = (time.perf_counter() - start) / 5
    print(f"    单次哈希约 {cost * 1000:.1f} ms")
    print("    → 正常登录只算一次,感觉不到；但暴力猜测每秒只能试几十次")

    show("⑥ 空哈希（历史数据）会怎样")
    print("    verify_password('secret123', '') →", verify_password("secret123", ""))
    print("    → 返回 False,不抛异常。老数据没有密码时登录会被拒绝")
