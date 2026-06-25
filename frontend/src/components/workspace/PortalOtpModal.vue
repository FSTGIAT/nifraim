<template>
  <Teleport to="body">
    <Transition name="otp">
      <div v-if="open" class="otp-overlay" @click.self="onBackdrop">
        <div class="otp-card" role="dialog" aria-modal="true">
          <header class="otp-head">
            <span class="otp-badge" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                <rect width="14" height="20" x="5" y="2" rx="2"/>
                <path d="M12 18h.01"/>
              </svg>
            </span>
            <div class="otp-titles">
              <h3 class="otp-title">ממתין לקוד SMS</h3>
              <p class="otp-sub">{{ subText }}</p>
            </div>
            <button class="otp-x" @click="$emit('close')" aria-label="סגור" :disabled="submitting">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
              </svg>
            </button>
          </header>

          <div class="otp-body">
            <div class="otp-pulse" aria-hidden="true">
              <span></span><span></span><span></span>
            </div>
            <p class="otp-hint">
              אם הקוד לא מגיע אוטומטית — הזן אותו כאן ידנית
            </p>

            <div class="otp-input-row">
              <input
                v-for="(d, i) in digits"
                :key="i"
                :ref="(el) => setBoxRef(el, i)"
                :value="d"
                class="otp-box ltr-number"
                inputmode="numeric"
                pattern="\d*"
                maxlength="1"
                autocomplete="one-time-code"
                @keydown="onKeydown($event, i)"
                @input="onInput($event, i)"
                @paste="onPaste"
                :disabled="submitting"
              />
            </div>

            <div v-if="error" class="otp-error">{{ error }}</div>

            <p v-if="showForwardHint" class="otp-forward-hint">
              רוצה שזה יקרה לבד? הגדר
              <a href="#" @click.prevent="$emit('open-phone-forward')">העברת SMS אוטומטית</a>
              והטלפון שלך יזין את הקוד עבורך.
            </p>
          </div>

          <footer class="otp-foot">
            <button class="otp-cancel" @click="$emit('close')" :disabled="submitting">סגור</button>
            <button
              class="otp-submit"
              type="button"
              :disabled="submitting || !isComplete"
              @click="submit"
            >
              {{ submitting ? 'שולח…' : 'אשר קוד' }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  run: { type: Object, default: null },
  companyName: { type: String, default: '' },
  credentialOtpMethod: { type: String, default: 'twilio' },
})
const emit = defineEmits(['submit', 'close', 'open-phone-forward'])

const showForwardHint = computed(() => props.credentialOtpMethod !== 'phone_forward')

const digits = ref(Array(6).fill(''))
const boxRefs = ref([])
const submitting = ref(false)
const error = ref('')

function setBoxRef(el, i) {
  if (el) boxRefs.value[i] = el
}

const isComplete = computed(() => digits.value.every((d) => /^\d$/.test(d)))

const subText = computed(() => {
  if (props.companyName) return `${props.companyName} שולח כעת קוד אימות. ברגע שיגיע — האוטומציה תמשיך אוטומטית.`
  return 'הפורטל שולח כעת קוד אימות. ברגע שיגיע — האוטומציה תמשיך אוטומטית.'
})

watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    digits.value = Array(6).fill('')
    error.value = ''
    submitting.value = false
    await nextTick()
    boxRefs.value[0]?.focus()
  }
})

function focusBox(i) {
  if (i < 0) i = 0
  if (i > 5) i = 5
  boxRefs.value[i]?.focus()
  boxRefs.value[i]?.select?.()
}

function onInput(e, i) {
  const v = (e.target.value || '').replace(/\D/g, '').slice(-1)
  digits.value[i] = v
  if (v && i < 5) focusBox(i + 1)
  if (isComplete.value) submit()
}
function onKeydown(e, i) {
  if (e.key === 'Backspace' && !digits.value[i] && i > 0) {
    digits.value[i - 1] = ''
    focusBox(i - 1)
    e.preventDefault()
  } else if (e.key === 'ArrowLeft' && i < 5) {
    focusBox(i + 1); e.preventDefault()
  } else if (e.key === 'ArrowRight' && i > 0) {
    focusBox(i - 1); e.preventDefault()
  } else if (e.key === 'Enter' && isComplete.value) {
    submit()
  }
}
function onPaste(e) {
  const text = (e.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, 6)
  if (!text) return
  e.preventDefault()
  for (let i = 0; i < 6; i++) digits.value[i] = text[i] || ''
  focusBox(Math.min(text.length, 5))
  if (isComplete.value) submit()
}

async function submit() {
  if (submitting.value || !isComplete.value) return
  submitting.value = true
  error.value = ''
  try {
    await emit('submit', digits.value.join(''))
  } catch (e) {
    error.value = 'שגיאה בשליחת הקוד. נסה שוב.'
  } finally {
    submitting.value = false
  }
}

function onBackdrop() {
  if (!submitting.value) emit('close')
}
</script>

<style scoped>
.otp-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 12, 6, 0.42);
  backdrop-filter: blur(4px);
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 20px;
}
.otp-card {
  width: min(440px, 100%);
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 30px 70px rgba(17, 12, 6, 0.22);
  font-family: 'Heebo', sans-serif;
  display: flex;
  flex-direction: column;
}
.otp-card::before {
  content: '';
  display: block;
  height: 3px;
  background: linear-gradient(90deg, transparent, #F57C00, transparent);
}

.otp-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border-subtle);
}
.otp-badge {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.32);
}
.otp-titles { flex: 1; min-width: 0; }
.otp-title { margin: 0; font-size: 15px; font-weight: 800; color: var(--text); }
.otp-sub { margin: 2px 0 0; font-size: 12px; color: var(--text-muted); }

.otp-x {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-subtle);
  background: transparent;
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}
.otp-x:hover { background: var(--bg); color: var(--text); }
.otp-x:disabled { opacity: 0.55; cursor: not-allowed; }

.otp-body { padding: 22px 20px 6px; }

.otp-pulse {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 14px;
}
.otp-pulse span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(245, 124, 0, 0.35);
  animation: pulseDot 1.4s ease-in-out infinite;
}
.otp-pulse span:nth-child(2) { animation-delay: 0.18s; }
.otp-pulse span:nth-child(3) { animation-delay: 0.36s; }
@keyframes pulseDot {
  0%, 100% { transform: scale(0.8); opacity: 0.4; }
  50%      { transform: scale(1.3); opacity: 1; background: #F57C00; }
}

.otp-hint {
  margin: 0 0 12px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-muted);
}

.otp-input-row {
  display: grid;
  grid-template-columns: repeat(6, 36px);
  gap: 6px;
  direction: ltr;
  margin: 0 auto;
  width: fit-content;
  justify-content: center;
}
.otp-box {
  width: 36px;
  height: 42px;
  padding: 0;
  font-size: 18px;
  font-weight: 800;
  text-align: center;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  background: var(--bg);
  border: 1.5px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--text);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
.otp-box:focus {
  border-color: #F57C00;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.18);
}
.otp-box:disabled { opacity: 0.55; cursor: not-allowed; }

.otp-error {
  margin-top: 10px;
  text-align: center;
  font-size: 12px;
  color: #C23934;
  padding: 8px 12px;
  background: rgba(194, 57, 52, 0.08);
  border: 1px solid rgba(194, 57, 52, 0.24);
  border-radius: 8px;
}

.otp-forward-hint {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}
.otp-forward-hint a {
  color: #f57c00;
  font-weight: 600;
  text-decoration: none;
}
.otp-forward-hint a:hover { text-decoration: underline; }

.otp-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px 16px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg);
}
.otp-cancel {
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  border-radius: 9px;
  padding: 9px 16px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.otp-cancel:hover:not(:disabled) { background: var(--card-bg); border-color: var(--text-muted); }
.otp-cancel:disabled { opacity: 0.55; cursor: not-allowed; }

.otp-submit {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: none;
  border-radius: 9px;
  padding: 9px 20px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.3);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
}
.otp-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(245, 124, 0, 0.4);
}
.otp-submit:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

.otp-enter-active, .otp-leave-active { transition: opacity 0.18s ease; }
.otp-enter-active .otp-card, .otp-leave-active .otp-card { transition: transform 0.22s ease, opacity 0.22s ease; }
.otp-enter-from, .otp-leave-to { opacity: 0; }
.otp-enter-from .otp-card, .otp-leave-to .otp-card { transform: translateY(8px) scale(0.98); opacity: 0; }
</style>
