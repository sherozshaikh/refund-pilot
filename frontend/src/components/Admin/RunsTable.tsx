import { useEffect, useState } from 'react'
import { useAdminRuns } from '../../hooks/useAdminRuns'
import { apiClient } from '../../lib/api'
import type { AgentRunSummary } from '../../lib/types'

interface CustomerOption { id: string; name: string }

const DECISION_STYLES: Record<string, string> = {
  approved: 'bg-green-100 text-green-800',
  denied: 'bg-red-100 text-red-800',
  escalated: 'bg-orange-100 text-orange-800',
  fallback: 'bg-yellow-100 text-yellow-800',
}

interface Props {
  onSelectRun: (runId: string) => void
  selectedRunId: string | null
}

export function RunsTable({ onSelectRun, selectedRunId }: Props) {
  const [page, setPage] = useState(1)
  const [decisionFilter, setDecisionFilter] = useState<string>('')
  const [customerFilter, setCustomerFilter] = useState<string>('')
  const [customers, setCustomers] = useState<CustomerOption[]>([])
  const { data, isLoading, isError } = useAdminRuns(page, decisionFilter || undefined, customerFilter || undefined)

  useEffect(() => {
    apiClient.get<CustomerOption[]>('/api/v1/customers')
      .then(r => setCustomers(r.data))
      .catch(() => {})
  }, [])

  const totalPages = data ? Math.ceil(data.total / 20) : 1

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <select
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={decisionFilter}
          onChange={(e) => { setDecisionFilter(e.target.value); setPage(1) }}
        >
          <option value="">All decisions</option>
          <option value="approved">Approved</option>
          <option value="denied">Denied</option>
          <option value="escalated">Escalated</option>
          <option value="fallback">Fallback</option>
        </select>
        <select
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={customerFilter}
          onChange={(e) => { setCustomerFilter(e.target.value); setPage(1) }}
        >
          <option value="">All customers</option>
          {customers.map(c => (
            <option key={c.id} value={c.id}>{c.name} #{c.id.slice(-8)}</option>
          ))}
        </select>
        {data && (
          <span className="text-sm text-gray-500">{data.total} total runs</span>
        )}
      </div>

      {isError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
          Failed to load runs. Check admin credentials.
        </p>
      )}

      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Decision</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Customer</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Message</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Tokens in/out</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Latency</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Created</th>
              <th className="px-4 py-3 text-center font-medium text-gray-600">Injection</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-gray-100" />
                      </td>
                    ))}
                  </tr>
                ))
              : data?.items.map((run: AgentRunSummary) => (
                  <tr
                    key={run.id}
                    className={`cursor-pointer transition-colors hover:bg-blue-50 ${
                      selectedRunId === run.id ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => onSelectRun(run.id)}
                  >
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${DECISION_STYLES[run.decision] ?? 'bg-gray-100 text-gray-700'}`}
                      >
                        {run.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">
                      <span className="font-medium">{run.customer_name}</span>
                      <span className="ml-1 font-mono text-gray-400">#{run.customer_id.slice(-8)}</span>
                    </td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-xs text-gray-500" title={run.input_message}>
                      {run.input_message}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                      {run.input_tokens} / {run.output_tokens}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                      {run.latency_ms}ms
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {run.injection_detected && (
                        <span className="inline-block rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                          ⚠ detected
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2">
          <button
            className="rounded px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          <button
            className="rounded px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40"
            disabled={page === totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
