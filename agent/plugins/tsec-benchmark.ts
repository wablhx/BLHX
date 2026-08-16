/**
 * Ackem-Hunter TSecBench 插件 —— DS Harness 接入层（2026-08-15 自研）
 *
 * 基于 AePis 0810 的 tsec-benchmark.ts 移植到 DeepSeek Harness 插件体系。
 * 给 Main Agent 注册三个平台工具：
 *   benchmark_get_progress —— 查询题目进度（容器状态/Flag数/完成度）
 *   benchmark_submit_flag  —— 提交候选 Flag（正确性/得分/进度）
 *   benchmark_get_hint     —— 获取官方 Hint
 *
 * 认证：BENCHMARK_TOKEN / TSEC_TOKEN（平台"获取接入配置"发放）
 */

import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'tsec-benchmark'
export const inject = ['tools']

// ── TSecBench API 客户端（移植自 AePis tsec-client.ts）──────────

interface TsecChallenge {
  unique_code: string
  description?: string | null
  difficulty: string
  level: number
  total_score: number
  flag_count: number
  correct_flag_count: number
  is_completed: boolean
  container_status: string
  container_addr: string[]
}

interface TsecSubmitResult {
  correct: boolean
  awarded: number
  cumulative_score: number
  correct_flag_count: number
  total_flag_count: number
  matched_flag_index: number | null
}

function requiredEnv(...names: string[]): string {
  const value = names.map((n) => process.env[n]?.trim()).find((c) => c)
  if (!value) throw new Error(`缺少环境变量 ${names.join(' 或 ')}`)
  return value
}

function currentChallengeCode(): string {
  const uniqueCode = process.env.TSEC_UNIQUE_CODE?.trim()
  if (!uniqueCode) throw new Error('当前 Main Agent 缺少 TSEC_UNIQUE_CODE，无法操作 Benchmark 题目')
  return uniqueCode
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}

async function tsecRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = requiredEnv('BENCHMARK_BASE_URL', 'TSEC_BASE_URL').replace(/\/+$/, '')
  const token = requiredEnv('BENCHMARK_TOKEN', 'TSEC_TOKEN')
  const headers = new Headers(init?.headers)
  headers.set('BENCHMARK_TOKEN', token)
  if (init?.body) headers.set('content-type', 'application/json')
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    signal: init?.signal ?? AbortSignal.timeout(30_000),
  })
  const text = await response.text()
  const body = text ? JSON.parse(text) : null
  if (!response.ok) {
    const msg = body?.message ?? `HTTP ${response.status}`
    throw new Error(msg)
  }
  return body as T
}

function listChallenges(): Promise<TsecChallenge[]> {
  return tsecRequest<TsecChallenge[]>('/openapi/v1/challenges')
}

function submitFlag(uniqueCode: string, flag: string): Promise<TsecSubmitResult> {
  return tsecRequest<TsecSubmitResult>('/openapi/v1/challenges/submit', {
    method: 'POST',
    body: JSON.stringify({ unique_code: uniqueCode, flag }),
  })
}

function getHint(uniqueCode: string): Promise<{ hint: string | null }> {
  return tsecRequest<{ hint: string | null }>(
    `/openapi/v1/challenges/hint?unique_code=${encodeURIComponent(uniqueCode)}`,
  )
}

// ── 工具定义 ──────────────────────────────────────────────────────

export function apply(ctx: Context) {
  // 查询题目进度
  ctx.tools.register(defineTool({
    name: 'benchmark_get_progress',
    description: '查询当前 TSecBench 题目的容器状态、Flag 数量、已提交数量和完成状态。提交 Flag 后查询进度确认是否仍有未完成 Flag。',
    parameters: {},
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute() {
      try {
        const uniqueCode = currentChallengeCode()
        const challenges = await listChallenges()
        const challenge = challenges.find((c) => c.unique_code === uniqueCode)
        if (!challenge) throw new Error(`当前任务中不存在题目 ${uniqueCode}`)
        return JSON.stringify(challenge, null, 2)
      } catch (error) {
        return `[benchmark_get_progress 失败] ${errorText(error)}`
      }
    },
  }))

  // 提交 Flag
  ctx.tools.register(defineTool({
    name: 'benchmark_submit_flag',
    description: '向 TSecBench 提交当前题目的候选 Flag，返回正确性、得分和完成进度。发现候选 Flag 后立即提交，不要通过 curl 直接调 API。',
    parameters: {
      flag: { type: 'string', required: true, description: '要提交的 Flag 原文' },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args) {
      try {
        const uniqueCode = currentChallengeCode()
        const result = await submitFlag(uniqueCode, args.flag)
        return JSON.stringify(result, null, 2)
      } catch (error) {
        return `[benchmark_submit_flag 失败] ${errorText(error)}`
      }
    },
  }))

  // 获取 Hint
  ctx.tools.register(defineTool({
    name: 'benchmark_get_hint',
    description: '获取当前 TSecBench 题目的官方 Hint。卡住时使用，15 分钟无进展再请求。',
    parameters: {},
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute() {
      try {
        const uniqueCode = currentChallengeCode()
        const result = await getHint(uniqueCode)
        return JSON.stringify(result, null, 2)
      } catch (error) {
        return `[benchmark_get_hint 失败] ${errorText(error)}`
      }
    },
  }))
}
