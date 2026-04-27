<template>
  <Teleport to="body">
    <Transition name="ai-sheet-overlay">
      <div v-if="open" class="ai-sheet-overlay" @click.self="close" />
    </Transition>
    <Transition name="ai-sheet">
      <aside v-if="open" class="ai-sheet" role="dialog" aria-modal="true" :aria-label="headerLabel">
        <header class="ai-sheet-head">
          <div class="ai-sheet-head-left">
            <span class="ai-sheet-badge" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8z"/>
                <path d="M19 3v4"/>
                <path d="M5 17v4"/>
                <path d="M3 19h4"/>
                <path d="M17 19h4"/>
              </svg>
            </span>
            <div class="ai-sheet-titles">
              <span class="ai-sheet-title">עוזר AI</span>
              <span class="ai-sheet-sub" v-if="viewTitle">· {{ viewTitle }}</span>
            </div>
          </div>
          <div class="ai-sheet-actions">
            <button
              v-if="chatStore.messages.length"
              class="ai-sheet-icon-btn"
              @click="chatStore.clearMessages"
              title="נקה שיחה"
              type="button"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 105.64-11.95L1 10"/>
              </svg>
            </button>
            <button class="ai-sheet-icon-btn" @click="close" title="סגור" type="button">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </header>

        <div v-if="chatStore.error" class="ai-sheet-error">{{ chatStore.error }}</div>

        <div class="ai-sheet-body" ref="bodyEl">
          <div v-if="!chatStore.messages.length" class="ai-sheet-empty">
            <span class="ai-sheet-empty-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
              </svg>
            </span>
            <p class="ai-sheet-empty-title">שאל אותי על המסך הזה</p>
            <p class="ai-sheet-empty-sub">אענה על בסיס הנתונים שלך — חברות, עמלות, לקוחות שהשתנו.</p>
          </div>

          <div
            v-for="(msg, i) in chatStore.messages"
            :key="i"
            class="ai-msg"
            :class="msg.role"
          >
            <div class="ai-msg-avatar" :class="msg.role" aria-hidden="true">
              {{ msg.role === 'user' ? 'א' : 'AI' }}
            </div>
            <div class="ai-msg-bubble">
              <div
                v-if="msg.role === 'assistant'"
                class="ai-msg-content rendered"
                v-html="renderMarkdown(msg.content)"
              />
              <div v-else class="ai-msg-content">{{ msg.content }}</div>
              <span
                v-if="msg.role === 'assistant' && chatStore.loading && i === chatStore.messages.length - 1 && !msg.content"
                class="ai-typing"
                aria-label="כותב…"
              >
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </span>
            </div>
          </div>
        </div>

        <form class="ai-sheet-input-row" @submit.prevent="submit">
          <textarea
            ref="inputEl"
            v-model="draft"
            class="ai-sheet-input"
            rows="1"
            maxlength="500"
            placeholder="שאל שאלה…"
            @keydown="onKeydown"
            @input="autoSize"
          ></textarea>
          <button
            class="ai-sheet-send"
            type="submit"
            :disabled="!canSend"
            :aria-disabled="!canSend"
            title="שלח"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </form>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { useChatStore } from '../../stores/chat.js'
import { renderMarkdown } from '../../utils/renderMarkdown.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  viewTitle: { type: String, default: '' },
  viewContext: { type: String, default: '' },
  initialQuestion: { type: String, default: '' },
  // When set (e.g. 'agency_accountant'), the chat uses the agency-flavored
  // system prompt + agency-aggregated context.
  promptPersona: { type: String, default: null },
})
const emit = defineEmits(['update:open', 'latest-viz'])

const chatStore = useChatStore()
const draft = ref('')
const bodyEl = ref(null)
const inputEl = ref(null)
let lastTrigger = null

const headerLabel = computed(() => `עוזר AI${props.viewTitle ? ' · ' + props.viewTitle : ''}`)
const canSend = computed(() => !!draft.value.trim() && !chatStore.loading)

function close() {
  emit('update:open', false)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  } else if (e.key === 'Escape') {
    close()
  }
}

function autoSize() {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 96) + 'px'
}

async function submit() {
  const text = draft.value.trim()
  if (!text || chatStore.loading) return
  draft.value = ''
  nextTick(autoSize)
  await chatStore.sendMessage(text, props.viewContext || null, props.promptPersona || null)
}

function onEscape(e) {
  if (e.key === 'Escape' && props.open) close()
}

// Open / close lifecycle — focus, escape, initial question
watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    lastTrigger = document.activeElement
    window.addEventListener('keydown', onEscape)
    await nextTick()
    inputEl.value?.focus()
    if (props.initialQuestion && props.initialQuestion.trim()) {
      const q = props.initialQuestion.trim()
      await chatStore.sendMessage(q, props.viewContext || null, props.promptPersona || null)
    }
  } else {
    window.removeEventListener('keydown', onEscape)
    // Return focus to trigger
    if (lastTrigger && typeof lastTrigger.focus === 'function') {
      lastTrigger.focus()
    }
  }
})

// Auto-scroll to latest message during streaming
watch(
  () => chatStore.messages.length && chatStore.messages[chatStore.messages.length - 1]?.content,
  () => {
    nextTick(() => {
      if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight
    })
  }
)

// Emit the latest viz payload (if any) so a sibling AiVizPanel can render it.
// We forward a fresh reference each time so watchers on the parent always fire.
const latestViz = computed(() => {
  for (let i = chatStore.messages.length - 1; i >= 0; i--) {
    const m = chatStore.messages[i]
    if (m.role === 'assistant' && m.viz) return m.viz
  }
  return null
})
watch(latestViz, (v) => emit('latest-viz', v), { deep: false })

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscape)
})
</script>

<style scoped>
.ai-sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 12, 6, 0.28);
  backdrop-filter: blur(3px);
  z-index: 1004;
}

.ai-sheet {
  position: fixed;
  top: 0;
  bottom: 0;
  inset-inline-end: 0;
  width: 420px;
  max-width: 92vw;
  background: #ffffff;
  border-inline-start: 1px solid var(--border-subtle);
  box-shadow: -18px 0 48px rgba(17, 12, 6, 0.12), -2px 0 6px rgba(17, 12, 6, 0.04);
  z-index: 1005;
  display: flex;
  flex-direction: column;
  font-family: inherit;
}

.ai-sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
  background:
    linear-gradient(180deg, rgba(245, 124, 0, 0.05) 0%, #ffffff 100%);
}
.ai-sheet-head-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.ai-sheet-badge {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.32);
  flex-shrink: 0;
}
.ai-sheet-titles { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
.ai-sheet-title { font-size: 14px; font-weight: 800; color: var(--text); }
.ai-sheet-sub { font-size: 12px; color: var(--text-muted); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.ai-sheet-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.ai-sheet-icon-btn {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.ai-sheet-icon-btn:hover {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: rgba(245, 124, 0, 0.18);
}

.ai-sheet-error {
  margin: 10px 14px 0;
  padding: 8px 12px;
  font-size: 12px;
  color: #8A1111;
  background: rgba(234, 0, 30, 0.06);
  border: 1px solid rgba(234, 0, 30, 0.2);
  border-radius: var(--radius-sm);
}

.ai-sheet-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scrollbar-width: thin;
}

.ai-sheet-empty {
  margin: auto;
  text-align: center;
  max-width: 280px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.ai-sheet-empty-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: var(--primary-light);
  color: var(--primary-deep);
  margin-bottom: 4px;
}
.ai-sheet-empty-title { font-size: 14px; font-weight: 700; color: var(--text); margin: 0; }
.ai-sheet-empty-sub { font-size: 12px; line-height: 1.5; margin: 0; color: var(--text-muted); }

.ai-msg {
  display: flex;
  gap: 8px;
  max-width: 100%;
}
.ai-msg.user { flex-direction: row-reverse; }
.ai-msg-avatar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.3px;
}
.ai-msg-avatar.user {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  box-shadow: 0 3px 8px rgba(245, 124, 0, 0.28);
}
.ai-msg-avatar.assistant {
  background: var(--bg);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.ai-msg-bubble {
  max-width: calc(100% - 36px);
  border-radius: 14px;
  padding: 10px 12px;
  font-size: 13.5px;
  line-height: 1.55;
  word-wrap: break-word;
}
.ai-msg.user .ai-msg-bubble {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  border-bottom-right-radius: 4px;
}
.ai-msg.assistant .ai-msg-bubble {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border-subtle);
  border-bottom-left-radius: 4px;
}
.ai-msg-content :deep(p) { margin: 0 0 6px; }
.ai-msg-content :deep(p:last-child) { margin-bottom: 0; }
.ai-msg-content :deep(strong) { font-weight: 700; color: var(--primary-deep); }
.ai-msg.user .ai-msg-content :deep(strong) { color: #ffffff; }
.ai-msg-content :deep(.chat-table-wrap) {
  margin: 6px 0;
  overflow-x: auto;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}
.ai-msg-content :deep(.chat-table) { width: 100%; border-collapse: collapse; font-size: 12px; }
.ai-msg-content :deep(.chat-table th),
.ai-msg-content :deep(.chat-table td) { padding: 6px 8px; text-align: start; border-bottom: 1px solid var(--border-subtle); }
.ai-msg-content :deep(.chat-table th) { background: var(--bg); font-weight: 700; }
.ai-msg-content :deep(.ltr-number) { direction: ltr; display: inline-block; unicode-bidi: isolate; }

.ai-typing { display: inline-flex; gap: 3px; align-items: center; padding: 2px 0; }
.ai-typing .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: aiTypingBlink 1.2s infinite ease-in-out;
}
.ai-typing .dot:nth-child(2) { animation-delay: 0.15s; }
.ai-typing .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes aiTypingBlink {
  0%, 60%, 100% { opacity: 0.25; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-2px); }
}

.ai-sheet-input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px 14px;
  border-top: 1px solid var(--border-subtle);
  background: #ffffff;
}
.ai-sheet-input {
  flex: 1;
  resize: none;
  min-height: 38px;
  max-height: 96px;
  padding: 9px 12px;
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.4;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.ai-sheet-input:focus {
  border-color: rgba(245, 124, 0, 0.45);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.12);
  background: #ffffff;
}
.ai-sheet-send {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.3);
}
.ai-sheet-send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.38);
}
.ai-sheet-send:disabled { opacity: 0.4; cursor: default; box-shadow: none; }

/* Transitions */
.ai-sheet-overlay-enter-active,
.ai-sheet-overlay-leave-active { transition: opacity 0.22s var(--transition); }
.ai-sheet-overlay-enter-from,
.ai-sheet-overlay-leave-to { opacity: 0; }

.ai-sheet-enter-active { transition: transform 0.28s var(--transition), opacity 0.28s var(--transition); }
.ai-sheet-leave-active { transition: transform 0.2s var(--transition), opacity 0.2s var(--transition); }
.ai-sheet-enter-from,
.ai-sheet-leave-to {
  opacity: 0;
  transform: translateX(-40px); /* RTL body → visual right slide-in */
}

/* Responsive: become a bottom sheet on small screens */
@media (max-width: 520px) {
  .ai-sheet {
    top: auto;
    inset-inline-end: 0;
    inset-inline-start: 0;
    left: 12px;
    right: 12px;
    width: auto;
    max-width: none;
    bottom: 0;
    height: 78vh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    border-inline-start: none;
    border-top: 1px solid var(--border-subtle);
    box-shadow: 0 -18px 44px rgba(17, 12, 6, 0.16);
  }
  .ai-sheet-enter-from,
  .ai-sheet-leave-to { transform: translateY(30px); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ai-sheet-enter-active,
  .ai-sheet-leave-active,
  .ai-sheet-overlay-enter-active,
  .ai-sheet-overlay-leave-active { transition-duration: 0.12s; }
  .ai-sheet-enter-from,
  .ai-sheet-leave-to { transform: none; }
  .ai-typing .dot { animation: none; opacity: 0.55; }
}
</style>
