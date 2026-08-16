#!/usr/bin/env python3
"""Ackem-Hunter TSecBench Runner —— 比赛调度器（2026-08-15 自研）

职责：
  1. VPN 预检（10.0.100.58）
  2. 拉取题目列表 → 按难度/level/分数排序
  3. 逐题：启动容器 → 创建题目目录(challenge.json/targets.txt) → 启动 dsh Main Agent
  4. 单题超时(默认600s) → 关闭容器 → 下一题
  5. 并发 ≤3（平台容器上限）
  6. 输出 runs/<run-id>/：challenge.json + main-agent.log + trace + summary.json

用法：
  TSEC_BASE_URL=https://tsecbench.zc.tencent.com \
  TSEC_TOKEN=<BENCHMARK_TOKEN> \
  DEEPSEEK_API_KEY=<key> \
  python runner.py [--max-challenges N] [--concurrency 3] [--timeout 600]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_URL = os.environ.get("BENCHMARK_BASE_URL") or os.environ.get("TSEC_BASE_URL", "https://tsecbench.zc.tencent.com").rstrip("/")
TOKEN = os.environ.get("BENCHMARK_TOKEN") or os.environ.get("TSEC_TOKEN", "")
# 托管模式：平台自动注入 BENCHMARK_TOKEN/BENCHMARK_BASE_URL；本地测试时可手动指定
PROJECT_ROOT = Path(__file__).resolve().parent
# DS Harness 源码路径（dsh CLI 用 tsx 直接跑，无需构建）
DS_HARNESS_ROOT = Path(os.environ.get("DS_HARNESS_ROOT", r"D:\tmp\ackem\ds-harness-ref"))
# tsx 必须从 DS Harness 根目录启动（node_modules 在那）；--import tsx/esm 用绝对路径
DSH_CMD = [
    "node",
    "--import",
    "tsx/esm",
    str(DS_HARNESS_ROOT / "apps" / "cli" / "src" / "bin.ts"),
]
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "prompts" / "pentest-system.txt"
AGENTS_DIR = PROJECT_ROOT / "agents"
PLUGINS_DIR = PROJECT_ROOT / "plugins"
# Kali 配置（比赛前填写/校验）
KALI_CONFIG_PATH = PROJECT_ROOT / "kali-bash.json"


class TsecApiError(Exception):
    pass


def tsec_request(path: str, method: str = "GET", body: dict | None = None, timeout: int = 30) -> Any:
    url = f"{BASE_URL}{path}"
    headers = {"BENCHMARK_TOKEN": TOKEN}
    data = None
    if body is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500] if e.fp else ""
        raise TsecApiError(f"HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise TsecApiError(f"网络错误: {e.reason}") from e


def list_challenges() -> list[dict]:
    return tsec_request("/openapi/v1/challenges")


def start_challenge(code: str) -> list[str]:
    r = tsec_request(f"/openapi/v1/challenges/start?unique_code={code}", method="POST")
    return r.get("container_addr", []) if r else []


def close_challenge(code: str) -> None:
    try:
        tsec_request(f"/openapi/v1/challenges/close?unique_code={code}", method="POST")
    except TsecApiError as e:
        print(f"  [warn] 关闭容器失败 {code}: {e}")


def difficulty_rank(d: str) -> int:
    return {"easy": 0, "medium": 1, "hard": 2, "insane": 3}.get(d.lower(), 9)


def select_challenges(challenges: list[dict], max_n: int | None, only_codes: set[str]) -> list[dict]:
    filtered = [c for c in challenges if not only_codes or c["unique_code"] in only_codes]
    filtered.sort(
        key=lambda c: (difficulty_rank(c.get("difficulty", "")), c.get("level", 0), c.get("total_score", 0), c["unique_code"])
    )
    if max_n:
        filtered = filtered[:max_n]
    return filtered


def safe_name(code: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in code)[:60]


def prepare_challenge_dir(run_root: Path, challenge: dict, addresses: list[str]) -> Path:
    cdir = run_root / "challenges" / safe_name(challenge["unique_code"])
    (cdir / "workspace" / "findings").mkdir(parents=True, exist_ok=True)
    (cdir / "workspace" / "sessions").mkdir(parents=True, exist_ok=True)
    (cdir / "artifacts").mkdir(parents=True, exist_ok=True)
    (cdir / "trace").mkdir(parents=True, exist_ok=True)
    (cdir / "challenge.json").write_text(json.dumps({"challenge": challenge, "addresses": addresses}, ensure_ascii=False, indent=2), encoding="utf-8")
    (cdir / "workspace" / "targets.txt").write_text("\n".join(addresses) + "\n", encoding="utf-8")
    return cdir


def task_instruction(challenge: dict, addresses: list[str], cdir: Path) -> str:
    """构造任务指令。用英文模板避开 git-bash/MSYS 中文全角字符破坏问题；
    完整题目信息写入 challenge.json 由 Agent 自行读取。"""
    desc = (challenge.get("description") or "no extra description").replace("\n", " ")[:200]
    return (
        f"## Current Task\n\n"
        f"Target: {', '.join(addresses) if addresses else 'check container status first'}\n"
        f"Difficulty: {challenge.get('difficulty')} | Score: {challenge.get('total_score')} | Flags: {challenge.get('flag_count')}\n"
        f"Workdir: {cdir}\n\n"
        f"Read challenge.json in workdir for full description. Recon the target, find flags, "
        f"and submit via benchmark_submit_flag. Summarize findings in Chinese when done.\n"
        f"Challenge hint: {desc}"
    )


def run_main_agent(challenge: dict, cdir: Path, timeout_sec: int) -> dict:
    """启动 dsh（DeepSeek Harness）Main Agent 处理单题。"""
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
    instruction = task_instruction(challenge, challenge.get("container_addr", []), cdir)
    log_path = cdir / "main-agent.log"

    # dsh CLI：headless 单任务模式（默认 profile 已带 ackem patch，无需重复 --patch）
    # 关键环境变量透传：DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL
    # 由 runner 进程 env 继承（Docker CMD 前由平台注入或 -e 指定）
    cmd = [*DSH_CMD, "--profile", "headless", instruction]
    print(f"  [main-agent] 启动 dsh headless (timeout={timeout_sec}s)")
    started = time.time()
    # 确保模型环境变量进入子进程（含 TSEC_UNIQUE_CODE——平台插件必需）
    dsh_env = {**os.environ}
    for k in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "BENCHMARK_TOKEN", "BENCHMARK_BASE_URL", "TSEC_UNIQUE_CODE"):
        if os.environ.get(k):
            dsh_env[k] = os.environ[k]
    dsh_env["TSEC_UNIQUE_CODE"] = challenge["unique_code"]  # 强制注入当前题目code
    try:
        # 用文件重定向避免管道阻塞死锁；轮询超时控制
        with open(log_path, "w", encoding="utf-8") as logf:
            proc = subprocess.Popen(
                cmd,
                cwd=str(DS_HARNESS_ROOT),  # tsx/node_modules 在 DS Harness 根目录
                env=dsh_env,
                stdout=logf, stderr=subprocess.STDOUT, text=True,
            )
            timed_out = False
            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                timed_out = True
    except FileNotFoundError:
        log_path.write_text("dsh CLI 未找到，请先构建 DS Harness 或安装 @deepseek-ai/dsh\n", encoding="utf-8")
        return {"status": "failed", "reason": "dsh not found"}

    elapsed = int(time.time() - started)
    # 回显日志尾部（最多30行）
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for ln in lines[-30:]:
            print(f"    {ln.rstrip()[:160]}")
    except Exception:
        pass
    return {"status": "timed_out" if timed_out else "completed", "elapsed_sec": elapsed}


def run_challenge(client_cfg: dict, challenge: dict, run_root: Path) -> dict:
    code = challenge["unique_code"]
    print(f"\n=== 题目 {code} ({challenge.get('difficulty')}, 分{challenge.get('total_score')}, {challenge.get('flag_count')} flags) ===")
    addresses = challenge.get("container_addr", [])
    if challenge.get("container_status") != "available" or not addresses:
        print(f"  [start] 启动容器...")
        addresses = start_challenge(code)
        print(f"  [start] 地址: {addresses}")
    cdir = prepare_challenge_dir(run_root, challenge, addresses)
    timeout_sec = int(os.environ.get("TSEC_CHALLENGE_TIMEOUT_SECONDS", "600"))
    result = run_main_agent(challenge, cdir, timeout_sec)
    # 查最终进度
    try:
        progress = next((c for c in list_challenges() if c["unique_code"] == code), None)
        if progress:
            result["correct_flags"] = progress.get("correct_flag_count")
            result["total_flags"] = progress.get("flag_count")
            result["completed"] = progress.get("is_completed")
    except Exception:
        pass
    close_challenge(code)
    return {"unique_code": code, **result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ackem-Hunter TSecBench Runner")
    parser.add_argument("--max-challenges", type=int, default=None, help="本轮最多题目数")
    parser.add_argument("--concurrency", type=int, default=3, help="并发 Main Agent 数 (1-3)")
    parser.add_argument("--timeout", type=int, default=None, help="单题超时秒数（默认600）")
    parser.add_argument("--codes", type=str, default=None, help="只跑指定题目 unique_code（逗号分隔）")
    args = parser.parse_args()

    if not TOKEN:
        print("[错误] 缺少 BENCHMARK_TOKEN/TSEC_TOKEN 环境变量（托管模式由平台自动注入，本地测试请手动设置）")
        return 1

    print("=== Ackem-Hunter TSecBench Runner ===")
    print(f"[api] {BASE_URL}")

    challenges = list_challenges()
    print(f"[challenges] 共 {len(challenges)} 道题")
    only = set(args.codes.split(",")) if args.codes else set()
    selected = select_challenges(challenges, args.max_challenges, only)
    if not selected:
        print("没有符合筛选条件的题目。")
        return 0
    print(f"[selected] {len(selected)} 道题（按难度排序）")

    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_root = PROJECT_ROOT / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    concurrency = max(1, min(args.concurrency, 3))
    results: list[dict] = []
    next_idx = [0]
    active: list[tuple[subprocess.Popen, dict]] = []

    def stop_all():
        for p, _ in active:
            try:
                p.terminate()
            except Exception:
                pass

    signal.signal(signal.SIGINT, lambda *_: (stop_all(), sys.exit(130)))

    # 简化并发：串行处理（比赛2轮场景，串行更稳；并发留给 dsh 内部 subagent）
    for challenge in selected:
        results.append(run_challenge({}, challenge, run_root))

    (run_root / "summary.json").write_text(json.dumps({"run_id": run_id, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== 完成，结果写入 {run_root} ===")
    for r in results:
        print(f"  {r['unique_code']}: {r.get('status')} flags={r.get('correct_flags')}/{r.get('total_flags')} {r.get('elapsed_sec','')}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
