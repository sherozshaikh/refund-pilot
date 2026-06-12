import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useChatStore } from '../../store/chat'
import { useChat } from '../../hooks/useChat'
import { MessageBubble } from './MessageBubble'

export function ChatWindow() {
  const { messages, selectedCustomer, selectedOrder, isStreaming } = useChatStore()
  const { sendMessage, closeStream } = useChat()

  useEffect(() => closeStream, [closeStream])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
  }, [input])

  const canSend = Boolean(selectedCustomer && selectedOrder && !isStreaming && input.trim())

  const handleSubmit = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!canSend) return
    const text = input.trim()
    setInput('')
    await sendMessage(text)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const lastMsgId = messages.at(-1)?.id

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center px-8">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg">
              <span className="text-xl font-bold text-white">RP</span>
            </div>
            <p className="text-lg font-semibold text-gray-800">Refund Pilot</p>
            <p className="max-w-sm text-sm text-gray-500">
              {selectedCustomer && selectedOrder
                ? `Ready to assist ${selectedCustomer.name}. Type your message below.`
                : 'Select a customer and order from the sidebar to begin.'}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isStreaming={isStreaming && msg.id === lastMsgId && msg.role === 'assistant'}
                customerName={selectedCustomer?.name}
              />
            ))}
            {isStreaming && messages.at(-1)?.role !== 'assistant' && (
              <div className="flex items-start gap-3 px-4 py-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 text-xs font-semibold text-white shadow-sm">
                  RP
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-gray-50 px-4 py-2.5 text-sm text-gray-400 ring-1 ring-gray-200 shadow-sm streaming-cursor">
                  &nbsp;
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t bg-white px-4 py-4">
        <form onSubmit={handleSubmit}>
          <div className="relative flex items-end gap-2 rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm focus-within:border-violet-400 focus-within:ring-2 focus-within:ring-violet-100 transition-all">
            <textarea
              ref={textareaRef}
              className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none min-h-[24px] max-h-[160px] leading-relaxed"
              placeholder={
                !selectedCustomer || !selectedOrder
                  ? 'Select customer and order first…'
                  : isStreaming
                  ? 'Agent is responding…'
                  : 'Message Refund Pilot… (Enter to send, Shift+Enter for newline)'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!selectedCustomer || !selectedOrder || isStreaming}
              rows={1}
              maxLength={2000}
            />
            <button
              type="submit"
              disabled={!canSend}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm transition-all hover:bg-violet-700 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
              </svg>
            </button>
          </div>
          <p className="mt-1.5 text-center text-xs text-gray-400">
            AI-powered refund decisions · Policy-enforced
          </p>
        </form>
      </div>
    </div>
  )
}
