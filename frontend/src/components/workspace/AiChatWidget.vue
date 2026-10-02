<template>
  <div class="ai-chat-widget">
    <div class="chat-card">
      <div class="chat-header">
        <ThinkingOrbIsland class="chat-header-orb" :state="chatStore.loading ? 'solving' : 'working'" :size="32" color="#6A48C9" :dot-size="1.5" />
        <span class="chat-header-title"><span dir="ltr">Nifra <b>AI</b></span></span>
        <AiLibraryIcons class="chat-libs" :documents="chatStore.documents" :sources="chatStore.sources" clickable @open="onLibOpen" />
        <button v-if="chatStore.messages.length" class="chat-clear-btn" @click="chatStore.clearMessages" title="נקה שיחה">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 105.64-11.95L1 10"/>
          </svg>
        </button>
      </div>

      <!-- Messages area -->
      <div v-if="chatStore.messages.length" class="chat-messages" ref="messagesEl">
        <div
          v-for="(msg, i) in chatStore.messages"
          :key="i"
          class="chat-message"
          :class="msg.role"
        >
          <div class="message-avatar" :class="msg.role" aria-hidden="true">
            <Avatar
              v-if="msg.role === 'user'"
              :name="auth.user?.full_name || ''"
              :username="auth.user?.username || ''"
              :avatar-seed="seedFor(auth.user)"
              :size="30"
            />
            <ThinkingOrbIsland
              v-else
              :state="chatStore.loading && i === chatStore.messages.length - 1 ? 'solving' : 'working'"
              :size="32" color="#6A48C9" :dot-size="1.5"
            />
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
              <span v-if="msg.status" class="typing-status">{{ msg.status }}…</span>
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
      <div v-if="chatStore.uploadError" class="chat-error">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        {{ chatStore.uploadError }}
      </div>

      <div v-if="chatStore.uploadingDoc && chatStore.uploadFileName" class="chat-upload-row">
        <UploadProgressCard
          :file-name="chatStore.uploadFileName"
          :file-size="chatStore.uploadFileSize"
          :progress="chatStore.uploadProgress"
          :stage="chatStore.uploadStage"
          @cancel="chatStore.cancelUpload()"
        />
      </div>

      <!-- Input bar -->
      <div class="chat-input-bar" :class="{ 'has-text': !!input.trim() }">
        <input
          ref="fileInputEl"
          type="file"
          accept="application/pdf"
          class="chat-file-input"
          @change="onFileChosen"
        />
        <button
          type="button"
          class="chat-attach-btn"
          :disabled="chatStore.uploadingDoc"
          :aria-busy="chatStore.uploadingDoc"
          :title="chatStore.uploadingDoc ? 'מעבד מסמך…' : 'צרף מסמך PDF'"
          @click="openFilePicker"
        >
          <span v-if="chatStore.uploadingDoc" class="chat-attach-spinner" aria-hidden="true"></span>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
        </button>
        <input
          v-model="input"
          class="chat-input"
          placeholder="שאלו את Nifra AI…"
          @keydown.enter.prevent="send(input)"
          :disabled="chatStore.loading"
        />
        <button
          class="chat-send-btn"
          @click="send(input)"
          :disabled="!input.trim() || chatStore.loading"
        >
          <!-- lucide CornerLeftUp (RTL) — same as the Nifra AI panel -->
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="14 9 9 4 4 9"/><path d="M20 20h-7a4 4 0 0 1-4-4V4"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import ThinkingOrbIsland from './ThinkingOrbIsland.vue'
import Avatar from '../Avatar.vue'
import { useAuthStore } from '../../stores/auth.js'
import { seedFor } from '../../utils/avatarSeed.js'
import AiLibraryIcons from './AiLibraryIcons.vue'
import { ref, nextTick, watch, onMounted, computed } from 'vue'
import { useChatStore } from '../../stores/chat.js'
import { renderMarkdown } from '../../utils/renderMarkdown.js'
import UploadProgressCard from './UploadProgressCard.vue'

const emit = defineEmits(['navigate-tab', 'latest-viz', 'latest-vizs'])

const chatStore = useChatStore()
const input = ref('')
const auth = useAuthStore()
const messagesEl = ref(null)
const fileInputEl = ref(null)

function openFilePicker() {
  if (chatStore.uploadingDoc) return
  fileInputEl.value?.click()
}

async function onFileChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  await chatStore.uploadDocument(file)
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

const sourceTabMap = {
  production: 'production',
  commission: 'comparison',
  myfile: 'recruits',
}

function onLibOpen(tab) {
  emit('navigate-tab', tab)
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
  if (!chatStore.sourcesLoaded) {
    chatStore.fetchSources()
  }
  if (!chatStore.documentsLoaded) {
    chatStore.loadDocuments()
  }
})

// Mirror AiConversationSheet: surface the most recent viz payload(s) so
// the parent view can mount an AiVizPanel as a sibling. Without this
// emit, the SSE-delivered viz lives only on the assistant message and
// has no path to actually render anywhere. Synthesis answers may carry
// multiple vizzes; we emit the full array (and the latest single one for
// any older consumers that still listen to `latest-viz`).
const latestVizs = computed(() => {
  for (let i = chatStore.messages.length - 1; i >= 0; i--) {
    const m = chatStore.messages[i]
    if (m.role === 'assistant' && Array.isArray(m.vizs) && m.vizs.length) return m.vizs
    if (m.role === 'assistant' && m.viz) return [m.viz]
  }
  return null
})
watch(latestVizs, (v) => {
  emit('latest-vizs', v)
  emit('latest-viz', v ? v[v.length - 1] : null)
}, { deep: false })

const suggestions = [
  'מה סטטוס ההתאמות שלי?',
  'אילו חברות עם הכי הרבה רשומות?',
  'מה סך הפרמיות שלי?',
]

async function send(text) {
  const q = text?.trim()
  if (!q || chatStore.loading) return
  input.value = ''
  await chatStore.sendMessage(q)
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
  background: var(--tab-ai-wash);
  color: var(--tab-ai-ink);
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
  background: rgba(127, 86, 217, 0.1);
  color: #7F56D9;
  border: 1px solid rgba(127, 86, 217, 0.15);
}
.source-tag.production:hover {
  background: rgba(127, 86, 217, 0.2);
  border-color: rgba(127, 86, 217, 0.3);
  transform: translateY(-1px);
}

.source-tag.commission {
  background: rgba(46, 132, 74, 0.1);
  color: #2E844A;
  border: 1px solid rgba(46, 132, 74, 0.15);
}
.source-tag.commission:hover {
  background: rgba(46, 132, 74, 0.2);
  border-color: rgba(46, 132, 74, 0.3);
  transform: translateY(-1px);
}

.source-tag.myfile {
  background: rgba(227, 6, 106, 0.1);
  color: #E3066A;
  border: 1px solid rgba(227, 6, 106, 0.15);
}
.source-tag.myfile:hover {
  background: rgba(227, 6, 106, 0.2);
  border-color: rgba(227, 6, 106, 0.3);
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

/* RTL: both speakers start on the right, like the Nifra AI panel */

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  flex-shrink: 0;
  letter-spacing: -0.5px;
}

.message-avatar.user { box-shadow: 0 2px 6px rgba(24, 24, 24, 0.12); }
.message-avatar.assistant { background: #F6F2FD; }

.message-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  line-height: 1.65;
  word-break: break-word;
}

/* the agent's message: soft lavender bubble, right-aligned */
.chat-message.user .message-bubble {
  max-width: 78%;
  direction: rtl; text-align: start; unicode-bidi: plaintext;
  background: #F2EEFB;
  color: var(--text-primary, #181818);
  border-radius: 18px;
  border-start-start-radius: 6px;
  font-size: 14.5px;
  white-space: pre-wrap;
}
/* Nifra AI's answer: clean text, no box */
.chat-message.assistant .message-bubble {
  max-width: calc(100% - 44px);
  background: transparent;
  color: var(--text-primary, #181818);
  border: none;
  padding: 4px 2px 0;
  font-size: 14.5px;
  line-height: 1.8;
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
.typing-status { margin-inline-start: 6px; font-size: 12px; color: var(--text-muted); animation: statusIn .35s ease-out; }
@keyframes statusIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
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
  background: rgba(106, 72, 201, 0.12);
}

.message-content.rendered :deep(.chat-table .ltr-number) {
  direction: ltr;
  unicode-bidi: embed;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--tab-ai-ink);
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
  border-color: var(--tab-ai-ink);
  color: var(--tab-ai-ink);
  background: var(--tab-ai-wash);
  box-shadow: var(--shadow-sm);
}

.suggestion-chip:hover svg {
  color: var(--tab-ai-ink);
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
.chat-upload-row {
  display: flex;
  justify-content: center;
  padding: 10px 14px 0;
  background: var(--glass);
}
/* input: the AIInput pill (same as the Nifra AI panel) */
.chat-input-bar {
  position: relative;
  margin: 10px 14px 14px;
  border-radius: 26px;
  background: rgba(24, 24, 24, 0.05);
  box-shadow: inset 0 0 0 1px rgba(24, 24, 24, 0.04);
  transition: background 0.2s ease, box-shadow 0.2s ease;
}
.chat-input-bar:focus-within { background: #fff; box-shadow: inset 0 0 0 1px rgba(106, 72, 201, 0.35), 0 10px 28px rgba(40, 24, 90, 0.1); }
.chat-input {
  display: block; width: 100%; height: 52px;
  padding: 0 52px; border: none; outline: none; background: transparent;
  font-size: 15px; font-family: inherit; color: var(--text-primary, #181818);
}
.chat-input::placeholder { color: rgba(24, 24, 24, 0.45); }
.chat-attach-btn, .chat-send-btn {
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 30px; height: 30px; border-radius: 12px; border: none; padding: 0;
  display: grid; place-items: center; cursor: pointer;
  transition: opacity 0.2s ease, transform 0.2s ease, background 0.15s ease, color 0.15s ease;
}
.chat-attach-btn { right: 12px; color: rgba(24, 24, 24, 0.7); background: rgba(24, 24, 24, 0.05); }
.chat-attach-btn:hover:not(:disabled) { background: rgba(106, 72, 201, 0.12); color: var(--tab-ai-ink, #6A48C9); }
.chat-send-btn {
  left: 12px; color: #fff; background: var(--tab-ai-ink, #6A48C9);
  opacity: 0; transform: translateY(-50%) scale(0.95); pointer-events: none;
}
.chat-input-bar.has-text .chat-send-btn { opacity: 1; transform: translateY(-50%) scale(1); pointer-events: auto; }
.chat-send-btn:hover:not(:disabled) { background: #5A3AB5; }
.chat-send-btn:disabled { opacity: 0.4; }

/* Attached AI documents */
.chat-doc-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 16px 0;
}
.chat-doc-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--tab-ai-ink);
  background: var(--tab-ai-wash);
  border: 1px solid rgba(106, 72, 201, 0.24);
  border-radius: 999px;
  max-width: 100%;
}
.chat-doc-chip-error {
  color: #C23934;
  background: rgba(234, 0, 30, 0.06);
  border-color: rgba(234, 0, 30, 0.2);
}
.chat-doc-chip-label {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chat-doc-chip-x {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  color: inherit;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}
.chat-doc-chip-x:hover { background: rgba(255, 255, 255, 1); }

/* Paperclip button inside the input bar */
.chat-file-input { display: none; }
.chat-attach-btn:disabled { opacity: 0.55; cursor: default; }
.chat-attach-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(106, 72, 201, 0.25);
  border-top-color: var(--tab-ai-ink);
  animation: chatAttachSpin 0.8s linear infinite;
}
@keyframes chatAttachSpin { to { transform: rotate(360deg); } }

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

/* Nifra AI header: orb + wordmark + library icons */
.chat-header-orb { width: 32px; height: 32px; flex-shrink: 0; }
.chat-header-title { font-size: 16px; font-weight: 900; letter-spacing: -0.02em; color: var(--text-primary, #181818); }
.chat-header-title b { color: var(--tab-ai-ink, #6A48C9); font-weight: 900; }
.chat-libs { margin-inline-start: auto; }
</style>
