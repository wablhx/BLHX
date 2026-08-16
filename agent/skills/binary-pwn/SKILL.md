---
name: binary-pwn
description: 二进制漏洞挖掘——逆向分析/栈溢出/格式化串/ret2win。Use when 看到ELF/二进制文件/需要逆向/反编译/内存破坏。
---

# 二进制漏洞挖掘

> 蒸馏自社区二进制CTF打法 + ljagiello/ctf-skills（2994★，MIT）
> 完整知识库见 references/（36个文件：overflow/ROP/format-string/heap/kernel/anti-analysis）

## 保护策略决策树（最重要）

| 防护 | 状态 | 利用策略 |
|---|---|---|
| PIE | Disabled | 地址固定（GOT/PLT/函数）→ 直接覆盖 |
| RELRO | Partial | GOT可写 → GOT overwrite |
| RELRO | Full | GOT只读 → __free_hook/__malloc_hook(<2.34)/返回地址 |
| NX | Enabled | 栈不可执行 → ROP/ret2win |
| Canary | 存在 | 需leak或走heap攻击 |

**速判**：Partial RELRO+无PIE → GOT overwrite（最容易）；Full RELRO → hook/返回地址；有Canary → 先leak

## 快速命令

```bash
file ./target; checksec --file=./target 2>/dev/null || readelf -l ./target | grep GNU_STACK
strings -n 6 ./target | head -50
ROPgadget --binary ./target | grep "pop rdi"   # 有ROPgadget
objdump -d ./target | grep -A5 "<win>"
# 偏移：cyclic
python3 -c "from pwn import *; print(cyclic(200))"
python3 -c "from pwn import *; print(cyclic_find(0x61616168))"
```

## 常见利用模板

**栈溢出 ret2win**（无PIE）：
```bash
python3 -c 'import struct; print(b"A"*OFFSET + struct.pack("<Q", WIN_ADDR).decode("latin1"))' | ./target
```

**格式化字符串**：
```bash
echo '%p.%p.%p.%p.%p.%p.%p.%p' | ./target   # 找偏移
# %n 写GOT/返回地址（Partial RELRO）
```

**ret2libc**（NX，有leak）：
```bash
# 需要libc版本匹配：libc-database find puts <leak后3位>
# pwntools ROP链
```

**Canary绕过**：
```bash
# fork服务可逐字节爆破：每字节256次尝试
# 或format string leak canary
```

## 源码红旗（审计时）

- `pthread`/线程 → 竞态
- `usleep/sleep` → 时间窗口
- 全局变量多线程 → TOCTOU
- `gets/scanf("%s")/strcpy` → 栈溢出
- `printf(user_input)` → 格式化串

## 无工具降级

```bash
# 无checksec：readelf -h / readelf -l | grep GNU_STACK
# 无gdb：objdump -d + 输入长度二分法
# 无pwntools：python3 struct手动打包
# 判flag：strings找flag{/BLHX{格式
```

## 详细参考（references/）

- overflow-basics.md: 栈/全局溢出、ret2win、canary爆破
- rop-and-shellcode.md + rop-advanced.md: ROP全系列（ret2libc/ret2csu/SROP/seccomp）
- format-string.md: 格式化串全技术
- heap-techniques*.md + heap-fsop.md: 堆利用（House系列/tcache/FSOP）
- kernel*.md: 内核利用（QEMU调试/提权/modprobe_path）
- anti-analysis*.md: 反分析绕过（反调试/混淆）
- patterns*.md: 常见漏洞模式识别
- advanced-exploits*.md: 高级技巧（Windows SEH/VM逃逸/竞态）
