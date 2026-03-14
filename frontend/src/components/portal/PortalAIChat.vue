<template>
  <div class="portal-ai-chat" :class="{ open }">
    <!-- Collapsed bubble -->
    <button v-if="!open" class="chat-bubble" @click="open = true">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
      </svg>
      <span class="bubble-label">שאל אותי</span>
    </button>

    <!-- Expanded chat card -->
    <Transition name="chat-pop">
      <div v-if="open" class="chat-card">
        <div class="chat-header">
          <div class="chat-header-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <span class="chat-title">עוזר תיק ביטוחי</span>
          <span class="msg-counter">{{ msgCount }}/{{ maxMessages }}</span>
          <button class="chat-close" @click="open = false">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <!-- Messages -->
        <div v-if="messages.length" class="chat-messages" ref="messagesEl">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="chat-message"
            :class="msg.role"
          >
            <div class="message-avatar" :class="msg.role">
              {{ msg.role === 'user' ? 'א' : 'AI' }}
            </div>
            <div class="message-bubble">
              <div
                v-if="msg.role === 'assistant'"
                class="message-content rendered"
                v-html="renderMarkdown(msg.content)"
              />
              <div v-else class="message-content">{{ msg.content }}</div>
              <span
                v-if="msg.role === 'assistant' && loading && i === messages.length - 1 && !msg.content"
                class="typing-indicator"
              >
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </span>
            </div>
          </div>
        </div>

        <!-- Suggestions -->
        <div v-if="!messages.length" class="chat-suggestions">
          <button
            v-for="s in suggestions"
            :key="s"
            class="suggestion-chip"
            @click="send(s)"
          >{{ s }}</button>
        </div>

        <!-- Error -->
        <div v-if="error" class="chat-error">{{ error }}</div>

        <!-- Input -->
        <div class="chat-input-bar">
          <input
            v-model="input"
            class="chat-input"
            placeholder="שאל שאלה על התיק שלך..."
            @keydown.enter.prevent="send(input)"
            :disabled="loading || msgCount >= maxMessages"
          />
          <button
            class="chat-send-btn"
            @click="send(input)"
            :disabled="!input.trim() || loading || msgCount >= maxMessages"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  token: { type: String, required: true },
})

const open = ref(false)
const input = ref('')
const messages = ref([])
const loading = ref(false)
const error = ref(null)
const messagesEl = ref(null)
const msgCount = ref(0)
const maxMessages = 20

const suggestions = [
  'מה הצבירה שלי?',
  'אילו מוצרים יש לי?',
  'הסבר לי את הפוליסות שלי',
]

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderMarkdown(text) {
  if (!text) return ''

  const lines = text.split('\n')
  const result = []
  let inTable = false
  let tableRows = []

  function flushTable() {
    if (tableRows.length === 0) return
    let html = '<div class="chat-table-wrap"><table class="chat-table">'
    let headerDone = false
    tableRows.forEach((row) => {
      const cells = row.split('|').filter((_, i, arr) => i > 0 && i < arr.length - 1).map(c => c.trim())
      if (cells.every(c => /^[-:]+$/.test(c))) {
        headerDone = true
        return
      }
      const tag = !headerDone ? 'th' : 'td'
      html += '<tr>' + cells.map(c => `<${tag}>${formatInline(escapeHtml(c))}</${tag}>`).join('') + '</tr>'
    })
    html += '</table></div>'
    result.push(html)
    tableRows = []
    inTable = false
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      inTable = true
      tableRows.push(trimmed)
    } else {
      if (inTable) flushTable()
      if (trimmed) {
        result.push('<p>' + formatInline(escapeHtml(trimmed)) + '</p>')
      }
    }
  }
  if (inTable) flushTable()

  return result.join('')
}

function formatInline(text) {
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/(₪[\d,]+(?:\.\d+)?)/g, '<span class="ltr-number">$1</span>')
  return text
}

async function send(text) {
  const q = text?.trim()
  if (!q || loading.value || msgCount.value >= maxMessages) return
  input.value = ''
  error.value = null
  loading.value = true
  msgCount.value++

  messages.value.push({ role: 'user', content: q })
  messages.value.push({ role: 'assistant', content: '' })
  const assistantIdx = messages.value.length - 1

  const history = messages.value.slice(0, -2).map(m => ({
    role: m.role,
    content: m.content,
  }))

  try {
    const portalToken = sessionStorage.getItem('portal_token')
    const res = await fetch(`/api/portal/${props.token}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${portalToken}`,
      },
      body: JSON.stringify({ question: q, history }),
    })

    if (!res.ok) {
      const detail = res.status === 429 ? 'הגעת למגבלת ההודעות' : 'שגיאה בשרת'
      throw new Error(detail)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.done) break
          if (data.text) {
            messages.value[assistantIdx].content += data.text
          }
        } catch {
          // ignore parse errors
        }
      }
    }
  } catch (e) {
    error.value = e.message
    if (!messages.value[assistantIdx].content) {
      messages.value.splice(assistantIdx, 1)
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => messages.value.length && messages.value[messages.value.length - 1]?.content,
  () => {
    nextTick(() => {
      if (messagesEl.value) {
        messagesEl.value.scrollTop = messagesEl.value.scrollHeight
      }
    })
  }
)
</script>

<style scoped>
.portal-ai-chat {
  position: fixed;
  bottom: 24px;
  left: 24px;
  z-index: 1000;
}

/* Bubble */
.chat-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 28px;
  border: none;
  background: linear-gradient(135deg, var(--primary, #f57c00), #ff9800);
  color: white;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(245, 124, 0, 0.35);
  transition: all 0.3s var(--transition);
  animation: bubblePulse 3s ease-in-out infinite;
}

.chat-bubble:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 28px rgba(245, 124, 0, 0.45);
}

@keyframes bubblePulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(245, 124, 0, 0.35); }
  50% { box-shadow: 0 4px 28px rgba(245, 124, 0, 0.5); }
}

.bubble-label {
  white-space: nowrap;
}

/* Card */
.chat-card {
  width: 380px;
  max-height: 520px;
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.chat-pop-enter-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); }
.chat-pop-leave-active { transition: all 0.2s ease; }
.chat-pop-enter-from { opacity: 0; transform: scale(0.9) translateY(12px); }
.chat-pop-leave-to { opacity: 0; transform: scale(0.95) translateY(8px); }

/* Header */
.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--glass);
}

.chat-header-icon {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.chat-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  flex: 1;
}

.msg-counter {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  direction: ltr;
}

.chat-close {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chat-close:hover {
  background: var(--border-subtle);
  color: var(--text);
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-subtle) transparent;
  min-height: 200px;
  max-height: 340px;
}

.chat-message {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 800;
  flex-shrink: 0;
  letter-spacing: -0.5px;
}

.message-avatar.user {
  background: var(--primary);
  color: #fff;
}

.message-avatar.assistant {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.message-bubble {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.chat-message.user .message-bubble {
  background: var(--primary);
  color: #fff;
  border-top-left-radius: 4px;
  white-space: pre-wrap;
}

.chat-message.assistant .message-bubble {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border-subtle);
  border-top-right-radius: 4px;
}

/* Typing indicator */
.typing-indicator {
  display: inline-flex;
  gap: 3px;
  padding: 4px 0;
}

.typing-indicator .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typingBounce 1.2s ease-in-out infinite;
}

.typing-indicator .dot:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-3px); opacity: 1; }
}

/* Rendered markdown */
.message-content.rendered :deep(p) { margin: 0 0 4px; }
.message-content.rendered :deep(p:last-child) { margin-bottom: 0; }
.message-content.rendered :deep(strong) { font-weight: 700; color: var(--text); }

.message-content.rendered :deep(.chat-table-wrap) {
  overflow-x: auto;
  margin: 6px -12px;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.message-content.rendered :deep(.chat-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 11.5px;
  direction: rtl;
}

.message-content.rendered :deep(.chat-table th) {
  background: rgba(0, 0, 0, 0.03);
  font-weight: 700;
  font-size: 10.5px;
  color: var(--text-muted);
  padding: 6px 10px;
  text-align: right;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.message-content.rendered :deep(.chat-table td) {
  padding: 5px 10px;
  text-align: right;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  white-space: nowrap;
}

.message-content.rendered :deep(.ltr-number) {
  direction: ltr;
  unicode-bidi: embed;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--primary-deep);
}

/* Suggestions */
.chat-suggestions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  flex: 1;
}

.suggestion-chip {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--bg);
  color: var(--text-secondary);
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: right;
}

.suggestion-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light);
}

/* Error */
.chat-error {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--red);
  font-size: 12px;
  padding: 6px 14px;
  background: var(--red-light);
  border-top: 1px solid var(--border-subtle);
}

/* Input */
.chat-input-bar {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 10px 12px;
  border-top: 1px solid var(--border-subtle);
  background: var(--glass);
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  outline: none;
  transition: border-color 0.2s ease;
}

.chat-input:focus {
  border-color: var(--primary);
}

.chat-input::placeholder {
  color: var(--text-muted);
}

.chat-send-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s var(--transition);
  flex-shrink: 0;
}

.chat-send-btn:hover:not(:disabled) {
  background: var(--primary-deep);
  transform: scale(1.05);
}

.chat-send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .portal-ai-chat {
    bottom: 16px;
    left: 16px;
    right: 16px;
  }

  .chat-card {
    width: 100%;
    max-height: 70vh;
  }
}

/* Hide in print */
@media print {
  .portal-ai-chat {
    display: none !important;
  }
}
</style>
