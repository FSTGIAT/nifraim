<template>
  <div class="admin-page">
    <header class="admin-header">
      <div class="admin-header-content">
        <div class="admin-brand">
          <router-link to="/workspace" class="brand-link">
            <div class="brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span>Nifraim</span>
          </router-link>
          <span class="admin-badge">Admin</span>
        </div>
        <router-link to="/workspace" class="btn-back-workspace">חזרה למערכת</router-link>
      </div>
    </header>

    <main class="admin-main">
      <!-- Tabs -->
      <div class="admin-tabs">
        <button :class="{ active: tab === 'users' }" @click="tab = 'users'">משתמשים</button>
        <button :class="{ active: tab === 'subscriptions' }" @click="tab = 'subscriptions'">מנויים</button>
      </div>

      <!-- Users Tab -->
      <div v-if="tab === 'users'" class="admin-section">
        <div class="section-header-row">
          <h2>ניהול משתמשים</h2>
          <span class="count-badge ltr-number">{{ users.length }}</span>
        </div>
        <div v-if="loadingUsers" class="loading">טוען...</div>
        <table v-else class="admin-table">
          <thead>
            <tr>
              <th>שם</th>
              <th>אימייל</th>
              <th>טלפון</th>
              <th>חברה</th>
              <th>סטטוס</th>
              <th>אדמין</th>
              <th>תאריך הצטרפות</th>
              <th>פעולות</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.full_name || '—' }}</td>
              <td class="ltr-number">{{ u.email }}</td>
              <td class="ltr-number">{{ u.phone || '—' }}</td>
              <td>{{ u.company_name || '—' }}</td>
              <td>
                <span class="status-badge" :class="u.is_active ? 'active' : 'inactive'">
                  {{ u.is_active ? 'פעיל' : 'לא פעיל' }}
                </span>
              </td>
              <td>
                <span class="status-badge" :class="u.is_admin ? 'admin' : ''">
                  {{ u.is_admin ? 'כן' : 'לא' }}
                </span>
              </td>
              <td class="ltr-number">{{ formatDate(u.created_at) }}</td>
              <td class="actions-cell">
                <button
                  class="action-btn"
                  :class="u.is_active ? 'deactivate' : 'activate'"
                  @click="toggleActive(u)"
                >
                  {{ u.is_active ? 'השבת' : 'הפעל' }}
                </button>
                <button
                  class="action-btn admin-toggle"
                  @click="toggleAdmin(u)"
                >
                  {{ u.is_admin ? 'הסר אדמין' : 'הגדר אדמין' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Subscriptions Tab -->
      <div v-if="tab === 'subscriptions'" class="admin-section">
        <div class="section-header-row">
          <h2>כל המנויים</h2>
          <span class="count-badge ltr-number">{{ subscriptions.length }}</span>
        </div>
        <div v-if="loadingSubs" class="loading">טוען...</div>
        <table v-else class="admin-table">
          <thead>
            <tr>
              <th>משתמש</th>
              <th>מסלול</th>
              <th>סכום</th>
              <th>סטטוס</th>
              <th>תחילת מנוי</th>
              <th>תאריך סיום</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in subscriptions" :key="s.id">
              <td class="ltr-number">{{ s.user_id }}</td>
              <td>{{ s.plan === 'monthly' ? 'חודשי' : 'שנתי' }}</td>
              <td class="ltr-number">&#8362;{{ s.amount }}</td>
              <td>
                <span class="status-badge" :class="s.status">
                  {{ statusLabels[s.status] || s.status }}
                </span>
              </td>
              <td class="ltr-number">{{ formatDate(s.started_at) }}</td>
              <td class="ltr-number">{{ formatDate(s.expires_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client.js'

const tab = ref('users')
const users = ref([])
const subscriptions = ref([])
const loadingUsers = ref(true)
const loadingSubs = ref(true)

const statusLabels = {
  active: 'פעיל',
  pending: 'ממתין',
  cancelled: 'מבוטל',
  expired: 'פג תוקף',
}

onMounted(() => {
  fetchUsers()
  fetchSubscriptions()
})

async function fetchUsers() {
  loadingUsers.value = true
  try {
    const res = await api.get('/admin/users')
    users.value = res.data
  } catch (e) {
    console.error('Failed to fetch users:', e)
  } finally {
    loadingUsers.value = false
  }
}

async function fetchSubscriptions() {
  loadingSubs.value = true
  try {
    const res = await api.get('/admin/subscriptions')
    subscriptions.value = res.data
  } catch (e) {
    console.error('Failed to fetch subscriptions:', e)
  } finally {
    loadingSubs.value = false
  }
}

async function toggleActive(user) {
  try {
    const res = await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active })
    Object.assign(user, res.data)
  } catch (e) {
    console.error('Failed to update user:', e)
  }
}

async function toggleAdmin(user) {
  try {
    const res = await api.patch(`/admin/users/${user.id}`, { is_admin: !user.is_admin })
    Object.assign(user, res.data)
  } catch (e) {
    console.error('Failed to update user:', e)
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('he-IL')
  } catch {
    return dateStr
  }
}
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--bg);
}

.admin-header {
  background: #FFFFFF;
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.admin-header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.admin-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
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

.admin-badge {
  padding: 2px 10px;
  background: var(--accent-violet);
  color: white;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.btn-back-workspace {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.btn-back-workspace:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.admin-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.admin-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 4px;
  width: fit-content;
}

.admin-tabs button {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  transition: all 0.2s;
}

.admin-tabs button.active {
  background: var(--primary);
  color: white;
}

.admin-tabs button:hover:not(.active) {
  color: var(--primary);
}

.section-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-header-row h2 {
  font-size: 20px;
  font-weight: 700;
}

.count-badge {
  padding: 2px 10px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
}

.loading {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

.admin-table {
  width: 100%;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
}

.admin-table th {
  padding: 12px 16px;
  background: var(--bg);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  border-bottom: 1px solid var(--border);
}

.admin-table td {
  padding: 12px 16px;
  font-size: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.admin-table tr:last-child td {
  border-bottom: none;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.active { background: var(--green-light); color: var(--green); }
.status-badge.inactive { background: var(--red-light); color: var(--red); }
.status-badge.admin { background: rgba(127, 86, 217, 0.1); color: var(--accent-violet); }
.status-badge.pending { background: var(--amber-light); color: var(--amber); }
.status-badge.cancelled { background: var(--red-light); color: var(--red); }
.status-badge.expired { background: var(--bg); color: var(--text-muted); }

.actions-cell {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.action-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.action-btn.activate {
  background: var(--green-light);
  border-color: transparent;
  color: var(--green);
}

.action-btn.deactivate {
  background: var(--red-light);
  border-color: transparent;
  color: var(--red);
}
</style>
