<template>
  <!-- Embedded mode: inline card (no modal overlay) -->
  <div v-if="embedded && show" class="embedded-portal">
    <div class="embedded-header">
      <div class="header-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
        </svg>
        <span>פורטל לקוחות</span>
        <span class="link-count" v-if="activeLinks.length">{{ activeLinks.length }} פעילים</span>
      </div>
    </div>
    <div class="embedded-body">
      <button class="btn-generate" @click="showGenerateModal = true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        צור קישור חדש
      </button>
      <div v-if="portalStore.loading && !portalStore.links.length" class="loading-state">
        <div class="mini-spinner"></div>
        <span>טוען קישורים...</span>
      </div>
      <div v-else-if="portalStore.links.length" class="links-list">
        <div
          v-for="link in portalStore.links"
          :key="link.id"
          class="link-row"
          :class="{ revoked: !link.is_active, expired: isExpired(link) }"
        >
          <div class="link-info">
            <span class="link-name">{{ link.customer_name }}</span>
            <span class="link-id ltr-number">{{ link.customer_id_number }}</span>
          </div>
          <div class="link-meta">
            <span class="link-status" :class="linkStatusClass(link)">
              {{ linkStatusLabel(link) }}
            </span>
            <span class="link-date">{{ formatDate(link.created_at) }}</span>
            <span v-if="link.last_accessed_at" class="link-accessed">
              נצפה: {{ formatDate(link.last_accessed_at) }}
            </span>
          </div>
          <div class="link-actions" v-if="link.is_active && !isExpired(link)">
            <button class="action-btn" @click="copyUrl(link)" :title="copiedToken === link.token ? 'הועתק!' : 'העתק קישור'">
              <svg v-if="copiedToken !== link.token" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
              </svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
            <button
              v-if="link.customer_email"
              class="action-btn email"
              @click="sendEmail(link)"
              title="שלח באימייל"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
            </button>
            <button class="action-btn revoke" @click="revokeLink(link)" title="בטל קישור">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
        </svg>
        <p>אין קישורים פעילים</p>
        <span>צור קישור חדש כדי לשתף תיק ביטוח עם לקוח</span>
      </div>
    </div>

    <PortalGenerateModal
      :show="showGenerateModal"
      @close="showGenerateModal = false"
      @generated="onGenerated"
    />
  </div>

  <!-- Modal mode (original) -->
  <template v-else>
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
          <div class="modal-card">
            <div class="modal-header">
              <div class="header-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
                  <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
                </svg>
                <span>קישורים ללקוחות</span>
                <span class="link-count" v-if="activeLinks.length">{{ activeLinks.length }}</span>
              </div>
              <button class="close-btn" @click="$emit('close')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <button class="btn-generate" @click="showGenerateModal = true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                צור קישור חדש
              </button>
              <div v-if="portalStore.loading && !portalStore.links.length" class="loading-state">
                <div class="mini-spinner"></div>
                <span>טוען קישורים...</span>
              </div>
              <div v-else-if="portalStore.links.length" class="links-list">
                <div
                  v-for="link in portalStore.links"
                  :key="link.id"
                  class="link-row"
                  :class="{ revoked: !link.is_active, expired: isExpired(link) }"
                >
                  <div class="link-info">
                    <span class="link-name">{{ link.customer_name }}</span>
                    <span class="link-id ltr-number">{{ link.customer_id_number }}</span>
                  </div>
                  <div class="link-meta">
                    <span class="link-status" :class="linkStatusClass(link)">
                      {{ linkStatusLabel(link) }}
                    </span>
                    <span class="link-date">{{ formatDate(link.created_at) }}</span>
                    <span v-if="link.last_accessed_at" class="link-accessed">
                      נצפה: {{ formatDate(link.last_accessed_at) }}
                    </span>
                  </div>
                  <div class="link-actions" v-if="link.is_active && !isExpired(link)">
                    <button class="action-btn" @click="copyUrl(link)" :title="copiedToken === link.token ? 'הועתק!' : 'העתק קישור'">
                      <svg v-if="copiedToken !== link.token" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                        <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                      </svg>
                      <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </button>
                    <button
                      v-if="link.customer_email"
                      class="action-btn email"
                      @click="sendEmail(link)"
                      title="שלח באימייל"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                        <polyline points="22,6 12,13 2,6"/>
                      </svg>
                    </button>
                    <button class="action-btn revoke" @click="revokeLink(link)" title="בטל קישור">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
                  <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
                </svg>
                <p>אין קישורים פעילים</p>
                <span>צור קישור חדש כדי לשתף תיק ביטוח עם לקוח</span>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <PortalGenerateModal
      :show="showGenerateModal"
      @close="showGenerateModal = false"
      @generated="onGenerated"
    />
  </template>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePortalStore } from '../../stores/portal.js'
import PortalGenerateModal from './PortalGenerateModal.vue'

defineProps({
  show: Boolean,
  embedded: { type: Boolean, default: false },
})

defineEmits(['close'])

const portalStore = usePortalStore()

const showGenerateModal = ref(false)
const copiedToken = ref(null)

const activeLinks = computed(() =>
  portalStore.links.filter(l => l.is_active && !isExpired(l))
)

onMounted(() => {
  portalStore.fetchLinks()
})

function isExpired(link) {
  return new Date(link.expires_at) < new Date()
}

function linkStatusClass(link) {
  if (!link.is_active) return 'revoked'
  if (isExpired(link)) return 'expired'
  return 'active'
}

function linkStatusLabel(link) {
  if (!link.is_active) return 'בוטל'
  if (isExpired(link)) return 'פג תוקף'
  return 'פעיל'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL', { day: 'numeric', month: 'short' })
}

async function copyUrl(link) {
  const url = `${window.location.origin}/portal/${link.token}`
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    const input = document.createElement('input')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
  }
  copiedToken.value = link.token
  setTimeout(() => { copiedToken.value = null }, 2000)
}

async function sendEmail(link) {
  try {
    await portalStore.sendEmail(link.token)
  } catch {
    // error in store
  }
}

async function revokeLink(link) {
  try {
    await portalStore.revokeLink(link.token)
  } catch {
    // error in store
  }
}

function onGenerated() {
  // Link already added to store by generateLink
}
</script>

<style scoped>
/* Embedded mode */
.embedded-portal {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.embedded-header {
  display: flex;
  align-items: center;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.embedded-body {
  padding: 20px 24px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.header-title svg { color: var(--primary); }

.link-count {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
  background: var(--primary-light);
  color: var(--primary);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: var(--bg);
  color: var(--text);
}

/* Body */
.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
}

.btn-generate {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  transition: all 0.2s var(--transition);
  margin-bottom: 16px;
}

.btn-generate:hover {
  background: var(--primary-deep);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.2);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.mini-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Links list */
.links-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.link-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  transition: all 0.2s var(--transition);
}

.link-row:hover { border-color: var(--border); }

.link-row.revoked, .link-row.expired { opacity: 0.5; }

.link-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 110px;
}

.link-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.link-id {
  font-size: 11px;
  color: var(--text-muted);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

.link-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  flex-wrap: wrap;
}

.link-status {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 8px;
}

.link-status.active { background: var(--green-light); color: var(--green); }
.link-status.revoked { background: var(--red-light); color: var(--red); }
.link-status.expired { background: var(--amber-light); color: var(--amber); }

.link-date, .link-accessed {
  font-size: 11px;
  color: var(--text-muted);
}

.link-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s var(--transition);
}

.action-btn:hover { background: var(--border-subtle); color: var(--text-secondary); }
.action-btn.email:hover { background: var(--green-light); color: var(--green); }
.action-btn.revoke:hover { background: var(--red-light); color: var(--red); }

/* Empty state */
.empty-state {
  text-align: center;
  padding: 32px 0 16px;
}

.empty-state svg {
  color: var(--text-muted);
  opacity: 0.25;
  margin-bottom: 12px;
}

.empty-state p {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 4px;
}

.empty-state span {
  font-size: 12px;
  color: var(--text-muted);
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s var(--transition);
}

.modal-enter-active .modal-card,
.modal-leave-active .modal-card {
  transition: transform 0.25s var(--transition);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-card {
  transform: translateY(20px) scale(0.97);
}

.modal-leave-to .modal-card {
  transform: translateY(10px) scale(0.98);
}

@media (max-width: 640px) {
  .link-row {
    flex-wrap: wrap;
  }
  .link-meta {
    order: 3;
    width: 100%;
  }
}
</style>
