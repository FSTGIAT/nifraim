<template>
  <div class="thread">
    <div ref="scrollEl" class="thread-scroll">
      <button v-if="store.hasMore" class="load-older" @click="store.loadOlder()">
        טען הודעות קודמות
      </button>

      <div v-if="store.loadingThread" class="thread-state">טוען…</div>

      <div v-else-if="!store.messages.length" class="thread-state thread-empty">
        <Avatar :name="contact.full_name" :username="contact.username" :size="52" />
        <p class="empty-title">התחילו שיחה עם {{ contact.full_name || contact.username }}</p>
        <p class="empty-sub">ההודעה הראשונה תופיע כאן.</p>
      </div>

      <div
        v-for="msg in store.messages"
        :key="msg.id"
        class="msg"
        :class="isMine(msg) ? 'me' : 'them'"
      >
        <div class="msg-bubble" :class="{ pending: msg.pending, failed: msg.failed }">
          <!--
            PLAIN TEXT, deliberately. Message bodies are user-authored, so this must
            never be v-html and never go through renderMarkdown (which the AI sheet
            applies only to the trusted assistant role). Interpolation escapes.
          -->
          <p class="msg-body">{{ msg.body }}</p>
          <span class="msg-time ltr-number">{{ timeOf(msg) }}</span>
        </div>

        <button v-if="msg.failed" class="msg-retry" @click="store.retry(msg)">
          לא נשלח · נסו שוב
        </button>
      </div>
    </div>

    <form class="composer" @submit.prevent="submit">
      <textarea
        ref="inputEl"
        v-model="draft"
        class="composer-input"
        rows="1"
        maxlength="4000"
        :placeholder="`הודעה אל ${contact.full_name || contact.username}…`"
        @input="autoSize"
        @keydown="onKeydown"
      />
      <button type="submit" class="composer-send" :disabled="!draft.trim()" aria-label="שליחה">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20 12 4 4l3 8-3 8z" />
          <path d="M7 12h13" />
        </svg>
      </button>
    </form>

    <p v-if="store.error" class="composer-error">{{ store.error }}</p>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import Avatar from '../Avatar.vue'
import { useMessengerStore } from '../../stores/messenger.js'

const props = defineProps({ contact: { type: Object, required: true } })
const store = useMessengerStore()

const draft = ref('')
const scrollEl = ref(null)
const inputEl = ref(null)

const isMine = (msg) => msg.sender_id === store.myId

function timeOf (msg) {
  const d = new Date(msg.created_at)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function autoSize () {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 120)}px`
}

function onKeydown (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

async function submit () {
  const text = draft.value.trim()
  if (!text) return
  draft.value = ''
  await nextTick(autoSize)
  await store.sendMessage(text)
}

function scrollToBottom () {
  const el = scrollEl.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(() => store.messages.length, () => nextTick(scrollToBottom))
watch(() => store.messages.at(-1)?.body, () => nextTick(scrollToBottom))
onMounted(() => {
  nextTick(scrollToBottom)
  inputEl.value?.focus()
})
</script>

<style scoped>
.thread { display: flex; flex-direction: column; flex: 1; min-height: 0; }

.thread-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.load-older {
  align-self: center;
  background: none;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  padding: 4px 12px;
  font: inherit;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
}
.load-older:hover { background: var(--bg); }

.thread-state {
  margin: auto;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}
.thread-empty { display: grid; justify-items: center; gap: 8px; }
.empty-title { font-size: 14px; font-weight: 700; color: var(--text); margin: 0; }
.empty-sub { margin: 0; font-size: 12px; }

.msg { display: flex; flex-direction: column; max-width: 82%; }
/* Outgoing sits at the inline END, incoming at the inline START — the logical
   form of the LTR convention, so under the RTL root it mirrors to "mine on the
   left", which is what Hebrew messengers do. */
.msg.me { align-self: flex-end; align-items: flex-end; }
.msg.them { align-self: flex-start; align-items: flex-start; }

.msg-bubble {
  border-radius: 14px;
  padding: 8px 11px 6px;
  font-size: 13.5px;
  line-height: 1.55;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
.msg.me .msg-bubble {
  background: linear-gradient(135deg, var(--chart-11), #E23E73);
  color: #fff;
  border-end-end-radius: 4px;   /* tucked toward its own edge */
}
.msg.them .msg-bubble {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border-subtle);
  border-end-start-radius: 4px;
}
.msg-bubble.pending { opacity: 0.62; }
.msg-bubble.failed { background: #FDECEA; color: #B3261E; border: 1px solid #F3B9B3; }

.msg-body { margin: 0; white-space: pre-wrap; }

.msg-time {
  display: block;
  margin-top: 3px;
  font-size: 10px;
  opacity: 0.72;
  text-align: end;
}
.msg.them .msg-time { color: var(--text-muted); }

.msg-retry {
  margin-top: 3px;
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  font-size: 11px;
  color: #B3261E;
  cursor: pointer;
  text-decoration: underline;
}

.composer {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}
.composer-input {
  flex: 1;
  resize: none;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  font: inherit;
  font-size: 13px;
  line-height: 1.5;
  max-height: 120px;
  background: var(--bg);
  color: var(--text);
}
.composer-input:focus-visible {
  outline: none;
  border-color: var(--chart-11);
  box-shadow: 0 0 0 3px rgba(255, 92, 138, 0.16);
}
.composer-send {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--chart-11), #E23E73);
  color: #fff;
  cursor: pointer;
  transition: transform 0.16s var(--transition), opacity 0.16s var(--transition);
}
.composer-send svg { width: 17px; height: 17px; transform: scaleX(-1); }
.composer-send:hover:not(:disabled) { transform: scale(1.06); }
.composer-send:disabled { opacity: 0.42; cursor: default; }

.composer-error {
  margin: 0;
  padding: 0 12px 8px;
  font-size: 11.5px;
  color: #B3261E;
}

@media (prefers-reduced-motion: reduce) {
  .composer-send { transition: none; }
}
</style>
