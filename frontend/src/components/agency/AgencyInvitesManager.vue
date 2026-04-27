<template>
  <div class="card">
    <div class="card-head">
      <h3>הזמנות לסוכנים</h3>
      <button class="btn-new" @click="openForm = !openForm">
        {{ openForm ? 'בטל' : '+ הזמן סוכן' }}
      </button>
    </div>

    <div v-if="openForm" class="invite-form">
      <input
        v-model="newEmail"
        type="email"
        placeholder="email@example.com"
        @keydown.enter.prevent="send"
      />
      <select v-model="newRole">
        <option value="agent">סוכן</option>
        <option value="agency_accountant">חשב עמלות</option>
      </select>
      <button class="btn-send" :disabled="!newEmail || sending" @click="send">
        {{ sending ? 'שולח...' : 'שלח הזמנה' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="!invites.length" class="empty">עדיין לא נשלחו הזמנות.</div>
    <table v-else class="invites-table">
      <thead>
        <tr>
          <th>אימייל</th>
          <th>תפקיד</th>
          <th>סטטוס</th>
          <th>הקישור</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="inv in invites" :key="inv.id">
          <td>{{ inv.email }}</td>
          <td>{{ roleLabel(inv.role) }}</td>
          <td>
            <span class="status" :class="statusOf(inv)">{{ statusLabel(inv) }}</span>
          </td>
          <td>
            <button class="btn-copy" @click="copy(inv.accept_url)" :disabled="!inv.accept_url">
              העתק
            </button>
          </td>
          <td>
            <button v-if="!inv.revoked_at && !inv.accepted_at" class="btn-revoke" @click="revoke(inv)">
              ביטול
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAgencyStore } from '../../stores/agency.js'

const agencyStore = useAgencyStore()
const openForm = ref(false)
const newEmail = ref('')
const newRole = ref('agent')
const sending = ref(false)
const error = ref('')

const invites = ref([])

async function refresh() {
  await agencyStore.fetchInvites()
  invites.value = agencyStore.invites
}

onMounted(refresh)

async function send() {
  error.value = ''
  sending.value = true
  try {
    await agencyStore.createInvite(newEmail.value, newRole.value)
    newEmail.value = ''
    newRole.value = 'agent'
    openForm.value = false
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || 'נכשל בשליחת ההזמנה'
  } finally {
    sending.value = false
  }
}

async function revoke(inv) {
  if (!confirm(`לבטל את ההזמנה ל-${inv.email}?`)) return
  await agencyStore.revokeInvite(inv.id)
  await refresh()
}

async function copy(url) {
  try {
    await navigator.clipboard.writeText(url)
  } catch { /* noop */ }
}

function roleLabel(r) {
  return r === 'agency_accountant' ? 'חשב עמלות' : 'סוכן'
}
function statusOf(inv) {
  if (inv.revoked_at) return 'revoked'
  if (inv.accepted_at) return 'accepted'
  if (new Date(inv.expires_at) < new Date()) return 'expired'
  return 'pending'
}
function statusLabel(inv) {
  const map = { pending: 'ממתין', accepted: 'הצטרף', revoked: 'בוטל', expired: 'פג תוקף' }
  return map[statusOf(inv)] || ''
}
</script>

<style scoped>
.card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 24px;
}
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
h3 { font-size: 16px; font-weight: 700; color: var(--text); }
.btn-new {
  background: var(--primary); color: #fff; border: none; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-new:hover { background: var(--primary-deep); }
.invite-form { display: flex; gap: 8px; margin-bottom: 14px; }
.invite-form input {
  flex: 1; padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit;
}
.invite-form select { padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit; }
.btn-send {
  background: var(--green); color: #fff; border: none; border-radius: 8px;
  padding: 9px 16px; font-weight: 600; cursor: pointer;
}
.btn-send:disabled { opacity: 0.5; }
.error { color: var(--red); font-size: 13px; margin-bottom: 10px; }
.empty { padding: 24px; text-align: center; color: var(--text-muted); }
.invites-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.invites-table th { text-align: right; font-size: 11px; color: var(--text-muted); padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.invites-table td { padding: 10px 6px; border-bottom: 1px solid var(--border-subtle); }
.status { padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 600; }
.status.pending  { background: var(--amber-light); color: var(--amber); }
.status.accepted { background: var(--green-light); color: var(--green-deep); }
.status.revoked  { background: var(--red-light); color: var(--red-deep); }
.status.expired  { background: var(--border-subtle); color: var(--text-muted); }
.btn-copy {
  background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 4px 10px; font-size: 12px; cursor: pointer;
}
.btn-copy:disabled { opacity: 0.4; }
.btn-revoke {
  background: transparent; color: var(--red); border: 1px solid var(--red-light);
  border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer;
}
.btn-revoke:hover { background: var(--red-light); }
</style>
