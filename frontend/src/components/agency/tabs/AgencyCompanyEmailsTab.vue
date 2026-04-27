<template>
  <div class="em-tab">
    <div v-if="!data" class="loading">טוען אנשי קשר…</div>
    <div v-else-if="!data.by_company.length" class="empty">
      עדיין לא הוגדרו אנשי קשר בחברות הביטוח ע"י סוכני הסוכנות.
    </div>
    <div v-else class="grid">
      <div v-for="c in data.by_company" :key="c.company" class="co-card">
        <div class="co-head">
          <h3>{{ c.company }}</h3>
          <span class="badge">{{ c.contacts.length }}</span>
        </div>
        <ul>
          <li v-for="(ct, i) in c.contacts" :key="i">
            <div class="ct-row">
              <span class="ct-name">{{ ct.contact_name || '—' }}</span>
              <a :href="'mailto:' + ct.email" class="ct-email ltr-number">{{ ct.email }}</a>
            </div>
            <div class="ct-agent">מקור: {{ ct.agent_name }}</div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgencyStore } from '../../../stores/agency.js'

const agencyStore = useAgencyStore()
const data = computed(() => agencyStore.emails)
onMounted(() => { if (!agencyStore.emails) agencyStore.fetchCompanyEmails() })
</script>

<style scoped>
.em-tab { position: relative; z-index: 2; }
.loading { padding: 60px; text-align: center; color: var(--text-muted); }
.empty { padding: 60px 20px; text-align: center; color: var(--text-muted); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.co-card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
.co-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.co-head h3 { font-size: 14px; font-weight: 700; color: var(--text); }
.badge { background: var(--primary-light); color: var(--primary-deep); padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.co-card ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.co-card li { padding: 8px 0; border-bottom: 1px dashed var(--border-subtle); }
.co-card li:last-child { border-bottom: none; }
.ct-row { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.ct-name { font-size: 13px; font-weight: 600; color: var(--text); }
.ct-email { font-size: 12.5px; color: var(--primary-deep); text-decoration: none; }
.ct-email:hover { text-decoration: underline; }
.ct-agent { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
</style>
