# BLHX 🦂

> **TSecBench 智能攻防 Agent** —— 基于 DeepSeek Harness 的自动化渗透测试智能体。
> 「Agent+」攻防能力挑战赛参赛作品（百度安全应急响应中心 BSRC 主办）。

## 架构

```
BLHX Agent（Docker 镜像，平台托管沙箱 8核16G）
├── DeepSeek Harness（dsh headless profile）—— Main Agent 底座
│   ├── + tsec-benchmark 插件：benchmark_get_progress / benchmark_submit_flag / benchmark_get_hint
│   ├── + kali-bash 插件：SSH 调 Kali 渗透工具
│   └── + Pentest Orchestrator persona（O-H-V-D 循环 + 收敛规则 + Flag 搜寻）
├── runner.py —— 调度器：拉题 → 逐题启动 Agent → 提交 Flag → 关闭容器
└── 13 个专业 Subagent 角色（注入/认证/文件/POC/逆向/加密/审计...）
```

## 关键机制

- **O-H-V-D 循环**：Observe → Hypothesize → Verify → Decide，证据驱动不枚举
- **凭证红线**：获得疑似凭证立即提交，不等"最终确认"
- **错误止损**：连续 3 次同类失败切换方法，2 个类别失败关闭方向
- **Flag 搜寻优先级**：环境变量 → 文件系统 → 数据库 → 容器元数据 → 应用内部
- **模型**：DeepSeek V4 Flash（走平台网关 `http://api.deepseek.com.tsecbench.gw/v1`）

## 本地测试

```bash
# 需要：BENCHMARK_TOKEN（平台接入配置）+ DEEPSEEK_API_KEY
export BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com
export BENCHMARK_TOKEN=xxx
export DEEPSEEK_API_KEY=sk-xxx
export DEEPSEEK_BASE_URL=https://api.deepseek.com/v1   # 本地用官方地址
python3 agent/runner.py --max-challenges 2
```

## 构建镜像（GitHub Actions 自动）

推 main 分支 → Actions 自动构建 → 下载 `blhx-agent` artifact（tar.gz）→ 上传平台。

手动构建：
```bash
docker build -t blhx-agent .
docker save blhx-agent | gzip > blhx-agent.tar.gz
```

## 合规声明

本作品仅用于「Agent+」挑战赛授权靶场环境。不攻击未授权目标、无害化验证、数据最小化。

## 致谢

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（MIT）—— Agent 底座
- [AePis](https://github.com/AutoPT-ai/AePis-public) —— TSecBench 接入参考
