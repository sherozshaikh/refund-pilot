import type { AgentRunSummary } from '../../lib/types'

interface Props {
  runs: AgentRunSummary[]
}

const DECISION_COLORS: Record<string, string> = {
  approved: '#22c55e',
  denied: '#ef4444',
  escalated: '#f97316',
  fallback: '#eab308',
}

export function MetricsPanel({ runs }: Props) {
  if (runs.length === 0) {
    return (
      <div className="rounded-lg border bg-white p-6 text-center text-sm text-gray-400">
        No runs to summarize.
      </div>
    )
  }

  const totalTokens = runs.reduce((s, r) => s + r.input_tokens + r.output_tokens, 0)
  const avgLatency = Math.round(runs.reduce((s, r) => s + r.latency_ms, 0) / runs.length)
  const maxLatency = Math.max(...runs.map((r) => r.latency_ms))
  const injectionCount = runs.filter((r) => r.injection_detected).length

  const decisionCounts = runs.reduce<Record<string, number>>((acc, r) => {
    acc[r.decision] = (acc[r.decision] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <MetricCard label="Total tokens" value={totalTokens.toLocaleString()} sub="this page" />
      <MetricCard label="Avg latency" value={`${avgLatency}ms`} sub={`max ${maxLatency}ms`} />
      <MetricCard
        label="Injection flags"
        value={String(injectionCount)}
        sub={`of ${runs.length} runs`}
        highlight={injectionCount > 0}
      />

      <div className="rounded-lg border bg-white p-3">
        <p className="text-xs text-gray-500">Decision breakdown</p>
        <div className="mt-2 space-y-1">
          {Object.entries(decisionCounts).map(([decision, count]) => (
            <div key={decision} className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                style={{ backgroundColor: DECISION_COLORS[decision] ?? '#6b7280' }}
              />
              <span className="text-xs text-gray-700 capitalize">{decision}</span>
              <span className="ml-auto text-xs font-semibold tabular-nums text-gray-900">
                {count}
              </span>
              <span className="text-xs text-gray-400">
                ({Math.round((count / runs.length) * 100)}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  sub,
  highlight = false,
}: {
  label: string
  value: string
  sub: string
  highlight?: boolean
}) {
  return (
    <div className={`rounded-lg border bg-white p-3 ${highlight ? 'border-red-200 bg-red-50' : ''}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${highlight ? 'text-red-700' : 'text-gray-900'}`}>
        {value}
      </p>
      <p className="text-xs text-gray-400">{sub}</p>
    </div>
  )
}
