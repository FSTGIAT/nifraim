<template>
  <div class="commission-uploader">
    <!-- Floating blur circles -->
    <div class="float-circle fc-1"></div>
    <div class="float-circle fc-2"></div>
    <div class="float-circle fc-3"></div>
    <div class="float-circle fc-4"></div>

    <!-- Animated waves at bottom -->
    <div class="wave-bg">
      <div class="shimmer"></div>
      <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="cwg1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#cwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="cwg2" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
            <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
            <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
          </linearGradient>
        </defs>
        <path fill="url(#cwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="cwg3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
          </linearGradient>
        </defs>
        <path fill="url(#cwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
      </svg>
    </div>

    <!-- Loading state -->
    <div v-if="comparisonStore.uploading" class="upload-loading">
      <div class="loading-content">
        <div class="loader">
          <div class="loader-ring"></div>
          <div class="loader-ring delay"></div>
        </div>
        <div class="loading-info">
          <span class="loading-text">{{ compStageLabel }}</span>
          <span class="loading-hint">{{ compStageHint }}</span>
        </div>
      </div>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" :style="{ width: compProgressWidth }"></div>
      </div>
      <span class="loading-wait-hint">קבצים גדולים עשויים לקחת עד דקה</span>
    </div>

    <!-- Upload button -->
    <button v-else class="upload-btn" @click="openFilePicker">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <span>העלה קבצי נפרעים להשוואה</span>
    </button>
    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls"
      multiple
      @change="onFileSelected"
      style="display: none"
    />

    <!-- Encrypted file option -->
    <div class="options-row">
      <label class="toggle-label">
        <div class="toggle" :class="{ on: needPassword }">
          <input type="checkbox" v-model="needPassword" />
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
        </div>
        <span>קובץ מוצפן</span>
      </label>
    </div>

    <Transition name="slide-down">
      <div class="password-field" v-if="needPassword">
        <input type="password" v-model="password" placeholder="סיסמת הקובץ..." dir="ltr" />
      </div>
    </Transition>

    <Transition name="fade">
      <p class="error-msg" v-if="error">{{ error }}</p>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, inject, watch } from 'vue'
import { useComparisonStore } from '../../stores/comparison.js'

const comparisonStore = useComparisonStore()

const fileInputRef = ref(null)
const needPassword = ref(false)
const password = ref('')
const error = ref('')
const compStage = ref(0) // 0=idle, 1=uploading, 2=comparing

const compStageLabel = computed(() => {
  if (compStage.value === 1) return 'מעלה קבצי נפרעים...'
  if (compStage.value === 2) return 'משווה מול פרודוקציה...'
  return 'מעבד...'
})

const compStageHint = computed(() => {
  if (compStage.value === 1) return 'מעביר קבצים לשרת'
  if (compStage.value === 2) return 'מתאים לקוחות ומוצרים'
  return ''
})

const compProgressWidth = computed(() => {
  if (compStage.value === 1) return '40%'
  if (compStage.value === 2) return '75%'
  return '0%'
})

// Receive files from full-page drop overlay
const droppedFiles = inject('droppedFiles', null)
if (droppedFiles) {
  watch(droppedFiles, (val) => {
    if (val && val.length > 0) {
      uploadFiles(Array.from(val))
    }
  })
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function onFileSelected(e) {
  const selected = e.target.files
  if (selected && selected.length > 0) {
    const files = Array.from(selected).filter(f => {
      const ext = f.name.split('.').pop().toLowerCase()
      return ext === 'xlsx' || ext === 'xls'
    })
    if (files.length > 0) {
      uploadFiles(files)
    }
  }
  e.target.value = ''
}

async function uploadFiles(files) {
  error.value = ''
  compStage.value = 1
  try {
    // Switch to comparing stage after a short delay (upload is fast, parsing is slow)
    setTimeout(() => {
      if (comparisonStore.uploading) compStage.value = 2
    }, 1500)
    await comparisonStore.compareWithProduction(
      files,
      needPassword.value ? password.value : null,
    )
    password.value = ''
    needPassword.value = false
  } catch (e) {
    error.value = comparisonStore.error || 'שגיאה בהעלאה'
  } finally {
    compStage.value = 0
  }
}
</script>

<style scoped>
.commission-uploader {
  max-width: 560px;
  margin: 0 auto;
  position: relative;
}

/* Floating blur circles */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.fc-1 {
  width: 220px;
  height: 220px;
  top: 10%;
  right: -60px;
  background: rgba(245, 124, 0, 0.045);
  border: 1px solid rgba(245, 124, 0, 0.06);
  animation: floatBob 8s ease-in-out infinite;
}

.fc-2 {
  width: 160px;
  height: 160px;
  bottom: 25%;
  left: -40px;
  background: rgba(245, 124, 0, 0.035);
  border: 1px solid rgba(245, 124, 0, 0.05);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}

.fc-3 {
  width: 90px;
  height: 90px;
  top: 30%;
  left: 8%;
  background: rgba(245, 124, 0, 0.05);
  animation: floatBob 10s ease-in-out infinite 2s;
}

.fc-4 {
  width: 120px;
  height: 120px;
  top: 55%;
  right: 6%;
  background: rgba(245, 124, 0, 0.03);
  border: 1px solid rgba(245, 124, 0, 0.04);
  animation: floatBob 9s ease-in-out infinite 1s;
}

@keyframes floatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* Waves fixed to bottom of page */
.wave-bg {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.shimmer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
}

.shimmer::after {
  content: '';
  position: absolute;
  top: 0;
  left: -80%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 200, 100, 0.1) 35%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 200, 100, 0.1) 65%,
    transparent 100%
  );
  animation: shimmerSweep 7s ease-in-out infinite;
}

@keyframes shimmerSweep {
  0%   { left: -80%; }
  100% { left: 180%; }
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 100%;
}

.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }

@keyframes waveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 16px 24px;
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn svg {
  color: #fff;
  flex-shrink: 0;
}

.upload-btn:hover {
  background: linear-gradient(135deg, #E65100, #F57C00);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.25);
}

.upload-btn:active {
  transform: translateY(0);
}

/* Loading */
.upload-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  background: var(--card-bg);
  border: 1.5px solid var(--green-light);
  border-radius: var(--radius-md);
}

.loading-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.loading-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.loader {
  width: 28px;
  height: 28px;
  position: relative;
  flex-shrink: 0;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--accent-emerald);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 4px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.loading-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.loading-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.progress-bar-track {
  width: 100%;
  height: 4px;
  background: var(--border-subtle);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan, var(--accent-emerald)));
  border-radius: 2px;
  transition: width 1s ease;
}

.loading-wait-hint {
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.7;
  animation: fadeInUp 0.5s ease;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 0.7; transform: translateY(0); }
}

/* Toggle */
.options-row {
  margin-top: 12px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
}

.toggle { position: relative; }
.toggle input { position: absolute; opacity: 0; pointer-events: none; }

.toggle-track {
  width: 36px;
  height: 20px;
  background: var(--border-subtle);
  border-radius: 10px;
  transition: all 0.3s var(--transition);
  position: relative;
}

.toggle.on .toggle-track { background: var(--green-light); }

.toggle-thumb {
  width: 16px;
  height: 16px;
  background: var(--text-secondary);
  border-radius: 50%;
  position: absolute;
  top: 2px;
  right: 2px;
  transition: all 0.3s var(--transition);
}

.toggle.on .toggle-thumb {
  right: 18px;
  background: var(--accent-emerald);
  box-shadow: 0 0 8px var(--green-light);
}

.password-field { margin-top: 12px; }

.password-field input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s var(--transition);
}

.password-field input:focus {
  border-color: var(--accent-emerald);
  box-shadow: 0 0 0 3px var(--green-light);
}

.slide-down-enter-active { animation: slideDown 0.3s var(--transition); }
.slide-down-leave-active { animation: slideDown 0.2s var(--transition) reverse; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

.error-msg {
  color: var(--red);
  font-size: 13px;
  margin-top: 12px;
  text-align: center;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}
</style>
