<template>
  <header class="workspace-header">
    <div class="header-content">
      <div class="brand">
        <div class="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span class="brand-name">Nifraim</span>
      </div>
      <!-- Global Search -->
      <div class="header-search" :class="{ open: searchOpen }">
        <button class="search-btn" @click="toggleSearch" title="חיפוש לקוח">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </button>
        <input
          v-if="searchOpen"
          ref="searchRef"
          type="text"
          v-model="comparisonStore.searchQuery"
          placeholder="חיפוש לפי שם או ת.ז..."
          class="header-search-input"
          @keydown.escape="closeSearch"
        />
      </div>

      <div class="header-actions">
        <div class="user-pill" v-if="auth.user">
          <div class="user-avatar">{{ avatarLetter }}</div>
          <span class="user-name">{{ auth.user.full_name || auth.user.email }}</span>
        </div>
        <!-- Settings gear -->
        <div class="settings-wrapper" ref="settingsRef">
          <button class="btn-settings" data-tour="settings-gear" @click="settingsOpen = !settingsOpen" title="הגדרות">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
          </button>
          <Transition name="pop">
            <div v-if="settingsOpen" class="settings-popover">
              <label class="settings-label">ספק דוא"ל</label>
              <select class="settings-select" :value="emailProvider" @change="onProviderChange">
                <option value="mailto">ברירת מחדל</option>
                <option value="gmail">Gmail</option>
                <option value="outlook">Outlook</option>
              </select>

              <!-- Subscription info -->
              <div v-if="subStore.status" class="settings-sub-section">
                <label class="settings-label">מנוי</label>
                <div class="sub-info">
                  <span class="sub-plan">{{ subStore.status.plan === 'monthly' ? 'חודשי' : 'שנתי' }}</span>
                  <span class="sub-status" :class="subStore.status.status">{{ subStatusLabel }}</span>
                </div>
                <div v-if="subStore.status.last4_digits" class="sub-card-info">
                  כרטיס: <span class="ltr-number">****{{ subStore.status.last4_digits }}</span>
                </div>
                <div v-if="subStore.status.next_charge_at" class="sub-next-charge">
                  חיוב הבא: <span class="ltr-number">{{ formatDate(subStore.status.next_charge_at) }}</span>
                </div>
                <button
                  v-if="subStore.status.is_recurring"
                  class="btn-cancel-sub"
                  @click="showCancelConfirm = true"
                >
                  ביטול הוראת קבע
                </button>
              </div>
            </div>
          </Transition>

          <!-- Cancel subscription confirmation -->
          <Teleport to="body">
            <Transition name="modal">
              <div v-if="showCancelConfirm" class="modal-overlay" @click.self="showCancelConfirm = false">
                <div class="modal-card">
                  <h3>ביטול הוראת קבע</h3>
                  <p>האם לבטל את החידוש האוטומטי?</p>
                  <p class="modal-note">הגישה למערכת תישמר עד תום תקופת המנוי הנוכחית.</p>
                  <div class="modal-actions">
                    <button class="modal-btn cancel" @click="showCancelConfirm = false">חזרה</button>
                    <button class="modal-btn confirm" @click="handleCancelSub" :disabled="cancelLoading">
                      <span v-if="cancelLoading" class="spinner-sm"></span>
                      <span v-else>אישור ביטול</span>
                    </button>
                  </div>
                </div>
              </div>
            </Transition>
          </Teleport>
        </div>
        <button class="btn-logout" @click="$emit('logout')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { useComparisonStore } from '../../stores/comparison.js'
import { useSubscriptionStore } from '../../stores/subscription.js'

const auth = useAuthStore()
const comparisonStore = useComparisonStore()
const subStore = useSubscriptionStore()
defineEmits(['logout'])

const searchOpen = ref(false)
const searchRef = ref(null)

const avatarLetter = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || ''
  return name.charAt(0).toUpperCase()
})

async function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) {
    await nextTick()
    searchRef.value?.focus()
  } else {
    comparisonStore.searchQuery = ''
  }
}

function closeSearch() {
  searchOpen.value = false
  comparisonStore.searchQuery = ''
}

// ─── Email provider settings ───
const settingsOpen = ref(false)
const settingsRef = ref(null)
const emailProvider = ref(localStorage.getItem('emailProvider') || 'mailto')

function onProviderChange(e) {
  emailProvider.value = e.target.value
  localStorage.setItem('emailProvider', e.target.value)
}

function onClickOutside(e) {
  if (settingsOpen.value && settingsRef.value && !settingsRef.value.contains(e.target)) {
    settingsOpen.value = false
  }
}

// ─── Subscription ───
const showCancelConfirm = ref(false)
const cancelLoading = ref(false)

const subStatusLabel = computed(() => {
  const s = subStore.status?.status
  if (s === 'active') return 'פעיל'
  if (s === 'cancelled') return 'מבוטל'
  if (s === 'expired') return 'פג תוקף'
  return s || ''
})

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('he-IL')
}

async function handleCancelSub() {
  cancelLoading.value = true
  try {
    await subStore.cancelSubscription()
    showCancelConfirm.value = false
    settingsOpen.value = false
  } catch {
    // error handled in store
  } finally {
    cancelLoading.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  subStore.fetchStatus()
})
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.workspace-header {
  background: #FFFFFF;
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 6px;
  background: var(--bg-surface);
  border-radius: 100px;
  border: 1px solid var(--border-subtle);
}

.user-avatar {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-violet) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: white;
}

.user-name {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Settings gear ── */
.settings-wrapper {
  position: relative;
}

.btn-settings {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all 0.25s var(--transition);
}

.btn-settings:hover {
  background: var(--bg-surface);
  color: var(--primary);
}

.settings-popover {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 12px 14px;
  z-index: 200;
  min-width: 180px;
}

.settings-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.settings-select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}

.settings-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

/* Popover transition */
.pop-enter-active { animation: popIn 0.15s ease-out; }
.pop-leave-active { animation: popIn 0.1s ease reverse; }
@keyframes popIn {
  from { opacity: 0; transform: translateY(-4px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.btn-logout {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all 0.25s var(--transition);
}

.btn-logout:hover {
  background: var(--red-light);
  color: var(--red);
}

/* Header search */
.header-search {
  display: flex;
  align-items: center;
  margin-right: auto;
  margin-left: 16px;
  border-radius: 8px;
  transition: all 0.25s ease;
}

.header-search.open {
  background: var(--bg);
  border: 1px solid var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

.search-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.header-search.open .search-btn {
  border: none;
  background: transparent;
  color: var(--primary);
}

.search-btn:hover {
  color: var(--primary);
  border-color: var(--primary);
}

.header-search-input {
  width: 220px;
  padding: 8px 12px 8px 0;
  border: none;
  font-size: 14px;
  font-family: inherit;
  background: transparent;
  color: var(--text);
  outline: none;
}

.header-search-input::placeholder {
  color: var(--text-muted);
}

/* ── Subscription section in settings ── */
.settings-sub-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.sub-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.sub-plan {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.sub-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 100px;
}

.sub-status.active {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.sub-status.cancelled {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.sub-status.expired {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.sub-card-info,
.sub-next-charge {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.btn-cancel-sub {
  width: 100%;
  margin-top: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--red);
  background: var(--red-light);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}

.btn-cancel-sub:hover {
  background: rgba(239, 68, 68, 0.12);
  border-color: var(--red);
}

/* ── Cancel confirmation modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5000;
}

.modal-card {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 32px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.15);
  text-align: center;
}

.modal-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
}

.modal-card p {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.modal-note {
  font-size: 13px !important;
  color: var(--text-muted) !important;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 24px;
}

.modal-btn {
  flex: 1;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}

.modal-btn.cancel {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.modal-btn.cancel:hover {
  border-color: var(--text-muted);
}

.modal-btn.confirm {
  background: var(--red);
  border: none;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-btn.confirm:hover:not(:disabled) {
  opacity: 0.9;
}

.modal-btn.confirm:disabled {
  opacity: 0.6;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.modal-enter-active { animation: modalIn 0.2s ease-out; }
.modal-leave-active { animation: modalIn 0.15s reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
