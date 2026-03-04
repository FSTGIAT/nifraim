<template>
  <div class="production-tab">
    <div v-if="productionStore.loading" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>טוען...</span>
    </div>

    <template v-else>
      <ProductionUploader v-if="!productionStore.currentFile" />

      <ProductionFileInfo
        v-else
        :file="productionStore.currentFile"
        @replace="showReplace = true"
        @delete="handleDelete"
      />

      <Transition name="slide-up">
        <div v-if="showReplace && productionStore.currentFile" class="replace-section">
          <div class="replace-header">
            <div class="replace-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
              </svg>
              <h4>החלפת קובץ פרודוקציה</h4>
            </div>
            <button class="btn-cancel" @click="showReplace = false">ביטול</button>
          </div>
          <ProductionUploader />
        </div>
      </Transition>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import ProductionUploader from './ProductionUploader.vue'
import ProductionFileInfo from './ProductionFileInfo.vue'

const productionStore = useProductionStore()
const showReplace = ref(false)

onMounted(() => {
  productionStore.fetchCurrent()
})

watch(() => productionStore.currentFile, (newVal) => {
  if (newVal && showReplace.value) {
    showReplace.value = false
  }
})

async function handleDelete() {
  try {
    await productionStore.removeCurrent()
  } catch (e) {
    // error handled in store
  }
}
</script>

<style scoped>
.production-tab {
  animation: slideUp 0.4s var(--transition);
}

.loading-state {
  text-align: center;
  padding: 64px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 40px;
  height: 40px;
  position: relative;
  margin: 0 auto 16px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 6px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.replace-section {
  margin-top: 28px;
  padding: 24px;
  background: var(--amber-light);
  border: 1px solid var(--amber-light);
  border-radius: var(--radius-md);
}

.replace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.replace-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--amber);
}

.replace-header h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--amber);
}

.btn-cancel {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-muted);
  border: 1px solid var(--border);
  transition: all 0.25s var(--transition);
}

.btn-cancel:hover {
  background: var(--bg-surface);
  color: var(--text);
}

.slide-up-enter-active { animation: slideUp 0.4s var(--transition); }
.slide-up-leave-active { animation: fadeOut 0.2s ease-out; }

@keyframes fadeOut {
  to { opacity: 0; transform: translateY(-8px); }
}
</style>
