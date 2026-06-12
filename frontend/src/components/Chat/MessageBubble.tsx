import type { Message } from '../../store/chat'

const DECISION_BADGE: Record<string, { label: string; className: string }> = {
  approved:  { label: '✓ Approved',  className: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  denied:    { label: '✕ Denied',    className: 'bg-red-50 text-red-700 border border-red-200' },
  escalated: { label: '⚡ Escalated', className: 'bg-amber-50 text-amber-700 border border-amber-200' },
}

interface Props {
  message: Message
  isStreaming?: boolean
  customerName?: string
}

export function MessageBubble({ message, isStreaming, customerName }: Props) {
  const isUser = message.role === 'user'
  const badge = message.decision ? DECISION_BADGE[message.decision] : null
  const initials = customerName
    ? customerName.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()
    : 'U'

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3 px-4 py-3 group">
        <div className="flex flex-col items-end max-w-[75%]">
          <div className="rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          <span className="mt-1 text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white shadow-sm">
          {initials}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 px-4 py-3 group">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 text-xs font-semibold text-white shadow-sm">
        RP
      </div>
      <div className="flex flex-col max-w-[80%]">
        <div className="rounded-2xl rounded-tl-sm bg-gray-50 px-4 py-2.5 text-sm leading-relaxed text-gray-900 shadow-sm ring-1 ring-gray-200">
          <p className={`whitespace-pre-wrap break-words${isStreaming ? ' streaming-cursor' : ''}`}>
            {message.content}
          </p>
        </div>
        <div className="mt-1.5 flex items-center gap-2">
          {badge && (
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.className}`}>
              {badge.label}
            </span>
          )}
          <span className="text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  )
}
