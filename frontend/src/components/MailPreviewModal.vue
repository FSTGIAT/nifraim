<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="state.open" class="fm-overlay" @click.self="close">
        <div class="fm-card mail-preview-card">
          <div class="fm-header">
            <div class="fm-header-info">
              <span class="fm-title">{{ state.subject || 'דואר חדש' }}</span>
              <span class="fm-count">אל: {{ state.to || '—' }}</span>
            </div>
            <button class="fm-close" @click="close" aria-label="סגור">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="mail-preview-info">
            הרשימה ארוכה מדי מכדי לפתוח דואר ישירות. העתק את התוכן ופתח את הדואר — התוכן יישאר בלוח.
          </div>
          <textarea
            class="mail-preview-body"
            readonly
            :value="state.body"
            ref="bodyRef"
          ></textarea>
          <div class="mail-preview-actions">
            <button class="mp-btn mp-copy" @click="copyBody">
              <span v-if="copied">✓ הועתק</span>
              <span v-else>העתק תוכן</span>
            </button>
            <button class="mp-btn mp-open" @click="openCompose">פתח דואר</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { mailPreviewState, closeMailPreview } from '../utils/mailPreviewState.js'
import { openMailCompose } from '../utils/mailHelper.js'

const state = mailPreviewState
const bodyRef = ref(null)
const copied = ref(false)

function close() {
  closeMailPreview()
  copied.value = false
}

async function copyBody() {
  try {
    await navigator.clipboard.writeText(state.body)
  } catch {
    bodyRef.value?.select()
    try { document.execCommand('copy') } catch { /* noop */ }
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

async function openCompose() {
  await openMailCompose({ to: state.to, subject: state.subject, body: '' })
}
</script>

<style scoped>
.fm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1010;
  padding: 24px;
}

.fm-card.mail-preview-card {
  background: #fff;
  border-radius: 12px;
  width: min(640px, 100%);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
}

.fm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e5e5;
  gap: 12px;
}

.fm-header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.fm-title {
  font-weight: 700;
  color: var(--color-text, #1a1a1a);
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fm-count {
  font-size: 0.8rem;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fm-close {
  background: transparent;
  border: none;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  color: #555;
}
.fm-close:hover { background: #f3f3f3; }

.mail-preview-info {
  padding: 12px 20px;
  font-size: 0.85rem;
  color: #555;
  background: #fff8ed;
  border-bottom: 1px solid #f5e2c4;
}

.mail-preview-body {
  flex: 1 1 auto;
  margin: 16px 20px 0;
  min-height: 220px;
  padding: 12px;
  font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
  font-size: 0.85rem;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  resize: vertical;
  direction: rtl;
  white-space: pre-wrap;
  background: #fafafa;
}

.mail-preview-actions {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  justify-content: flex-end;
}

.mp-btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.mp-copy {
  background: #f5f5f5;
  color: #1a1a1a;
  border: 1px solid #d9d9d9;
}
.mp-copy:hover { background: #ececec; }

.mp-open {
  background: #f57c00;
  color: #fff;
}
.mp-open:hover { background: #e76b00; }

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
