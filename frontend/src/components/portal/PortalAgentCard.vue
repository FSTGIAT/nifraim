<template>
  <section v-if="agent && (agent.name || agent.phone)" class="agent-card" aria-label="הסוכן שלך">
    <span class="agent-avatar" aria-hidden="true">{{ initials }}</span>
    <div class="agent-text">
      <span class="agent-kicker">הסוכן שלך</span>
      <span class="agent-name">{{ agent.name || 'הסוכן שלך' }}</span>
      <span v-if="agent.company_name" class="agent-company">{{ agent.company_name }}</span>
    </div>
    <div v-if="phone" class="agent-actions">
      <a class="agent-btn" :href="`tel:${phone}`">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
        חיוג
      </a>
      <a class="agent-btn agent-btn--ghost" :href="whatsapp" target="_blank" rel="noopener noreferrer">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
        וואטסאפ
      </a>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ agent: { type: Object, default: null } })

const phone = computed(() => (props.agent?.phone || '').replace(/[^\d+]/g, ''))
// wa.me wants the international form without "+" or the leading 0 (IL: 972…)
const whatsapp = computed(() => {
  const d = phone.value.replace(/^\+/, '')
  return `https://wa.me/${d.startsWith('0') ? '972' + d.slice(1) : d}`
})
const initials = computed(() =>
  (props.agent?.name || '').trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join('') || '?',
)
</script>

<style scoped>
.agent-card {
  margin-top: 20px;
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  padding: 16px 18px; border-radius: 14px;
  background: var(--card-bg, #fff); border: 1px solid var(--border-subtle, #E5E7EB);
  box-shadow: var(--shadow-sm, 0 2px 6px rgba(24, 24, 24, 0.05));
}
.agent-avatar {
  width: 46px; height: 46px; flex-shrink: 0; display: grid; place-items: center; border-radius: 50%;
  font-size: 16px; font-weight: 800; color: var(--tab-portal-ink, #35719A);
  background: var(--tab-portal-wash, rgba(78, 157, 208, 0.12));
}
.agent-text { flex: 1; min-width: 140px; display: flex; flex-direction: column; }
.agent-kicker { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.agent-name { font-size: 16px; font-weight: 800; color: var(--text); }
.agent-company { font-size: 12.5px; color: var(--text-muted); }
.agent-actions { display: flex; gap: 8px; }
.agent-btn {
  display: inline-flex; align-items: center; gap: 6px; min-height: 44px; padding: 0 16px;
  border-radius: 10px; font-size: 14px; font-weight: 700; text-decoration: none;
  background: var(--tab-portal-ink, #35719A); color: #fff;
}
.agent-btn--ghost { background: transparent; color: var(--tab-portal-ink, #35719A); border: 1px solid var(--tab-portal-ink, #35719A); }
.agent-btn:focus-visible { outline: 2px solid var(--tab-portal-ink, #35719A); outline-offset: 2px; }
@media print { .agent-actions { display: none; } }
</style>
