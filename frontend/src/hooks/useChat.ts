import { useCallback, useRef } from 'react'
import { apiClient } from '../lib/api'
import { useChatStore, type Message } from '../store/chat'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export function useChat() {
  const {
    conversationId,
    selectedCustomer,
    selectedOrder,
    setConversationId,
    addMessage,
    setStreaming,
    isStreaming,
  } = useChatStore()

  const esRef = useRef<EventSource | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const ensureConversation = useCallback(async (): Promise<string> => {
    if (conversationId) return conversationId
    const { data } = await apiClient.post<{ conversation_id: string }>(
      '/api/v1/conversations',
      { customer_id: selectedCustomer!.id },
    )
    setConversationId(data.conversation_id)
    return data.conversation_id
  }, [conversationId, selectedCustomer, setConversationId])

  const openStream = useCallback(
    (convId: string, onResult: () => void) => {
      esRef.current?.close()
      const url = `${BASE_URL}/api/v1/conversations/${convId}/stream`
      const es = new EventSource(url)
      esRef.current = es

      const streamingMsgId = crypto.randomUUID()
      let accumulated = ''
      let bubbleAdded = false

      es.onmessage = (event: MessageEvent<string>) => {
        try {
          const parsed = JSON.parse(event.data) as Record<string, unknown>

          if (parsed.event === 'heartbeat') return

          if (parsed.event === 'token' && typeof parsed.text === 'string') {
            accumulated += parsed.text
            if (!bubbleAdded) {
              addMessage({
                id: streamingMsgId,
                role: 'assistant',
                content: accumulated,
                created_at: new Date().toISOString(),
              })
              bubbleAdded = true
            } else {
              useChatStore.getState().patchMessage(streamingMsgId, { content: accumulated })
            }
            return
          }

          if (parsed.event === 'done') {
            const decision = typeof parsed.decision === 'string' ? parsed.decision : undefined
            useChatStore.getState().patchMessage(streamingMsgId, {
              decision: decision as Message['decision'],
            })
            setStreaming(false)
            es.close()
            esRef.current = null
            reconnectAttemptsRef.current = 0
            onResult()
            return
          }

          if (parsed.event === 'error') {
            setStreaming(false)
            es.close()
            esRef.current = null
            if (!bubbleAdded) {
              addMessage({
                id: streamingMsgId,
                role: 'assistant',
                content: 'Request timed out. Please try again.',
                created_at: new Date().toISOString(),
              })
            }
            return
          }
        } catch {
          // malformed SSE payload — ignore
        }
      }

      es.onerror = () => {
        es.close()
        esRef.current = null
        if (reconnectAttemptsRef.current < 3) {
          reconnectAttemptsRef.current += 1
          setTimeout(() => openStream(convId, onResult), reconnectAttemptsRef.current * 1000)
        } else {
          setStreaming(false)
          reconnectAttemptsRef.current = 0
          addMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: 'Connection lost. Please try again.',
            created_at: new Date().toISOString(),
          })
        }
      }
    },
    [addMessage, setStreaming],
  )

  const sendMessage = useCallback(
    async (text: string) => {
      if (!selectedCustomer || !selectedOrder || isStreaming) return

      const convId = await ensureConversation()

      addMessage({
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      })

      setStreaming(true)
      reconnectAttemptsRef.current = 0

      await apiClient.post(`/api/v1/conversations/${convId}/message`, {
        order_id: selectedOrder.id,
        message: text,
      })

      openStream(convId, () => {})
    },
    [selectedCustomer, selectedOrder, isStreaming, ensureConversation, addMessage, setStreaming, openStream],
  )

  const closeStream = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  return { sendMessage, isStreaming, closeStream }
}
