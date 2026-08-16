/**
 * Ackem-Hunter Kali 工具箱插件 —— 通过 SSH 在 Kali 环境执行渗透工具（2026-08-15 自研）
 *
 * 移植自 AePis 0810 的 kali-bash.ts。给 Main Agent 注册 kali_bash 工具：
 *   kali_bash —— 在已配置的 Kali 主机执行非交互式 bash 命令
 *
 * 配置：KALI_SSH_TARGET（user@host:port）或 kali-bash.json
 * 适用：nmap / sqlmap / ffuf / binwalk / hydra 等本地没有的重型工具
 */

import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

export const name = 'kali-bash'
export const inject = ['tools']

const execFileAsync = promisify(execFile)

interface KaliConfig {
  remote: string
  cwd?: string
  sshOptions?: string[]
}

function loadKaliConfig(): KaliConfig {
  // 环境变量优先：KALI_SSH_TARGET = user@host 或 user@host:port
  const envTarget = process.env.KALI_SSH_TARGET?.trim()
  if (envTarget) {
    return { remote: envTarget, cwd: process.env.KALI_SSH_CWD?.trim() || undefined }
  }
  // 配置文件兜底：kali-bash.json（本地凭证文件，不提交Git）
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const fs = require('node:fs') as typeof import('node:fs')
    const path = process.env.KALI_CONFIG_PATH || './kali-bash.json'
    if (fs.existsSync(path)) {
      return JSON.parse(fs.readFileSync(path, 'utf-8')) as KaliConfig
    }
  } catch {
    // fallthrough
  }
  throw new Error('缺少 Kali 配置：请设置 KALI_SSH_TARGET 环境变量或提供 kali-bash.json')
}

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'kali_bash',
    description: '在已配置的 Kali 环境执行非交互式 bash 命令。适合 nmap/sqlmap/ffuf/binwalk/hydra 等本地未安装的渗透工具。命令必须非交互、限定目标为本题平台分配地址，并为扫描或长任务设置 timeout。',
    parameters: {
      command: { type: 'string', required: true, description: '要执行的 bash 命令（非交互式，自行结束）' },
      timeout: { type: 'number', description: '超时秒数（默认 120，最大 300）' },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args) {
      const config = loadKaliConfig()
      const timeoutSec = Math.min(args.timeout ?? 120, 300)
      // 解析 user@host[:port]
      const m = config.remote.match(/^(.*)@([^:]+)(?::(\d+))?$/)
      if (!m) throw new Error(`Kali 配置 remote 格式错误: ${config.remote}（应为 user@host 或 user@host:port）`)
      const [, user, host, port] = m
      const sshArgs = [
        ...(config.sshOptions ?? []),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        ...(port ? ['-p', port] : []),
        `${user}@${host}`,
        `cd ${config.cwd || '/root'} && timeout ${timeoutSec} bash -lc ${JSON.stringify(args.command)}`,
      ]
      try {
        const { stdout, stderr } = await execFileAsync('ssh', sshArgs, {
          timeout: (timeoutSec + 20) * 1000,
          maxBuffer: 8 * 1024 * 1024,
        })
        const out = stdout || stderr
        return out.length > 12000 ? out.slice(0, 12000) + '\n...[kali_bash 输出截断]' : out || '(无输出)'
      } catch (error) {
        const e = error as { stdout?: string; stderr?: string; message?: string }
        const partial = e.stdout || e.stderr || ''
        if (partial) return `[kali_bash 执行返回非零/超时]\n${partial.slice(0, 8000)}`
        return `[kali_bash 失败] ${e.message ?? String(error)}`
      }
    },
  }))
}
