<template>
  <Teleport to="body">
    <div v-if="show" class="imp-banner" role="status">
      <div class="imp-banner-inner">
        <span class="imp-eye" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </span>
        <span class="imp-text">
          מציג בשם <strong>{{ name }}</strong>
        </span>
        <button class="imp-exit" @click="exit">חזור לסוכנות</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { isImpersonating, getImpersonatedName, endImpersonation } from '../../api/client.js'
import { useAuthStore } from '../../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const show = computed(() => isImpersonating())
const name = computed(() => getImpersonatedName() || 'סוכן')

async function exit() {
  endImpersonation()
  await auth.fetchUser()
  router.push('/agency')
}
</script>

<style scoped>
.imp-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9000;
  background: linear-gradient(135deg, #F57C00 0%, #E65100 100%);
  color: #fff;
  padding: 8px 16px;
  font-family: 'Heebo', sans-serif;
  box-shadow: 0 2px 12px rgba(245, 124, 0, 0.4);
}
.imp-banner-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 14px;
}
.imp-eye {
  display: inline-flex;
  width: 26px; height: 26px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  align-items: center; justify-content: center;
}
.imp-text { flex: 1; font-size: 14px; }
.imp-exit {
  background: rgba(255,255,255,0.18);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.35);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: background .15s;
}
.imp-exit:hover { background: rgba(255,255,255,0.32); }
</style>
