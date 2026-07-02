<template>
  <Transition name="wic">
    <div v-if="show" class="wic" :class="{ 'wic--done': online }">
      <button class="wic__dismiss" aria-label="סגור" @click="dismiss">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>

      <!-- Glow orbs -->
      <span class="wic__orb wic__orb--1" aria-hidden="true"></span>
      <span class="wic__orb wic__orb--2" aria-hidden="true"></span>

      <div class="wic__head">
        <div class="wic__icon" :class="{ 'wic__icon--on': online }">
          <svg v-if="!online" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/><path d="M12 7v6M9 10l3 3 3-3"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 6 9 17l-5-5"/>
          </svg>
        </div>
        <div class="wic__titles">
          <h3 class="wic__title">{{ online ? 'המחשב מחובר — הכל מוכן' : 'הפעלת הורדה אוטומטית' }}</h3>
          <p class="wic__sub">
            {{ online
              ? 'מעכשיו כל הורדה מהאתר תרוץ אוטומטית מהמחשב שלך — בלי פרוקסי, בלי חסימות.'
              : 'התקנה חד-פעמית: ההורדות ירוצו ישירות מהמחשב שלך (כתובת IP ישראלית), וכל החברות יעבדו.' }}
          </p>
        </div>
        <span class="wic__pill" :class="online ? 'wic__pill--on' : 'wic__pill--wait'">
          <span class="wic__dot"></span>{{ online ? 'מחובר' : 'ממתין לחיבור' }}
        </span>
      </div>

      <div v-if="!online" class="wic__steps">
        <div class="wic__step">
          <span class="wic__num">1</span>
          <div class="wic__steptext">
            <strong>הורידו את קובץ ההתקנה</strong>
            <span>קובץ קטן שמכין את המחשב להורדות אוטומטיות.</span>
          </div>
          <button class="wic__dl" :disabled="downloading" @click="downloadInstaller">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>
            {{ downloading ? 'מוריד…' : 'הורד מתקין' }}
          </button>
        </div>
        <div class="wic__step">
          <span class="wic__num">2</span>
          <div class="wic__steptext">
            <strong>לחצו עליו פעמיים</strong>
            <span>Double-click על הקובץ שירד. אם תופיע אזהרת אבטחה — <code>Run</code>. ההתקנה מתבצעת לבד.</span>
          </div>
        </div>
        <div class="wic__step">
          <span class="wic__num">3</span>
          <div class="wic__steptext">
            <strong>זהו — המחשב יתחבר</strong>
            <span>תוך כ-20 שניות המחוון כאן יהפוך ל"מחובר". השאירו את המחשב והטלפון דולקים.</span>
          </div>
        </div>
      </div>

      <p v-if="hint" class="wic__hint">{{ hint }}</p>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { getUserFlag, setUserFlag } from '../../utils/userFlags.js'
import api from '../../api/client.js'

const store = usePortalAutomationStore()
// Per-user (not browser-global): on a shared browser, a new account must still
// see the install card even if an earlier user dismissed it. The permanent
// entry in the settings gear is the always-available fallback once dismissed.
const dismissed = ref(getUserFlag('worker_install_dismissed') === 'true')
const downloading = ref(false)
const hint = ref('')

const online = computed(() => !!store.workerStatus?.online)
// Show until the worker connects (or the user dismisses). Once connected we show
// the success state briefly, then it can be dismissed.
const show = computed(() => !dismissed.value)

let poll = null
onMounted(() => {
  store.fetchWorkerStatus()
  poll = setInterval(() => store.fetchWorkerStatus(), 8000)
})
onUnmounted(() => { if (poll) clearInterval(poll) })

async function downloadInstaller() {
  downloading.value = true
  hint.value = ''
  try {
    const res = await api.get('/portal-automation/worker/installer', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/octet-stream' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'nifraim-worker-setup.bat'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    hint.value = 'הקובץ ירד. לחצו עליו פעמיים (Double-click). אם מופיעה אזהרת אבטחה — לחצו Run.'
  } catch (e) {
    hint.value = 'ההורדה נכשלה. נסו שוב או פנו לתמיכה.'
  } finally {
    downloading.value = false
  }
}

function dismiss() {
  dismissed.value = true
  setUserFlag('worker_install_dismissed', 'true')
}
</script>

<style scoped>
.wic {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 22px 24px;
  background: linear-gradient(135deg, #0b3b34 0%, #11514a 55%, #0d6b5a 100%);
  color: #eafff7;
  box-shadow: 0 12px 30px rgba(8, 60, 50, 0.28);
  font-family: 'Heebo', sans-serif;
}
.wic--done { background: linear-gradient(135deg, #065f46 0%, #047857 60%, #10b981 100%); }

.wic__orb { position: absolute; border-radius: 50%; filter: blur(38px); opacity: 0.5; pointer-events: none; }
.wic__orb--1 { width: 200px; height: 200px; background: rgba(16,185,129,0.55); top: -70px; left: -40px; }
.wic__orb--2 { width: 160px; height: 160px; background: rgba(110,231,183,0.4); bottom: -60px; right: -30px; }

.wic__dismiss {
  position: absolute; top: 12px; left: 12px; z-index: 2;
  display: inline-flex; border: none; background: rgba(255,255,255,0.12);
  color: #eafff7; border-radius: 8px; padding: 5px; cursor: pointer;
}
.wic__dismiss:hover { background: rgba(255,255,255,0.2); }

.wic__head { position: relative; z-index: 1; display: flex; align-items: center; gap: 14px; }
.wic__icon {
  flex-shrink: 0; width: 50px; height: 50px; border-radius: 14px;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.14); color: #d7fff0;
  border: 1px solid rgba(255,255,255,0.18);
}
.wic__icon--on { background: rgba(255,255,255,0.22); color: #fff; }
.wic__titles { flex: 1; min-width: 0; }
.wic__title { margin: 0 0 3px; font-size: 17px; font-weight: 800; }
.wic__sub { margin: 0; font-size: 13px; line-height: 1.5; color: rgba(234,255,247,0.82); }

.wic__pill {
  flex-shrink: 0; display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 700;
  background: rgba(255,255,255,0.12);
}
.wic__pill--on { background: rgba(255,255,255,0.22); }
.wic__dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.wic__pill--wait .wic__dot { background: #fcd34d; animation: wic-blink 1.4s ease-in-out infinite; }
.wic__pill--on .wic__dot { background: #6ee7b7; box-shadow: 0 0 0 0 rgba(110,231,183,0.6); animation: wic-pulse 1.8s ease-out infinite; }
@keyframes wic-blink { 50% { opacity: 0.3; } }
@keyframes wic-pulse { 70% { box-shadow: 0 0 0 7px rgba(110,231,183,0); } 100% { box-shadow: 0 0 0 0 rgba(110,231,183,0); } }

.wic__steps { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 10px; margin-top: 18px; }
.wic__step {
  display: flex; align-items: center; gap: 13px;
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
  border-radius: 12px; padding: 12px 14px;
}
.wic__num {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.18); font-size: 13px; font-weight: 800; color: #fff;
}
.wic__steptext { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.wic__steptext strong { font-size: 14px; font-weight: 700; }
.wic__steptext span { font-size: 12.5px; color: rgba(234,255,247,0.78); line-height: 1.45; }
.wic__steptext code {
  background: rgba(0,0,0,0.25); padding: 1px 6px; border-radius: 5px;
  font-size: 12px; direction: ltr; display: inline-block;
}
.wic__dl {
  flex-shrink: 0; display: inline-flex; align-items: center; gap: 8px;
  padding: 9px 16px; border: none; border-radius: 10px; cursor: pointer;
  background: #fff; color: #066c57; font-family: inherit; font-size: 13.5px; font-weight: 800;
  box-shadow: 0 4px 12px rgba(0,0,0,0.16); transition: transform 0.15s, box-shadow 0.15s;
}
.wic__dl:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(0,0,0,0.22); }
.wic__dl:active { transform: translateY(0); }
.wic__dl:disabled { opacity: 0.65; cursor: default; }

.wic__hint {
  position: relative; z-index: 1; margin: 14px 0 0; font-size: 12.5px;
  color: #d1fae5; background: rgba(255,255,255,0.1);
  border-radius: 9px; padding: 9px 12px;
}

.wic-enter-active, .wic-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.wic-enter-from, .wic-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
