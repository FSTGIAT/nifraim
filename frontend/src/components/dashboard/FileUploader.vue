<template>
  <div class="uploader-card">
    <!-- Mode Toggle -->
    <div class="mode-toggle">
      <button
        class="toggle-btn"
        :class="{ active: mode === 'single' }"
        @click="mode = 'single'"
      >העלאה רגילה</button>
      <button
        class="toggle-btn"
        :class="{ active: mode === 'compare' }"
        @click="mode = 'compare'"
      >השוואת קבצים</button>
    </div>

    <!-- Single Upload Mode -->
    <template v-if="mode === 'single'">
      <div
        class="drop-zone"
        :class="{ dragging: isDragging, uploading: uploadsStore.uploading }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
        @click="$refs.fileInput.click()"
      >
        <div v-if="uploadsStore.uploading" class="upload-progress">
          <div class="spinner"></div>
          <span>מעלה ומעבד...</span>
        </div>
        <div v-else>
          <div class="upload-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <p>גרור קובץ Excel לכאן</p>
          <p class="hint">או לחץ לבחירה (.xlsx / .xls)</p>
        </div>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".xlsx,.xls"
        @change="handleFileSelect"
        style="display: none"
      />
      <div class="password-field" v-if="needPassword">
        <label>סיסמת קובץ מוצפן</label>
        <input type="password" v-model="password" placeholder="הזן סיסמה..." dir="ltr" />
      </div>
      <label class="checkbox">
        <input type="checkbox" v-model="needPassword" />
        <span>קובץ מוגן בסיסמה</span>
      </label>
    </template>

    <!-- Compare Mode -->
    <template v-if="mode === 'compare'">
      <!-- Production File -->
      <div class="zone-label production-label">קובץ פרודוקציה</div>
      <div
        class="drop-zone production-zone"
        :class="{ dragging: prodDragging, selected: prodFile }"
        @dragover.prevent="prodDragging = true"
        @dragleave="prodDragging = false"
        @drop.prevent="handleProdDrop"
        @click="$refs.prodInput.click()"
      >
        <div v-if="prodFile" class="file-selected">
          <svg class="file-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span class="file-name">{{ prodFile.name }}</span>
          <button class="file-remove" @click.stop="prodFile = null">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div v-else>
          <div class="upload-icon small-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <p>גרור או בחר קובץ</p>
        </div>
      </div>
      <input
        ref="prodInput"
        type="file"
        accept=".xlsx,.xls"
        @change="e => { prodFile = e.target.files[0]; e.target.value = '' }"
        style="display: none"
      />

      <!-- Commission File -->
      <div class="zone-label commission-label">דוח נפרעים</div>
      <div
        class="drop-zone commission-zone"
        :class="{ dragging: commDragging, selected: commFile }"
        @dragover.prevent="commDragging = true"
        @dragleave="commDragging = false"
        @drop.prevent="handleCommDrop"
        @click="$refs.commInput.click()"
      >
        <div v-if="commFile" class="file-selected">
          <svg class="file-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span class="file-name">{{ commFile.name }}</span>
          <button class="file-remove" @click.stop="commFile = null">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div v-else>
          <div class="upload-icon small-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
            </svg>
          </div>
          <p>גרור או בחר קובץ</p>
        </div>
      </div>
      <input
        ref="commInput"
        type="file"
        accept=".xlsx,.xls"
        @change="e => { commFile = e.target.files[0]; e.target.value = '' }"
        style="display: none"
      />

      <!-- Password Options -->
      <label class="checkbox">
        <input type="checkbox" v-model="compareNeedPassword" />
        <span>קובץ מוגן בסיסמה</span>
      </label>
      <div class="password-field" v-if="compareNeedPassword">
        <label>סיסמה לפרודוקציה</label>
        <input type="password" v-model="prodPassword" placeholder="סיסמה..." dir="ltr" />
        <label style="margin-top: 8px;">סיסמה לנפרעים</label>
        <input type="password" v-model="commPassword" placeholder="סיסמה..." dir="ltr" />
      </div>

      <!-- Compare Button -->
      <button
        class="btn-compare"
        :disabled="!canCompare || comparisonStore.uploading"
        @click="startComparison"
      >
        <template v-if="comparisonStore.uploading">
          <div class="spinner small"></div>
          <span>מעבד...</span>
        </template>
        <template v-else>
          התחל השוואה
        </template>
      </button>
    </template>

    <Transition name="fade">
      <p class="error" v-if="error">{{ error }}</p>
    </Transition>
    <Transition name="fade">
      <p class="success" v-if="successMsg">{{ successMsg }}</p>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUploadsStore } from '../../stores/uploads.js'
import { useComparisonStore } from '../../stores/comparison.js'

const emit = defineEmits(['uploaded', 'compared'])
const uploadsStore = useUploadsStore()
const comparisonStore = useComparisonStore()

// Mode
const mode = ref('single')

// Single upload state
const isDragging = ref(false)
const needPassword = ref(false)
const password = ref('')
const error = ref('')
const successMsg = ref('')

// Compare mode state
const prodFile = ref(null)
const commFile = ref(null)
const prodDragging = ref(false)
const commDragging = ref(false)
const compareNeedPassword = ref(false)
const prodPassword = ref('')
const commPassword = ref('')

const canCompare = computed(() => prodFile.value && commFile.value)

// Single upload handlers
async function uploadFile(file) {
  error.value = ''
  successMsg.value = ''
  try {
    const result = await uploadsStore.uploadFile(file, needPassword.value ? password.value : null)
    successMsg.value = `הועלו ${result.record_count} רשומות מ-${result.filename}`
    password.value = ''
    emit('uploaded')
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בהעלאת הקובץ'
  }
}

function handleDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) uploadFile(file)
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) uploadFile(file)
  e.target.value = ''
}

// Compare mode handlers
function handleProdDrop(e) {
  prodDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) prodFile.value = file
}

function handleCommDrop(e) {
  commDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) commFile.value = file
}

async function startComparison() {
  error.value = ''
  successMsg.value = ''
  try {
    await comparisonStore.uploadAndCompare(
      prodFile.value,
      commFile.value,
      compareNeedPassword.value ? prodPassword.value : null,
      compareNeedPassword.value ? commPassword.value : null,
    )
    successMsg.value = 'ההשוואה הושלמה בהצלחה'
    emit('compared')
    await uploadsStore.fetchUploads()
  } catch (e) {
    error.value = comparisonStore.error || 'שגיאה בהשוואה'
  }
}
</script>

<style scoped>
.uploader-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
}

/* Mode Toggle */
.mode-toggle {
  display: flex;
  gap: 4px;
  background: var(--bg-surface);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 3px;
  margin-bottom: 16px;
}

.toggle-btn {
  flex: 1;
  padding: 7px 8px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.25s;
}

.toggle-btn.active {
  background: var(--card-bg);
  color: var(--text);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  font-weight: 600;
}

/* Drop Zones */
.drop-zone {
  border: 2px dashed var(--border-subtle);
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--primary);
  background: var(--primary-light);
}

.drop-zone.uploading {
  pointer-events: none;
  opacity: 0.7;
}

.drop-zone.selected {
  border-style: solid;
  background: var(--green-light);
  border-color: var(--green-light);
}

.production-zone:hover,
.production-zone.dragging {
  border-color: var(--primary);
  background: var(--primary-light);
}

.production-zone.selected {
  border-color: var(--primary-light);
  background: var(--primary-light);
}

.commission-zone:hover,
.commission-zone.dragging {
  border-color: var(--green);
  background: var(--green-light);
}

.commission-zone.selected {
  border-color: var(--green-light);
  background: var(--green-light);
}

.upload-icon {
  margin: 0 auto 8px;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.small-icon {
  width: 36px;
  height: 36px;
  margin-bottom: 4px;
}

.drop-zone p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.hint {
  font-size: 12px !important;
  color: var(--text-muted) !important;
}

/* Zone Labels */
.zone-label {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  margin-top: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.production-label {
  color: var(--primary);
}

.commission-label {
  color: var(--green);
}

/* File Selected State */
.file-selected {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.file-check {
  color: var(--green);
}

.file-name {
  font-size: 12px;
  color: var(--text);
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.file-remove:hover {
  background: var(--red-light);
  color: var(--red);
}

/* Compare Button */
.btn-compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px;
  margin-top: 12px;
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s;
  position: relative;
  overflow: hidden;
}

.btn-compare::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.08) 50%, transparent 60%);
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.btn-compare:hover:not(:disabled) {
  box-shadow: 0 4px 16px var(--primary-light);
  transform: translateY(-1px);
}

.btn-compare:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Password & Misc */
.password-field {
  margin-top: 12px;
}

.password-field label {
  display: block;
  font-size: 13px;
  margin-bottom: 4px;
  color: var(--text-muted);
}

.password-field input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-surface);
  color: var(--text);
}

.password-field input:focus {
  outline: none;
  border-color: var(--primary);
}

.checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.2);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.small {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-progress span {
  font-size: 14px;
  color: var(--text-secondary);
}

.upload-progress .spinner {
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
}

.error {
  color: var(--red);
  font-size: 13px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}

.success {
  color: var(--green);
  font-size: 13px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--green-light);
  border-radius: 8px;
  border: 1px solid var(--green-light);
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
