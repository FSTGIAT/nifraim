<template>
  <Teleport to="body">
    <Transition name="ag-modal">
      <div v-if="open" class="ag-overlay" @click.self="$emit('close')">
        <div class="ag-card" :class="size">
          <header class="ag-head">
            <button class="ag-close" @click="$emit('close')" aria-label="סגור">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
            <div class="ag-head-text">
              <p class="ag-eyebrow" v-if="eyebrow">{{ eyebrow }}</p>
              <h2 class="ag-title">{{ title }}</h2>
            </div>
            <slot name="header-right" />
          </header>

          <div class="ag-body">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  eyebrow: { type: String, default: '' },
  size: { type: String, default: 'lg' }, // 'md' | 'lg' | 'xl'
})
defineEmits(['close'])
</script>

<style scoped>
.ag-overlay {
  position: fixed; inset: 0; z-index: 1010;
  background: rgba(45, 37, 34, 0.45);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
  font-family: 'Heebo', sans-serif;
}
.ag-card {
  width: 100%;
  max-height: 88vh;
  background: #FFFFFF;
  border-radius: 20px;
  box-shadow: 0 30px 80px -20px rgba(45, 37, 34, 0.45);
  overflow: hidden;
  display: flex; flex-direction: column;
  border: 1px solid rgba(45, 37, 34, 0.08);
}
.ag-card.md { max-width: 560px; }
.ag-card.lg { max-width: 880px; }
.ag-card.xl { max-width: 1200px; }

.ag-head {
  display: flex; align-items: center; gap: 12px;
  padding: 18px 22px;
  background: linear-gradient(180deg, #FFF8F0 0%, #FAF6F2 100%);
  border-bottom: 1px solid rgba(45, 37, 34, 0.08);
  position: relative;
}
.ag-close {
  background: rgba(45, 37, 34, 0.06);
  border: none; color: rgba(45, 37, 34, 0.7);
  width: 30px; height: 30px;
  border-radius: 8px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
  flex-shrink: 0;
}
.ag-close:hover { background: #2D2522; color: #fff; }

.ag-head-text { flex: 1; }
.ag-eyebrow {
  font-size: 10.5px; font-weight: 700; letter-spacing: 1.4px;
  text-transform: uppercase; color: #C85A00;
  margin-bottom: 2px;
}
.ag-title {
  font-size: 19px; font-weight: 800; color: #2D2522;
  letter-spacing: -0.3px;
}

.ag-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #F9F6F2;
}

/* ── transitions ── */
.ag-modal-enter-active, .ag-modal-leave-active {
  transition: opacity .25s var(--transition);
}
.ag-modal-enter-active .ag-card, .ag-modal-leave-active .ag-card {
  transition: transform .35s var(--transition), opacity .25s var(--transition);
}
.ag-modal-enter-from, .ag-modal-leave-to { opacity: 0; }
.ag-modal-enter-from .ag-card { transform: translateY(20px) scale(0.96); opacity: 0; }
.ag-modal-leave-to .ag-card { transform: translateY(10px) scale(0.98); opacity: 0; }

@media (max-width: 700px) {
  .ag-overlay { padding: 0; }
  .ag-card { max-height: 100vh; height: 100vh; border-radius: 0; }
}
</style>
