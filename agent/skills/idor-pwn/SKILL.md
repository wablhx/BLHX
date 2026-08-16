---
name: idor-pwn
description: IDOR/BOLA越权漏洞挖掘——对象引用替换、批量操作、路径Body不匹配、WebSocket。Use when 看到user_id/对象引用参数/订单ID/文件下载ID。
---

# IDOR / BOLA 越权挖掘

> 蒸馏自CC挖洞武器库 idor-完整手册 + idor-2025-2026-supplement（实战验证）

## 核心认知

IDOR = 应用信任客户端提供的对象标识（ID），未校验归属 → 替换他人ID越权。
**出货率最高的SRC漏洞类型**（通过率85%+，赏金¥400-1800）。

## 快速检查清单（拿到目标后30秒）

1. 找所有带ID的参数：user_id/order_id/file_id/doc_id/attachment_id/uid
2. 双账号注册：A/B两个账号，收集各自ID
3. 交叉替换：用A的请求头/Cookie，把ID换成B的
4. 观察响应差异：B的数据出现在A的响应里 = IDOR确认

## 12种绕过技术（基础被拦时）

| # | 技术 | 方法 |
|---|---|---|
| 1 | 参数污染 | `?id=1&id=2`、`?id[]=1&id[]=2` |
| 2 | 批量操作 | 批量删除/收藏/导出接口（常漏鉴权） |
| 3 | WebSocket | 实时通信通道（常不鉴权） |
| 4 | 路径Body不匹配 | GET /order/{self} + body传victim_id |
| 5 | Cache-Key混淆 | CDN缓存：租户ID放不同位置 |
| 6 | BOPLA | 改对象属性（如isAdmin字段） |
| 7 | 异步任务 | 任务ID可枚举（job_id） |
| 8 | 双ID收集 | 注册多账号收集ID池 |
| 9 | GUID不可预测 | 找第二端点泄露（me/别名） |
| 10 | 302重定向泄露 | 盲IDOR：响应302+Location泄露 |
| 11 | 多步骤越权 | 步骤间跳步/改步骤参数 |
| 12 | Referer绕过 | 仅检查Referer的端点 |

## 实战验证命令

```bash
# 替换ID测试（A账号Cookie访问B的订单）
curl -b "session=A" "https://target/api/order/1002" -o /tmp/a.txt
curl -b "session=A" "https://target/api/order/1003" -o /tmp/b.txt  # 1003是B的
diff /tmp/a.txt /tmp/b.txt   # 有差异 = 越权

# 批量接口（常漏鉴权）
curl -b "session=A" "https://target/api/orders/batch-delete" -X POST -d '{"ids":[1002,1003]}'

# 路径Body不匹配
curl -b "session=A" "https://target/api/order/1002" -X PUT -d '{"order_id":1003,"status":"paid"}'
```

## 加密接口变体（金融/政务）

请求全加密时：JS找加密函数（AresCrypto.encrypt/decrypt）→ 断点固定动态key → 改参数动态加密 → 解密响应 → 越权。详见 cloud/加密接口章节。

## 提交要点

- 危害描述：能读取他人订单/个人信息/文件 = 中危起步
- 证据：A账号请求 + B账号数据响应 同屏截图
- 平台：补天/漏洞盒子均可，选"越权访问/IDOR"
