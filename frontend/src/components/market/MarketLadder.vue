<template>
  <section class="ml">
  <!-- סולם הסיכון — the leaders at each risk level (by real stock exposure, not by name). Category = text tabs,
       level = a segmented 1–5; tracks your customers hold carry a count that opens them. -->
    <nav class="ml-cats">
      <button v-for="c in MARKET_CATEGORIES" :key="c.id" type="button" :class="{ on: cat === c.id }" @click="cat = c.id">{{ c.label }}</button>
    </nav>
    <div class="ml-levels" role="tablist">
      <button v-for="l in RISK_LEVELS" :key="l.level" type="button" role="tab" :aria-selected="level === l.level"
              :class="{ on: level === l.level }" @click="level = l.level">
        <span class="ltr-number">{{ l.level }}</span> {{ l.label }}
      </button>
    </div>
    <div v-if="loading" class="ml-wait">טוען…</div>
    <template v-else-if="data">
      <p class="ml-sub">
        {{ data.category }} · רמת סיכון {{ data.risk_level }} · {{ data.tracks_in_level }} מסלולים מדורגים · נתוני {{ data.data_month }}
      </p>
      <p v-if="data.note" class="ml-note">{{ data.note }}</p>
      <RiskLadder v-if="(data.top || []).length" :key="cat + level" :tracks="data.top" :max="15"
                  @customers="(t, el) => $emit('customers', t, el)" />
      <p class="ml-rule">{{ data.rule }} {{ data.disclaimer }}</p>
    </template>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import RiskLadder from './RiskLadder.vue'
import { MARKET_CATEGORIES, RISK_LEVELS, useMarketStore } from '../../stores/market.js'

defineEmits(['customers'])
const store = useMarketStore()
const cat = ref('pension')
const level = ref(4)
const data = ref(null)
const loading = ref(false)
watch([cat, level], async () => {
  loading.value = true
  try { data.value = await store.loadLadder(cat.value, level.value) } finally { loading.value = false }
}, { immediate: true })
</script>

<style scoped>
.ml { display: flex; flex-direction: column; gap: 12px; }
.ml-cats { display: flex; gap: 18px; border-bottom: 1px solid var(--border-subtle, #E5E5E5); }
.ml-cats button {
  border: none; background: none; padding: 8px 2px; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  color: var(--text-secondary, #5C5C5C); border-bottom: 2.5px solid transparent; margin-bottom: -1px;
}
.ml-cats button.on { color: var(--tab-market-ink); border-bottom-color: var(--tab-market); }
.ml-levels { display: flex; gap: 4px; padding: 4px; border-radius: 12px; background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); align-self: flex-start; flex-wrap: wrap; }
.ml-levels button { border: none; background: none; padding: 6px 12px; border-radius: 9px; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; color: var(--text-secondary, #5C5C5C); }
.ml-levels button.on { background: var(--tab-market-ink); color: #fff; }
.ml-sub { margin: 0; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.ml-note { margin: 0; padding: 12px 14px; border-radius: 12px; background: var(--tab-market-wash); font-size: 13.5px; }
.ml-wait { padding: 24px; text-align: center; color: var(--text-secondary, #5C5C5C); }
.ml-rule { margin: 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
</style>
