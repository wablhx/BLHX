# BLHX —— TSecBench 智能攻防 Agent（2026-08-15）
# 平台托管模式：8核16G沙箱，模型走 .tsecbench.gw 网关，BENCHMARK_TOKEN 自动注入
#
# 构建：docker build -t blhx-agent .
# 导出：docker save blhx-agent | gzip > blhx-agent.tar.gz

FROM node:24-slim AS base
# node:24 修复：Node22 require(ESM) 循环 bug 导致插件加载崩溃（ERR_REQUIRE_CYCLE_MODULE）

# ── 基础工具（渗透测试常用；比赛闭卷环境不能联网装，全预装）──
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git python3 python3-pip ca-certificates \
    nmap netcat-openbsd dnsutils iputils-ping procps \
    build-essential python3-dev gdb binutils file strace \
    && rm -rf /var/lib/apt/lists/*

# ── Python 渗透库（pwntools/requests/云CLI，闭卷环境必备）──
# Debian 12 PEP668 保护：需要 --break-system-packages
RUN pip3 install --no-cache-dir --break-system-packages \
    pwntools requests beautifulsoup4 lxml \
    aliyun-python-sdk-core aliyun-python-sdk-ecs aliyun-python-sdk-ram \
    tencentcloud-sdk-python boto3 \
    && rm -rf ~/.cache/pip

# ── DS Harness（DeepSeek 官方，MIT）──
WORKDIR /opt/dsh
COPY harness/package.json harness/pnpm-lock.yaml harness/pnpm-workspace.yaml ./
COPY harness/tsconfig*.json ./
COPY harness/apps ./apps
COPY harness/packages ./packages
COPY harness/scripts ./scripts
COPY harness/vendor ./vendor
COPY harness/native ./native
COPY harness/patches ./patches
# pnpm 安装（GitHub Actions 构建时网络通畅；锁文件失败时回退普通安装）
RUN corepack enable && (pnpm install --frozen-lockfile || pnpm install)

# ── BLHX Agent 代码 ──
WORKDIR /opt/blhx
COPY agent/runner.py ./
COPY agent/plugins ./plugins
COPY agent/agents ./agents
COPY agent/prompts ./prompts
COPY agent/skills ./skills
COPY agent/kali-bash.json ./kali-bash.json
RUN mkdir -p runs

# ── 挂载 BLHX skills 到 dsh 的 user-agents 根（Agent 按需读取）──
RUN mkdir -p /root/.agents && cp -r /opt/blhx/skills /root/.agents/skills

# ── dsh profile：固化 BLHX patch 到 headless profile ──
COPY agent/ackem-tsecbench.patch.yml /root/.dsh/profiles/headless/cordis.patch.yml
RUN mkdir -p /root/.dsh/profiles/headless/plugins \
    && cp /opt/blhx/plugins/tsec-benchmark.ts /root/.dsh/profiles/headless/plugins/ \
    && cp /opt/blhx/plugins/kali-bash.ts /root/.dsh/profiles/headless/plugins/

# ── 平台网关：模型走 http://api.deepseek.com.tsecbench.gw/v1 ──
ENV DEEPSEEK_BASE_URL=http://api.deepseek.com.tsecbench.gw/v1
ENV DEEPSEEK_MODEL=deepseek-v4-flash
ENV DS_HARNESS_ROOT=/opt/dsh
ENV PATH="/opt/dsh/node_modules/.bin:$PATH"

WORKDIR /opt/blhx
CMD ["python3", "runner.py", "--concurrency", "2"]
