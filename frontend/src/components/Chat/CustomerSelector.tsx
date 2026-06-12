import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import type { Customer, Order } from '../../lib/types'
import { useChatStore } from '../../store/chat'

export function CustomerSelector() {
  const { selectedCustomer, setCustomer } = useChatStore()

  const { data: customers = [], isLoading } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: async () => {
      const { data } = await apiClient.get<Customer[]>('/api/v1/customers')
      return data
    },
  })

  return (
    <div>
      <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5">
        Customer
      </label>
      <select
        className="w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-50 [&>option]:bg-gray-800 [&>option]:text-gray-100"
        value={selectedCustomer?.id ?? ''}
        onChange={(e) => {
          const found = customers.find((c) => c.id === e.target.value) ?? null
          setCustomer(found)
        }}
        disabled={isLoading}
      >
        <option value="">Select customer…</option>
        {customers.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} · {c.tier}
          </option>
        ))}
      </select>
    </div>
  )
}

export function OrderSelector() {
  const { selectedCustomer, selectedOrder, setOrder } = useChatStore()

  const { data: orders = [], isLoading } = useQuery<Order[]>({
    queryKey: ['orders', selectedCustomer?.id],
    queryFn: async () => {
      const { data } = await apiClient.get<Order[]>(
        `/api/v1/customers/${selectedCustomer!.id}/orders`,
      )
      return data
    },
    enabled: Boolean(selectedCustomer),
  })

  if (!selectedCustomer) return null

  return (
    <div>
      <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5">
        Order
      </label>
      {!isLoading && orders.length === 0 ? (
        <p className="text-sm text-gray-500">No orders found</p>
      ) : (
        <select
          className="w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-50 [&>option]:bg-gray-800 [&>option]:text-gray-100"
          value={selectedOrder?.id ?? ''}
          onChange={(e) => {
            const found = orders.find((o) => o.id === e.target.value) ?? null
            setOrder(found)
          }}
          disabled={isLoading}
        >
          <option value="">Select order…</option>
          {orders.map((o) => (
            <option key={o.id} value={o.id}>
              {o.product_name} — ${o.amount.toFixed(2)}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}
