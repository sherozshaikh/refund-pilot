import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import type { AgentRunDetail, RunList } from '../lib/types'

export function useAdminRuns(page = 1, decision?: string, customerId?: string) {
  return useQuery<RunList>({
    queryKey: ['admin-runs', page, decision, customerId],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, limit: 20 }
      if (decision) params.decision = decision
      if (customerId) params.customer_id = customerId
      const { data } = await apiClient.get<RunList>('/api/v1/admin/runs', { params })
      return data
    },
    refetchInterval: 10_000,
  })
}

export function useAdminRunDetail(runId: string | null) {
  return useQuery<AgentRunDetail>({
    queryKey: ['admin-run', runId],
    queryFn: async () => {
      const { data } = await apiClient.get<AgentRunDetail>(`/api/v1/admin/runs/${runId}`)
      return data
    },
    enabled: Boolean(runId),
  })
}
