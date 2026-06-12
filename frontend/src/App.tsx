import { useState } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Login } from './components/Login'
import { ChatWindow } from './components/Chat/ChatWindow'
import { CustomerSelector, OrderSelector } from './components/Chat/CustomerSelector'
import { RunsTable } from './components/Admin/RunsTable'
import { RunDetail } from './components/Admin/RunDetail'
import { MetricsPanel } from './components/Admin/MetricsPanel'
import { useAdminRuns } from './hooks/useAdminRuns'
import { useChatStore } from './store/chat'

type View = 'chat' | 'admin' | 'login'

const TIER_COLORS: Record<string, string> = {
  vip:      'bg-amber-400/20 text-amber-300 border border-amber-400/30',
  premium:  'bg-violet-400/20 text-violet-300 border border-violet-400/30',
  standard: 'bg-gray-400/20 text-gray-400 border border-gray-500/30',
}

function Sidebar({ view, setView }: { view: View; setView: (v: View) => void }) {
  const { selectedCustomer, selectedOrder, reset } = useChatStore()
  const hasToken = Boolean(localStorage.getItem('admin_token'))

  const handleAdminClick = () => {
    setView(hasToken ? 'admin' : 'login')
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col bg-[#1a1a2e] text-gray-100">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-white/10 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg">
          <span className="text-xs font-bold text-white">RP</span>
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Refund Pilot</p>
          <p className="text-xs text-gray-500">AI Support Agent</p>
        </div>
      </div>

      {/* Nav */}
      <div className="flex gap-1 px-3 py-3 border-b border-white/10">
        <button
          onClick={() => setView('chat')}
          className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            view === 'chat'
              ? 'bg-white/10 text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
          }`}
        >
          Chat
        </button>
        <button
          onClick={handleAdminClick}
          className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            view === 'admin' || view === 'login'
              ? 'bg-white/10 text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
          }`}
        >
          Admin
        </button>
      </div>

      {/* Customer context (only in chat view) */}
      {view === 'chat' && (
        <div className="flex flex-col gap-4 px-4 py-4 border-b border-white/10">
          <CustomerSelector />
          <OrderSelector />
        </div>
      )}

      {/* Active session info */}
      {view === 'chat' && selectedCustomer && (
        <div className="mx-4 mt-3 rounded-xl bg-white/5 px-4 py-3 border border-white/10">
          <div className="flex items-start gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 text-xs font-bold text-white">
              {selectedCustomer.name.split(' ').map((w) => w[0]).slice(0, 2).join('')}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-100">{selectedCustomer.name}</p>
              <span className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${TIER_COLORS[selectedCustomer.tier] ?? TIER_COLORS.standard}`}>
                {selectedCustomer.tier}
              </span>
            </div>
          </div>
          {selectedOrder && (
            <div className="mt-3 border-t border-white/10 pt-3">
              <p className="text-xs text-gray-400 truncate">{selectedOrder.product_name}</p>
              <p className="text-xs font-semibold text-gray-200">${selectedOrder.amount?.toFixed(2)}</p>
            </div>
          )}
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom actions */}
      <div className="border-t border-white/10 px-4 py-4 space-y-2">
        {view === 'chat' && (
          <button
            onClick={reset}
            className="w-full rounded-lg border border-white/10 px-3 py-2 text-xs text-gray-400 hover:bg-white/5 hover:text-gray-200 transition-colors"
          >
            + New Conversation
          </button>
        )}
        {view === 'admin' && (
          <button
            onClick={() => {
              localStorage.removeItem('admin_token')
              window.location.reload()
            }}
            className="w-full rounded-lg border border-white/10 px-3 py-2 text-xs text-gray-400 hover:bg-white/5 hover:text-gray-200 transition-colors"
          >
            Sign out
          </button>
        )}
      </div>
    </aside>
  )
}

function AdminView() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const { data } = useAdminRuns(1)
  const runs = data?.items ?? []

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Agent Runs</h2>
      <MetricsPanel runs={runs} />
      <div className="flex gap-4">
        <div className={`${selectedRunId ? 'w-1/2' : 'w-full'} transition-all`}>
          <RunsTable onSelectRun={setSelectedRunId} selectedRunId={selectedRunId} />
        </div>
        {selectedRunId && (
          <div className="w-1/2 rounded-xl border bg-white shadow-sm">
            <div className="flex items-center justify-between border-b px-4 py-2">
              <h3 className="text-sm font-semibold text-gray-700">Run Detail</h3>
              <button
                className="text-xs text-gray-400 hover:text-gray-600"
                onClick={() => setSelectedRunId(null)}
              >
                ✕
              </button>
            </div>
            <RunDetail runId={selectedRunId} />
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<View>('chat')

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar view={view} setView={setView} />

      <main className="flex flex-1 flex-col overflow-hidden">
        {view === 'chat' && (
          <ErrorBoundary>
            <div className="flex-1 overflow-hidden">
              <ChatWindow />
            </div>
          </ErrorBoundary>
        )}
        {view === 'login' && (
          <ErrorBoundary>
            <div className="flex-1 overflow-y-auto bg-gray-50">
              <Login onSuccess={() => setView('admin')} />
            </div>
          </ErrorBoundary>
        )}
        {view === 'admin' && (
          <ErrorBoundary>
            <div className="flex-1 overflow-hidden">
              <AdminView />
            </div>
          </ErrorBoundary>
        )}
      </main>
    </div>
  )
}
