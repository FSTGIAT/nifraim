<template>
  <div class="agency-uploader">
    <!-- Floating blur circles -->
    <div class="float-circle fc-1"></div>
    <div class="float-circle fc-2"></div>
    <div class="float-circle fc-3"></div>
    <div class="float-circle fc-4"></div>
    <div class="float-circle fc-5"></div>
    <div class="float-circle fc-6"></div>
    <div class="float-circle fc-7"></div>

    <div class="up-card" :class="{ dragover: isDragging }"
         @dragenter.prevent="isDragging = true"
         @dragover.prevent
         @dragleave.prevent="onLeave"
         @drop.prevent="onDrop">
      <div class="up-icon">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <h3 class="up-title">העלאת קבצים לסוכנות</h3>
      <p class="up-sub">
        קבצי עמלות מחברות הביטוח, דוחות היקפים שהתקבלו ב-{{ agencyName }} —
        קבצים שמכילים נתונים על כלל הסוכנים.
      </p>

      <label class="up-button">
        <input type="file" accept=".xlsx,.xls" @change="onPick" multiple :disabled="uploading" />
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <span>{{ uploading ? `מעלה... (${currentIdx + 1}/${total})` : 'בחירת קבצים או גרירה לכאן' }}</span>
      </label>

      <div class="encrypted-row">
        <label class="enc-toggle">
          <input type="checkbox" v-model="encrypted" />
          <span>קובץ מוצפן (סיסמה)</span>
        </label>
        <input
          v-if="encrypted"
          v-model="password"
          type="password"
          class="enc-pass"
          placeholder="סיסמה"
        />
      </div>

      <div v-if="error" class="up-error">{{ error }}</div>
      <div v-if="successMessages.length" class="up-success">
        <div v-for="m in successMessages" :key="m">✓ {{ m }}</div>
      </div>

      <!-- Recent agency uploads -->
      <div v-if="recent.length" class="recent">
        <div class="recent-title">הועלו לאחרונה ע"י החשב</div>
        <ul>
          <li v-for="u in recent" :key="u.id">
            <span class="recent-name">{{ u.filename }}</span>
            <span class="recent-meta">
              <strong>{{ u.record_count?.toLocaleString('he-IL') || 0 }}</strong> רשומות
              · {{ formatDate(u.uploaded_at) }}
            </span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Animated waves at bottom -->
    <div class="wave-bg">
      <div class="shimmer"></div>
      <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="agwg1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#agwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="agwg2" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
            <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
            <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
          </linearGradient>
        </defs>
        <path fill="url(#agwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="agwg3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="50%" stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#agwg3)" d="M0,140L60,143.3C120,147,240,153,360,156.7C480,160,600,160,720,153.3C840,147,960,133,1080,133.3C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useUploadsStore } from '../../stores/uploads.js'

const props = defineProps({ agencyName: { type: String, default: '' } })
const emit = defineEmits(['uploaded'])

const uploadsStore = useUploadsStore()
const isDragging = ref(false)
const uploading = ref(false)
const error = ref('')
const successMessages = ref([])
const password = ref('')
const encrypted = ref(false)
const currentIdx = ref(0)
const total = ref(0)

const recent = computed(() =>
  (uploadsStore.uploads || []).slice(0, 5)
)

onMounted(async () => {
  try { await uploadsStore.fetchUploads() } catch { /* ignore */ }
})

function onLeave(e) {
  if (e.relatedTarget && e.currentTarget.contains(e.relatedTarget)) return
  isDragging.value = false
}

async function onDrop(ev) {
  isDragging.value = false
  const files = Array.from(ev.dataTransfer?.files || [])
  if (files.length) await runUpload(files)
}

async function onPick(ev) {
  const files = Array.from(ev.target.files || [])
  if (files.length) await runUpload(files)
  ev.target.value = ''
}

async function runUpload(files) {
  error.value = ''
  successMessages.value = []
  uploading.value = true
  total.value = files.length
  currentIdx.value = 0
  try {
    for (let i = 0; i < files.length; i++) {
      currentIdx.value = i
      const f = files[i]
      try {
        const res = await uploadsStore.uploadFile(f, encrypted.value ? password.value : null)
        successMessages.value.push(`${f.name} — ${res?.record_count || 0} רשומות`)
      } catch (e) {
        error.value = e.response?.data?.detail || `נכשל בהעלאת ${f.name}`
        break
      }
    }
    emit('uploaded')
  } finally {
    uploading.value = false
    password.value = ''
    encrypted.value = false
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('he-IL', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.agency-uploader {
  position: relative;
  min-height: 360px;
  margin-bottom: 28px;
}

/* ─── Card ─── */
.up-card {
  position: relative;
  z-index: 2;
  background: linear-gradient(180deg, #FFFFFF 0%, #FFFAF3 100%);
  border: 1.5px dashed var(--primary-light);
  border-radius: 24px;
  padding: 36px 36px 28px;
  text-align: center;
  box-shadow: 0 4px 18px rgba(245, 124, 0, 0.06);
  transition: all .25s var(--transition);
}
.up-card.dragover {
  border-color: var(--primary);
  background: linear-gradient(180deg, #FFFFFF 0%, #FFF3E0 100%);
  transform: scale(1.005);
  box-shadow: 0 8px 28px rgba(245, 124, 0, 0.18);
}
.up-icon {
  width: 78px; height: 78px;
  margin: 0 auto 14px;
  background: linear-gradient(135deg, var(--primary) 0%, #FF9800 100%);
  color: #fff;
  border-radius: 22px;
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: 0 12px 28px rgba(245, 124, 0, 0.28);
}
.up-title {
  font-size: 22px; font-weight: 800; color: var(--text);
  margin: 0 0 6px; letter-spacing: -0.4px;
}
.up-sub {
  color: var(--text-muted); font-size: 14px;
  max-width: 540px; margin: 0 auto 18px; line-height: 1.6;
}
.up-button {
  display: inline-flex; align-items: center; gap: 10px;
  background: linear-gradient(135deg, #F57C00 0%, #FF9800 100%);
  color: #fff;
  padding: 14px 28px;
  border-radius: 12px;
  font-size: 15px; font-weight: 700;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(245, 124, 0, 0.32);
  transition: transform .15s var(--transition), box-shadow .15s var(--transition);
}
.up-button:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(245, 124, 0, 0.42); }
.up-button input[type="file"] { display: none; }

.encrypted-row {
  margin-top: 14px;
  display: inline-flex; align-items: center; gap: 12px;
}
.enc-toggle { display: inline-flex; align-items: center; gap: 6px; color: var(--text-muted); font-size: 13px; cursor: pointer; }
.enc-pass { padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit; font-size: 13px; }

.up-error {
  margin-top: 14px;
  padding: 10px 14px;
  background: var(--red-light); color: var(--red-deep);
  border-radius: 8px; font-size: 13.5px;
}
.up-success {
  margin-top: 14px;
  padding: 10px 14px;
  background: var(--green-light); color: var(--green-deep);
  border-radius: 8px; font-size: 13.5px; line-height: 1.6;
  text-align: right;
}

.recent { margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--border-subtle); text-align: right; }
.recent-title { font-size: 12px; color: var(--text-muted); font-weight: 600; margin-bottom: 8px; }
.recent ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.recent li {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 8px 12px; background: var(--bg); border-radius: 8px;
  font-size: 13px;
}
.recent-name { color: var(--text); font-weight: 600; }
.recent-meta { color: var(--text-muted); font-size: 12px; }
.recent-meta strong { color: var(--primary-deep); margin-left: 2px; }

/* ─── Floating blur circles ─── */
.float-circle { position: absolute; border-radius: 50%; pointer-events: none; z-index: 0; filter: blur(40px); }
.fc-1 { width: 220px; height: 220px; top: -60px; left: -40px; background: rgba(245, 124, 0, 0.10); animation: floatBob 14s ease-in-out infinite; }
.fc-2 { width: 160px; height: 160px; bottom: -30px; right: -20px; background: rgba(255, 152, 0, 0.12); animation: floatBob 12s ease-in-out infinite reverse; }
.fc-3 { width: 110px; height: 110px; top: 40%; left: 10%; background: rgba(255, 183, 77, 0.10); animation: floatBob 17s ease-in-out infinite; }
.fc-4 { width: 90px; height: 90px; top: 25%; right: 25%; background: rgba(245, 124, 0, 0.08); animation: floatBob 9s ease-in-out infinite reverse; }
.fc-5 { width: 70px; height: 70px; bottom: 25%; left: 30%; background: rgba(255, 152, 0, 0.10); animation: floatBob 11s ease-in-out infinite; }
.fc-6 { width: 130px; height: 130px; top: 60%; right: 5%; background: rgba(255, 183, 77, 0.08); animation: floatBob 15s ease-in-out infinite reverse; }
.fc-7 { width: 50px; height: 50px; top: 18%; left: 50%; background: rgba(245, 124, 0, 0.12); animation: floatBob 8s ease-in-out infinite; }

@keyframes floatBob {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(15px, -20px) scale(1.05); }
}

/* ─── Waves ─── */
.wave-bg {
  position: absolute; bottom: -8px; left: 0; right: 0; height: 200px;
  pointer-events: none; z-index: 1; overflow: hidden; border-radius: 0 0 24px 24px;
}
.wave { position: absolute; bottom: 0; left: 0; width: 100%; height: 100%; }
.wave-1 { animation: waveSlide 18s linear infinite; }
.wave-2 { animation: waveSlide 22s linear infinite reverse; }
.wave-3 { animation: waveSlide 26s linear infinite; }

@keyframes waveSlide {
  0% { transform: translateX(0); }
  100% { transform: translateX(-100px); }
}
.shimmer {
  position: absolute; bottom: 0; left: -100%; width: 200%; height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 224, 178, 0.18) 50%, transparent 100%);
  animation: shimmerSweep 8s linear infinite;
}
@keyframes shimmerSweep {
  0% { transform: translateX(-50%); }
  100% { transform: translateX(50%); }
}
</style>
