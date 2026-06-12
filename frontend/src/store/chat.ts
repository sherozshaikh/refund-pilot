import { create } from 'zustand'
import type { Customer, Order } from '../lib/types'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  decision?: 'approved' | 'denied' | 'escalated' | 'fallback'
}

interface ChatStore {
  selectedCustomer: Customer | null
  selectedOrder: Order | null
  conversationId: string | null
  messages: Message[]
  isStreaming: boolean
  setCustomer: (customer: Customer | null) => void
  setOrder: (order: Order | null) => void
  setConversationId: (id: string) => void
  addMessage: (msg: Message) => void
  patchMessage: (id: string, patch: Partial<Omit<Message, 'id'>>) => void
  setStreaming: (streaming: boolean) => void
  reset: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  selectedCustomer: null,
  selectedOrder: null,
  conversationId: null,
  messages: [],
  isStreaming: false,
  setCustomer: (customer) =>
    set({ selectedCustomer: customer, selectedOrder: null, messages: [], conversationId: null }),
  setOrder: (order) => set({ selectedOrder: order }),
  setConversationId: (id) => set({ conversationId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  patchMessage: (id, patch) =>
    set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)) })),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  reset: () =>
    set({ selectedCustomer: null, selectedOrder: null, conversationId: null, messages: [], isStreaming: false }),
}))
