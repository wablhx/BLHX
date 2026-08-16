/**
 * Decode an SSE byte stream into event `data` payloads.
 *
 * BLHX patch: lenient line-based parsing (no blank-line terminator required).
 * Some OpenAI-compatible gateways (e.g. the Baidu Zhipu challenge gateway)
 * terminate the stream with `data: [DONE]` WITHOUT a trailing blank line;
 * eventsource-parser is spec-strict and drops such unterminated events,
 * causing spurious STREAM_CLOSED errors. This implementation yields each
 * `data:` line immediately and also flushes a final unterminated line at EOF.
 *
 * @module dsh-llm-deepseek/sse
 */

import { LlmError } from '@deepseek-ai/dsh-llm'

/** The terminal payload DeepSeek (and OpenAI) send after the last chunk. */
export const DONE = '[DONE]'

/**
 * Parse an SSE byte stream into data payloads. Yields `[DONE]` as the final
 * value and returns; throws `LlmError('STREAM_CLOSED')` when the stream ends
 * without it (truncated response — the model call cannot be trusted).
 * @param stream - raw SSE bytes; reads may split anywhere, including mid-UTF-8 sequence.
 * @param onComment - retained for API compatibility; comments are ignored.
 * @returns each event's data payload in arrival order, the `[DONE]` sentinel last.
 */
export async function* parseSse(
  stream: ReadableStream<BufferSource>,
  _onComment?: (comment: string) => void,
): AsyncGenerator<string> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  const emit = (line: string): string | undefined => {
    const t = line.trim()
    if (!t.startsWith('data:')) return undefined
    const data = t.slice(5).trim()
    if (data === '') return undefined
    return data
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let nl: number
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl)
      buf = buf.slice(nl + 1)
      const data = emit(line)
      if (data !== undefined) {
        yield data
        if (data === DONE) return
      }
    }
  }

  // EOF: flush a final unterminated line (lenient tail handling).
  if (buf.length > 0) {
    const data = emit(buf)
    if (data !== undefined) {
      yield data
      if (data === DONE) return
    }
  }
  throw new LlmError('SSE stream ended without [DONE]', 'STREAM_CLOSED')
}
