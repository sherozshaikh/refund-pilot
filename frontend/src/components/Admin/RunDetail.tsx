import { useAdminRunDetail } from '../../hooks/useAdminRuns'
import type { TraceStep } from '../../lib/types'

const DECISION_STYLES: Record<string, string> = {
  approved: 'bg-green-100 text-green-800',
  denied: 'bg-red-100 text-red-800',
  escalated: 'bg-orange-100 text-orange-800',
  fallback: 'bg-yellow-100 text-yellow-800',
}

interface Props {
  runId: string
}

export function RunDetail({ runId }: Props) {
  const { data: run, isLoading, isError } = useAdminRunDetail(runId)

  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-6 animate-pulse rounded bg-gray-100" />
        ))}
      </div>
    )
  }

  if (isError || !run) {
    return (
      <p className="p-4 text-sm text-red-600">Failed to load run detail.</p>
    )
  }

  return (
    <div className="space-y-4 overflow-y-auto p-4 text-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${DECISION_STYLES[run.decision] ?? 'bg-gray-100 text-gray-700'}`}
        >
          {run.decision.toUpperCase()}
        </span>
        {run.injection_detected && (
          <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
            ⚠ INJECTION DETECTED
          </span>
        )}
        <span className="text-xs text-gray-400">
          {new Date(run.created_at).toLocaleString()}
        </span>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-lg font-semibold tabular-nums text-gray-900">{run.latency_ms}ms</p>
          <p className="text-xs text-gray-500">Latency</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-lg font-semibold tabular-nums text-gray-900">{run.input_tokens}</p>
          <p className="text-xs text-gray-500">Input tokens</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-lg font-semibold tabular-nums text-gray-900">{run.output_tokens}</p>
          <p className="text-xs text-gray-500">Output tokens</p>
        </div>
      </div>

      {/* Input message */}
      <section>
        <h3 className="mb-1 font-semibold text-gray-700">User message</h3>
        <p className="rounded-md bg-blue-50 px-3 py-2 text-gray-800">{run.input_message}</p>
      </section>

      {/* Reasoning */}
      <section>
        <h3 className="mb-1 font-semibold text-gray-700">Agent reasoning</h3>
        <p className="rounded-md bg-gray-50 px-3 py-2 text-gray-700 leading-relaxed">
          {run.reasoning || '—'}
        </p>
      </section>

      {/* Policy clauses */}
      {run.policy_clauses_cited.length > 0 && (
        <section>
          <h3 className="mb-1 font-semibold text-gray-700">Policy clauses cited</h3>
          <ul className="space-y-1">
            {run.policy_clauses_cited.map((clause: string, i: number) => (
              <li key={i} className="rounded-md bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
                {clause}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Trace tree */}
      {run.trace_steps.length > 0 && (
        <section>
          <h3 className="mb-2 font-semibold text-gray-700">Trace steps</h3>
          <div className="space-y-2">
            {run.trace_steps.map((step: TraceStep, i: number) => (
              <details key={i} className="group rounded-lg border bg-white">
                <summary className="flex cursor-pointer items-center gap-2 px-3 py-2 text-xs font-medium text-gray-700 marker:hidden">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-gray-500">
                    {i + 1}
                  </span>
                  <span>{step.node ?? `Step ${i + 1}`}</span>
                  {step.duration_ms !== undefined && (
                    <span className="ml-auto text-gray-400">{step.duration_ms}ms</span>
                  )}
                </summary>
                <div className="border-t px-3 py-2">
                  <p className="mb-1 text-xs font-medium text-gray-500">Input</p>
                  <pre className="overflow-x-auto rounded bg-gray-50 p-2 text-xs text-gray-700">
                    {JSON.stringify(step.input, null, 2)}
                  </pre>
                  <p className="mb-1 mt-2 text-xs font-medium text-gray-500">Output</p>
                  <pre className="overflow-x-auto rounded bg-gray-50 p-2 text-xs text-gray-700">
                    {JSON.stringify(step.output, null, 2)}
                  </pre>
                </div>
              </details>
            ))}
          </div>
        </section>
      )}

      {/* LangSmith link */}
      {run.langsmith_run_id && (
        <section>
          <h3 className="mb-1 font-semibold text-gray-700">LangSmith trace</h3>
          {import.meta.env.VITE_LANGSMITH_BASE_URL ? (
            <a
              href={`${import.meta.env.VITE_LANGSMITH_BASE_URL}/runs/${run.langsmith_run_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-blue-600 hover:underline"
            >
              {run.langsmith_run_id}
            </a>
          ) : (
            <span className="font-mono text-xs text-gray-500">{run.langsmith_run_id}</span>
          )}
        </section>
      )}
    </div>
  )
}
