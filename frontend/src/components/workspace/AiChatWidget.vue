<template>
  <div class="ai-chat-widget">
    <div class="chat-card">
      <div class="chat-header">
        <div class="chat-header-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <span class="chat-header-title">עוזר AI</span>
        <button v-if="chatStore.messages.length" class="chat-clear-btn" @click="chatStore.clearMessages" title="נקה שיחה">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 105.64-11.95L1 10"/>
          </svg>
        </button>
      </div>

      <!-- Data source tags -->
      <div v-if="!hideSources && chatStore.sources.length" class="chat-sources">
        <span class="sources-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/>
          </svg>
          מקורות נתונים:
        </span>
        <button
          v-for="src in chatStore.sources"
          :key="src.label"
          class="source-tag"
          :class="src.type"
          @click="onSourceClick(src)"
        >{{ src.label }}</button>
      </div>

      <!-- Messages area -->
      <div v-if="chatStore.messages.length" class="chat-messages" ref="messagesEl">
        <div
          v-for="(msg, i) in chatStore.messages"
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
              v-if="msg.role === 'assistant' && chatStore.loading && i === chatStore.messages.length - 1 && !msg.content"
              class="typing-indicator"
            >
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </span>
          </div>
        </div>
      </div>

      <!-- Suggestion chips (only when no messages) -->
      <div v-if="!chatStore.messages.length" class="chat-suggestions">
        <button
          v-for="s in suggestions"
          :key="s"
          class="suggestion-chip"
          @click="send(s)"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          {{ s }}
        </button>
      </div>

      <!-- Error -->
      <div v-if="chatStore.error" class="chat-error">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        {{ chatStore.error }}
      </div>

      <!-- Input bar -->
      <div class="chat-input-bar">
        <input
          v-model="input"
          class="chat-input"
          placeholder="שאל שאלה על הנתונים שלך..."
          @keydown.enter.prevent="send(input)"
          :disabled="chatStore.loading"
        />
        <button
          class="chat-send-btn"
          @click="send(input)"
          :disabled="!input.trim() || chatStore.loading"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, computed } from 'vue'
import { useChatStore } from '../../stores/chat.js'
import { renderMarkdown } from '../../utils/renderMarkdown.js'

const emit = defineEmits(['navigate-tab'])

const props = defineProps({
  // When set (e.g. 'agency_accountant') the chat uses the agency-flavored
  // system prompt + agency-aggregated context. Default = regular agent persona.
  promptPersona: { type: String, default: null },
  // Override default suggestion chips (used by the agency dashboard).
  customSuggestions: { type: Array, default: null },
  // Hide the data-source tags row (super-user doesn't have personal sources).
  hideSources: { type: Boolean, default: false },
})

const chatStore = useChatStore()
const input = ref('')
const messagesEl = ref(null)

const sourceTabMap = {
  production: 'production',
  commission: 'comparison',
  myfile: 'recruits',
}

function onSourceClick(src) {
  const tab = sourceTabMap[src.type]
  if (!tab) return
  if (src.type === 'commission') {
    emit('navigate-tab', { tab, company: src.label, uploadId: src.upload_id })
  } else {
    emit('navigate-tab', tab)
  }
}

onMounted(() => {
  if (!props.hideSources && !chatStore.sourcesLoaded) {
    chatStore.fetchSources()
  }
})

const defaultSuggestions = [
  'מה סטטוס ההתאמות שלי?',
  'אילו חברות עם הכי הרבה רשומות?',
  'מה סך הפרמיות שלי?',
]
const suggestions = computed(() => props.customSuggestions || defaultSuggestions)

async function send(text) {
  const q = text?.trim()
  if (!q || chatStore.loading) return
  input.value = ''
  await chatStore.sendMessage(q, null, props.promptPersona)
}

watch(
  () => chatStore.messages.length && chatStore.messages[chatStore.messages.length - 1]?.content,
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
.ai-chat-widget {
  max-width: 720px;
  margin: 16px auto 0;
  padding: 0 24px;
}

.chat-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 0;
  overflow: hidden;
}

/* Header */
.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--glass);
}

.chat-header-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.chat-header-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text);
  flex: 1;
}

.chat-clear-btn {
  width: 28px;
  height: 28px;
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

.chat-clear-btn:hover {
  background: var(--border-subtle);
  color: var(--text);
}

/* Data sources */
.chat-sources {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.01);
}

.sources-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  letter-spacing: -0.2px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.source-tag.production {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border: 1px solid rgba(99, 102, 241, 0.15);
}
.source-tag.production:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-1px);
}

.source-tag.commission {
  background: rgba(34, 211, 238, 0.1);
  color: #0891b2;
  border: 1px solid rgba(34, 211, 238, 0.15);
}
.source-tag.commission:hover {
  background: rgba(34, 211, 238, 0.2);
  border-color: rgba(34, 211, 238, 0.3);
  transform: translateY(-1px);
}

.source-tag.myfile {
  background: rgba(167, 139, 250, 0.1);
  color: #7c3aed;
  border: 1px solid rgba(167, 139, 250, 0.15);
}
.source-tag.myfile:hover {
  background: rgba(167, 139, 250, 0.2);
  border-color: rgba(167, 139, 250, 0.3);
  transform: translateY(-1px);
}

/* Messages */
.chat-messages {
  max-height: 380px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-subtle) transparent;
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
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
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
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  line-height: 1.65;
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
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typingBounce 1.2s ease-in-out infinite;
}

.typing-indicator .dot:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* Rendered markdown */
.message-content.rendered :deep(p) {
  margin: 0 0 6px;
}

.message-content.rendered :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content.rendered :deep(strong) {
  font-weight: 700;
  color: var(--text);
}

/* Tables */
.message-content.rendered :deep(.chat-table-wrap) {
  overflow-x: auto;
  margin: 10px -14px;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.message-content.rendered :deep(.chat-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  direction: rtl;
}

.message-content.rendered :deep(.chat-table th) {
  background: rgba(0, 0, 0, 0.03);
  font-weight: 700;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  padding: 8px 14px;
  text-align: right;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
  position: sticky;
  top: 0;
}

.message-content.rendered :deep(.chat-table td) {
  padding: 7px 14px;
  text-align: right;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  white-space: nowrap;
}

.message-content.rendered :deep(.chat-table tr:last-child td) {
  border-bottom: none;
}

.message-content.rendered :deep(.chat-table tr:nth-child(even) td) {
  background: rgba(0, 0, 0, 0.015);
}

.message-content.rendered :deep(.chat-table tr:hover td) {
  background: var(--primary-glow);
}

.message-content.rendered :deep(.chat-table .ltr-number) {
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
  padding: 16px;
}

.suggestion-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--bg);
  color: var(--text-secondary);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: right;
}

.suggestion-chip svg {
  flex-shrink: 0;
  color: var(--text-muted);
  transition: color 0.2s ease;
}

.suggestion-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light);
  box-shadow: var(--shadow-sm);
}

.suggestion-chip:hover svg {
  color: var(--primary);
}

/* Error */
.chat-error {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
  color: var(--red);
  font-size: 12.5px;
  padding: 8px 16px;
  background: var(--red-light);
  border-top: 1px solid var(--border-subtle);
}

/* Input */
.chat-input-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 14px;
  border-top: 1px solid var(--border-subtle);
  background: var(--glass);
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  font-size: 13.5px;
  font-family: inherit;
  color: var(--text);
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-input:focus {
  border-color: var(--primary);
  box-shadow: var(--shadow-glow);
}

.chat-input::placeholder {
  color: var(--text-muted);
}

.chat-send-btn {
  width: 36px;
  height: 36px;
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

@media (max-width: 768px) {
  .ai-chat-widget {
    padding: 0 12px;
    margin-top: 20px;
  }

  .message-bubble {
    max-width: 92%;
  }

  .message-content.rendered :deep(.chat-table th),
  .message-content.rendered :deep(.chat-table td) {
    padding: 6px 10px;
    font-size: 11.5px;
  }
}
</style>
