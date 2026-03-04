<template>
  <div class="commission-uploader">
    <!-- Loading state -->
    <div v-if="comparisonStore.uploading" class="upload-loading">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span class="loading-text">משווה מול פרודוקציה...</span>
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
import { ref, inject, watch } from 'vue'
import { useComparisonStore } from '../../stores/comparison.js'

const comparisonStore = useComparisonStore()

const fileInputRef = ref(null)
const needPassword = ref(false)
const password = ref('')
const error = ref('')

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
  try {
    await comparisonStore.compareWithProduction(
      files,
      needPassword.value ? password.value : null,
    )
    password.value = ''
    needPassword.value = false
  } catch (e) {
    error.value = comparisonStore.error || 'שגיאה בהעלאה'
  }
}
</script>

<style scoped>
.commission-uploader {
  max-width: 560px;
  margin: 0 auto;
}

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 16px 24px;
  border: 1.5px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--card-bg);
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn svg {
  color: var(--accent-emerald);
  flex-shrink: 0;
}

.upload-btn:hover {
  border-color: var(--accent-emerald);
  background: var(--green-light);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(46, 132, 74, 0.1);
}

.upload-btn:active {
  transform: translateY(0);
}

/* Loading */
.upload-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 16px 24px;
  background: var(--card-bg);
  border: 1.5px solid var(--green-light);
  border-radius: var(--radius-md);
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
