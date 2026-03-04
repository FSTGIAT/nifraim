<template>
  <div class="recruits-tab">
    <!-- No production file hint -->
    <div v-if="!productionStore.currentFile && !productionStore.loading" class="hint-banner">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      <span>העלה קובץ פרודוקציה בלשונית "פרודוקציה" כדי לבדוק מגויסים מולו</span>
    </div>

    <!-- Recruit entry form -->
    <RecruitForm />

    <!-- Compare button -->
    <div class="compare-section" v-if="recruitsStore.recruits.length > 0">
      <button
        class="btn-compare"
        :disabled="!productionStore.currentFile || recruitsStore.comparing"
        @click="runComparison"
      >
        <template v-if="recruitsStore.comparing">
          <div class="btn-spinner"></div>
          <span>בודק...</span>
        </template>
        <template v-else>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <span>בדוק מול פרודוקציה</span>
        </template>
      </button>
      <p class="compare-hint" v-if="!productionStore.currentFile">
        יש להעלות קובץ פרודוקציה לפני ביצוע בדיקה
      </p>
    </div>

    <!-- Comparison results -->
    <Transition name="results">
      <RecruitComparisonResults
        v-if="recruitsStore.comparisonResult"
        :result="recruitsStore.comparisonResult"
      />
    </Transition>

    <Transition name="fade">
      <p class="error-msg" v-if="recruitsStore.error">{{ recruitsStore.error }}</p>
    </Transition>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useRecruitsStore } from '../../stores/recruits.js'
import RecruitForm from './RecruitForm.vue'
import RecruitComparisonResults from './RecruitComparisonResults.vue'

const productionStore = useProductionStore()
const recruitsStore = useRecruitsStore()

onMounted(() => {
  if (!productionStore.currentFile && !productionStore.loading) {
    productionStore.fetchCurrent()
  }
})

async function runComparison() {
  try {
    await recruitsStore.compareRecruits()
  } catch (e) {
    // error handled in store
  }
}
</script>

<style scoped>
.recruits-tab {
  animation: slideUp 0.4s var(--transition);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hint-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: var(--amber-light);
  border: 1px solid var(--amber-light);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--amber);
}

.compare-section {
  text-align: center;
}

.btn-compare {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 36px;
  background: linear-gradient(135deg, var(--accent-violet), var(--primary-deep));
  color: white;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  transition: all 0.3s var(--transition);
  position: relative;
  overflow: hidden;
}

.btn-compare::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

.btn-compare:hover:not(:disabled) {
  box-shadow: 0 8px 32px rgba(127, 86, 217, 0.08);
  transform: translateY(-2px);
}

.btn-compare:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-compare:disabled::before {
  display: none;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.compare-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 10px;
}

.results-enter-active { animation: slideUp 0.5s var(--transition); }
.results-leave-active { animation: fadeOut 0.2s ease-out; }
@keyframes fadeOut { to { opacity: 0; } }

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

.error-msg {
  color: var(--red);
  font-size: 13px;
  text-align: center;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}
</style>
