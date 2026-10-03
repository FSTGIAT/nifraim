<template>
  <Teleport to="body">
    <Transition name="ai-sheet-overlay">
      <div v-if="open" class="ai-sheet-overlay" @click.self="close" />
    </Transition>
    <Transition name="ai-sheet">
      <aside v-if="open" class="ai-sheet" :class="{ 'ai-sheet--empty': !chatStore.messages.length }" role="dialog" aria-modal="true" :aria-label="headerLabel">
        <header class="ai-sheet-head">
          <div class="ai-sheet-head-left">
            <ThinkingOrbIsland class="ai-sheet-orb" :state="chatStore.loading ? 'solving' : 'listening'" :size="32" color="#6A48C9" :dot-size="1.5" />
            <div class="ai-sheet-titles">
              <span class="ai-sheet-title" dir="ltr">Nifra <b>AI</b></span>
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
        <div v-if="chatStore.uploadError" class="ai-sheet-error">{{ chatStore.uploadError }}</div>

        <!-- what Nifra AI reads: small library icons, not a chip per file -->
        <AiLibraryIcons class="ai-sheet-libs" :documents="chatStore.documents" :sources="chatStore.sources" />

        <div class="ai-sheet-body" ref="bodyEl">
          <div v-if="!chatStore.messages.length" class="ai-sheet-empty">
            <ThinkingOrbIsland class="ai-sheet-empty-orb" state="listening" :size="64" color="#6A48C9" :dot-size="1.4" />
            <p class="ai-sheet-empty-sub">שאלו על חברות, עמלות ולקוחות — אענה מהנתונים שלכם.</p>
          </div>

          <div
            v-for="(msg, i) in chatStore.messages"
            :key="i"
            class="ai-msg"
            :class="msg.role"
          >
            <div class="ai-msg-avatar" :class="msg.role" aria-hidden="true">
              <Avatar
                v-if="msg.role === 'user'"
                :name="auth.user?.full_name || ''"
                :username="auth.user?.username || ''"
                :avatar-seed="seedFor(auth.user)"
                :size="32"
              />
              <ThinkingOrbIsland
                v-else
                :state="chatStore.loading && i === chatStore.messages.length - 1 ? 'solving' : 'working'"
                :size="32" color="#6A48C9" :dot-size="1.5"
              />
            </div>
            <div class="ai-msg-bubble">
              <div
                v-if="msg.role === 'assistant'"
                class="ai-msg-content rendered"
                v-html="renderMarkdown(msg.content)"
              />
              <div v-else class="ai-msg-content">{{ msg.content }}</div>
              <AgentCallCard v-if="msg.call" :call="msg.call" :notify="chatStore.notifyCall" />
              <span
                v-if="msg.role === 'assistant' && chatStore.loading && i === chatStore.messages.length - 1 && !msg.content"
                class="ai-typing"
                aria-label="כותב…"
              >
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                <span v-if="msg.status" class="ai-typing-status">{{ msg.status }}…</span>
              </span>
              <!-- Numeric-validator warnings: amounts in the AI's answer that
                   aren't backed by the source data we showed it. Yellow chips
                   make the user pause before trusting the figure. -->
              <div
                v-if="msg.role === 'assistant' && Array.isArray(msg.warnings) && msg.warnings.length"
                class="ai-msg-warnings"
                role="alert"
              >
                <div class="ai-msg-warnings-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                  אזהרה: מספרים שלא אומתו במקור
                </div>
                <ul>
                  <li v-for="(w, wi) in msg.warnings" :key="wi">{{ w }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div v-if="chatStore.uploadingDoc && chatStore.uploadFileName" class="ai-sheet-upload-row">
          <UploadProgressCard
            :file-name="chatStore.uploadFileName"
            :file-size="chatStore.uploadFileSize"
            :progress="chatStore.uploadProgress"
            :stage="chatStore.uploadStage"
            @cancel="chatStore.cancelUpload()"
          />
        </div>

        <!-- Floating composer (Claude-style): a card inside the panel — centred
             under the greeting while empty, docked at the bottom once talking. -->
        <form class="ai-composer" @submit.prevent="submit">
          <input
            ref="fileInputEl"
            type="file"
            accept="application/pdf"
            class="ai-sheet-file-input"
            @change="onFileChosen"
          />
          <!-- AIInput design (pill, send appears once typing), in Vue -->
          <div class="ai-pill" :class="{ 'has-text': !!draft.trim() }">
            <textarea
              ref="inputEl"
              v-model="draft"
              class="ai-pill-input"
              rows="1"
              maxlength="500"
              placeholder="שאלו את Nifra AI…"
              @keydown="onKeydown"
              @input="autoSize"
            ></textarea>
            <button
              type="button"
              class="ai-pill-btn ai-pill-attach"
              :disabled="chatStore.uploadingDoc"
              :aria-busy="chatStore.uploadingDoc"
              :title="chatStore.uploadingDoc ? 'מעבד מסמך…' : 'צרף מסמך PDF'"
              @click="openFilePicker"
            >
              <span v-if="chatStore.uploadingDoc" class="ai-sheet-attach-spinner" aria-hidden="true"></span>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            </button>
            <button
              class="ai-pill-btn ai-pill-send"
              type="submit"
              :disabled="!canSend"
              :aria-disabled="!canSend"
              title="שלח"
            >
              <!-- lucide CornerLeftUp (RTL mirror of the design's CornerRightUp) -->
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="14 9 9 4 4 9"/><path d="M20 20h-7a4 4 0 0 1-4-4V4"/></svg>
            </button>
          </div>
        </form>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import AgentCallCard from '../ai/AgentCallCard.vue'
import Avatar from '../Avatar.vue'
import { useAuthStore } from '../../stores/auth.js'
import { seedFor } from '../../utils/avatarSeed.js'
import ThinkingOrbIsland from './ThinkingOrbIsland.vue'
import AiLibraryIcons from './AiLibraryIcons.vue'
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { useChatStore } from '../../stores/chat.js'
import { renderMarkdown } from '../../utils/renderMarkdown.js'
import UploadProgressCard from './UploadProgressCard.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  viewTitle: { type: String, default: '' },
  viewContext: { type: String, default: '' },
  initialQuestion: { type: String, default: '' },
})
const emit = defineEmits(['update:open', 'latest-viz', 'latest-vizs'])

const chatStore = useChatStore()
const auth = useAuthStore()
const draft = ref('')
const bodyEl = ref(null)
const inputEl = ref(null)
const fileInputEl = ref(null)
let lastTrigger = null

function openFilePicker() {
  if (chatStore.uploadingDoc) return
  fileInputEl.value?.click()
}

async function onFileChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // allow re-uploading same file later
  if (!file) return
  await chatStore.uploadDocument(file)
  nextTick(() => {
    if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight
  })
}

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

// AIInput: min 52px, grows to 200px
function autoSize() {
  const el = inputEl.value
  if (!el) return
  el.style.height = '52px'
  el.style.height = Math.max(52, Math.min(el.scrollHeight, 200)) + 'px'
}


async function submit() {
  const text = draft.value.trim()
  if (!text || chatStore.loading) return
  draft.value = ''
  nextTick(autoSize)
  await chatStore.sendMessage(text, props.viewContext || null)
}

function onEscape(e) {
  if (e.key === 'Escape' && props.open) close()
}

// Open / close lifecycle — focus, escape, initial question
watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    lastTrigger = document.activeElement
    window.addEventListener('keydown', onEscape)
    if (!chatStore.documentsLoaded) {
      chatStore.loadDocuments()
    }
    if (!chatStore.sourcesLoaded) chatStore.fetchSources()
    await nextTick()
    inputEl.value?.focus()
    if (props.initialQuestion && props.initialQuestion.trim()) {
      const q = props.initialQuestion.trim()
      await chatStore.sendMessage(q, props.viewContext || null)
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

// Emit the latest viz payload(s) so a sibling AiVizPanel can render them.
// We forward a fresh reference each time so watchers on the parent always fire.
// Synthesis answers may carry multiple vizzes — we emit both the full array
// (`latest-vizs`) and the latest single viz (`latest-viz`) for back-compat.
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
  width: 520px;
  max-width: 94vw;
  /* a soft lavender horizon rising from the bottom edge */
  background:
    radial-gradient(130% 42% at 50% 100%, rgba(183, 156, 235, 0.34) 0%, rgba(183, 156, 235, 0) 70%),
    radial-gradient(80% 30% at 85% 100%, rgba(106, 72, 201, 0.14) 0%, rgba(106, 72, 201, 0) 70%),
    linear-gradient(180deg, #FFFFFF 0%, #FBF9FE 100%);
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
  background: var(--bg-surface, #ffffff);
}
.ai-sheet-head-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.ai-sheet-badge {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--bg, #F3F3F3);
  border: 1px solid var(--border-subtle, #E5E5E5);
  color: var(--tab-ai-ink);
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
  background: var(--tab-ai-wash);
  color: var(--tab-ai-ink);
  border-color: rgba(106, 72, 201, 0.18);
}

.ai-sheet-error {
  margin: 10px 14px 0;
  padding: 8px 12px;
  font-size: 12px;
  color: #C23934;
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
  background: var(--tab-ai-wash);
  color: var(--tab-ai-ink);
  margin-bottom: 4px;
}
.ai-sheet-empty-title { font-size: 14px; font-weight: 700; color: var(--text); margin: 0; }
.ai-sheet-empty-sub { font-size: 12px; line-height: 1.5; margin: 0; color: var(--text-muted); }

.ai-msg {
  display: flex;
  gap: 8px;
  max-width: 100%;
}
/* RTL: both speakers start on the right (like the rest of the app) */
.ai-msg-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  overflow: hidden;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.3px;
}
.ai-msg-avatar.user { box-shadow: 0 2px 6px rgba(24, 24, 24, 0.12); }
.ai-msg-avatar.assistant { background: #F6F2FD; }
.ai-msg-bubble {
  max-width: calc(100% - 36px);
  border-radius: 14px;
  padding: 10px 12px;
  font-size: 13.5px;
  line-height: 1.55;
  word-wrap: break-word;
}
/* the agent's own message: a soft lavender bubble, text right-aligned */
.ai-msg.user .ai-msg-bubble {
  max-width: 78%;
  direction: rtl; text-align: start; unicode-bidi: plaintext;
  background: #F2EEFB;
  color: var(--text-primary, #181818);
  border-radius: 18px;
  border-start-start-radius: 6px;
  padding: 10px 14px;
  font-size: 15px;
}
/* Nifra AI's answer: clean text on the panel, no box (Claude-style) */
.ai-msg.assistant .ai-msg-bubble {
  background: transparent;
  color: var(--text-primary, #181818);
  border: none;
  padding: 4px 2px 0;
  font-size: 15px;
  line-height: 1.8;
}
.ai-msg-content :deep(p) { margin: 0 0 6px; }
.ai-msg-content :deep(p:last-child) { margin-bottom: 0; }
.ai-msg-content :deep(strong) { font-weight: 700; color: var(--tab-ai-ink); }
.ai-msg.user .ai-msg-content :deep(strong) { color: var(--tab-ai-ink, #6A48C9); }
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

/* Numeric-validator warning chip — drawn below the assistant message body.
   Soft amber so it reads as caution, not error. */
.ai-msg-warnings {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--amber-light);
  border: 1px solid #F0C869;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--amber);
}
.ai-msg-warnings-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--amber);
}
.ai-msg-warnings ul {
  margin: 0;
  padding-inline-start: 16px;
}
.ai-msg-warnings li { margin: 2px 0; }

.ai-typing { display: inline-flex; gap: 3px; align-items: center; padding: 2px 0; }
.ai-typing .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: aiTypingBlink 1.2s infinite ease-in-out;
}
.ai-typing .dot:nth-child(2) { animation-delay: 0.15s; }
.ai-typing-status { margin-inline-start: 6px; font-size: 12px; color: var(--text-muted); animation: aiStatusIn .35s ease-out; }
@keyframes aiStatusIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
.ai-typing .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes aiTypingBlink {
  0%, 60%, 100% { opacity: 0.25; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-2px); }
}

.ai-sheet-upload-row {
  display: flex;
  justify-content: center;
  padding: 10px 16px 0;
  background: #ffffff;
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
  border-color: rgba(106, 72, 201, 0.45);
  box-shadow: 0 0 0 3px rgba(106, 72, 201, 0.12);
  background: #ffffff;
}
.ai-sheet-send {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--tab-ai), var(--tab-ai-ink));
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  box-shadow: 0 4px 12px rgba(106, 72, 201, 0.3);
}
.ai-sheet-send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(106, 72, 201, 0.38);
}
.ai-sheet-send:disabled { opacity: 0.4; cursor: default; box-shadow: none; }

.ai-sheet-file-input { display: none; }
.ai-sheet-attach {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.15s;
}
.ai-sheet-attach:hover:not(:disabled) {
  background: var(--tab-ai-wash);
  color: var(--tab-ai-ink);
  border-color: rgba(106, 72, 201, 0.32);
}
.ai-sheet-attach:disabled { opacity: 0.55; cursor: default; }
.ai-sheet-attach-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(106, 72, 201, 0.25);
  border-top-color: var(--tab-ai-ink);
  animation: aiAttachSpin 0.8s linear infinite;
}
@keyframes aiAttachSpin {
  to { transform: rotate(360deg); }
}

.ai-doc-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 16px 0;
}
.ai-doc-chip {
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
.ai-doc-chip-error {
  color: #C23934;
  background: rgba(234, 0, 30, 0.06);
  border-color: rgba(234, 0, 30, 0.2);
}
.ai-doc-chip-label {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-doc-chip-x {
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
.ai-doc-chip-x:hover { background: rgba(255, 255, 255, 1); }

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

/* Nifra AI */
.ai-sheet-orb { width: 32px; height: 32px; flex-shrink: 0; }
.ai-sheet-title { font-size: 17px; font-weight: 900; letter-spacing: -0.02em; color: var(--text-primary, #181818); }
.ai-sheet-title b { color: var(--tab-ai-ink, #6A48C9); font-weight: 900; }
.ai-sheet-libs { padding: 10px 18px 0; }
.ai-sheet-empty-orb { width: 64px; height: 64px; margin-bottom: 6px; }
.ai-sheet-empty-sub { font-size: 14px !important; color: var(--text-secondary, #5C5A58) !important; max-width: 280px; }

/* Desktop: Nifra AI opens HORIZONTALLY out of the floating button (right
   edge) — a wide panel revealed from the button's side to the left. */
@media (min-width: 701px) {
  .ai-sheet {
    top: 96px; bottom: auto; right: 98px; left: auto; inset-inline-end: auto;
    width: min(1040px, calc(100vw - 230px));
    height: min(620px, calc(100vh - 124px));
    max-width: none;
    border-radius: 24px;
    border: 1px solid color-mix(in srgb, #6A48C9 16%, var(--border-subtle));
    box-shadow: 0 30px 80px rgba(40, 24, 90, 0.22), 0 4px 14px rgba(40, 24, 90, 0.08);
    overflow: hidden;
  }
  .ai-sheet-enter-active { transition: clip-path 0.5s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.25s ease; }
  .ai-sheet-leave-active { transition: clip-path 0.3s cubic-bezier(0.55, 0, 0.9, 0.4), opacity 0.3s ease; }
  .ai-sheet-enter-from,
  .ai-sheet-leave-to {
    opacity: 0.4;
    transform: none;
    clip-path: inset(0 0 0 100% round 24px); /* collapsed onto the right edge, next to the button */
  }
  .ai-sheet-enter-to,
  .ai-sheet-leave-from { clip-path: inset(0 0 0 0 round 24px); }
  .ai-sheet-empty-sub { max-width: 420px; }
}

/* ── composer: AIInput pill ── */
.ai-composer {
  position: relative; z-index: 2;
  width: min(720px, calc(100% - 40px));
  margin: 0 auto 22px;
}
.ai-pill {
  position: relative;
  border-radius: 26px;
  background: rgba(24, 24, 24, 0.05);
  box-shadow: inset 0 0 0 1px rgba(24, 24, 24, 0.04), 0 10px 30px rgba(40, 24, 90, 0.08);
  transition: background 0.2s ease, box-shadow 0.2s ease;
}
.ai-pill:focus-within { background: #fff; box-shadow: inset 0 0 0 1px rgba(106, 72, 201, 0.35), 0 12px 34px rgba(40, 24, 90, 0.12); }
.ai-pill-input {
  display: block; width: 100%; height: 52px; min-height: 52px; max-height: 200px;
  resize: none; overflow-y: auto; border: none; outline: none; background: transparent;
  /* RTL: attach on the right, mic/send on the left */
  padding: 16px 52px 16px 52px;
  font-family: inherit; font-size: 15.5px; line-height: 1.25; color: var(--text-primary, #181818);
  transition: height 0.1s ease-out;
}
.ai-pill-input::placeholder { color: rgba(24, 24, 24, 0.45); }
.ai-pill-btn {
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 30px; height: 30px; border-radius: 12px; border: none; padding: 0;
  display: grid; place-items: center; cursor: pointer;
  color: rgba(24, 24, 24, 0.7); background: rgba(24, 24, 24, 0.05);
  transition: right 0.2s ease, left 0.2s ease, opacity 0.2s ease, transform 0.2s ease, background 0.15s ease;
}
.ai-pill-btn:hover:not(:disabled) { background: rgba(106, 72, 201, 0.12); color: var(--tab-ai-ink, #6A48C9); }
.ai-pill-attach { right: 12px; }
.ai-pill-send { left: 12px; opacity: 0; transform: translateY(-50%) scale(0.95); pointer-events: none; color: #fff; background: var(--tab-ai-ink, #6A48C9); }
.ai-pill.has-text .ai-pill-send { opacity: 1; transform: translateY(-50%) scale(1); pointer-events: auto; }
.ai-pill-send:hover:not(:disabled) { background: #5A3AB5; color: #fff; }
.ai-pill-send:disabled { opacity: 0.4; }
/* empty: greeting + composer float together in the middle */
.ai-sheet--empty .ai-sheet-body { flex: 0 0 auto; margin-top: auto; padding-bottom: 18px; }
.ai-sheet--empty .ai-composer { margin-bottom: auto; }
.ai-sheet--empty .ai-sheet-empty-sub { font-size: 17px !important; font-weight: 600; }

/* conversation: a readable centred column on a clean surface — the horizon
   glow belongs to the empty greeting only */
.ai-sheet:not(.ai-sheet--empty) {
  background:
    radial-gradient(90% 22% at 50% 100%, rgba(183, 156, 235, 0.22) 0%, rgba(183, 156, 235, 0) 70%),
    #FFFFFF;
}
.ai-sheet:not(.ai-sheet--empty) .ai-sheet-body > .ai-msg,
.ai-sheet:not(.ai-sheet--empty) .ai-sheet-body > * { width: min(760px, 100%); margin-inline: auto; }
</style>
