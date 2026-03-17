<template>
  <div class="commission-rates-tab">
    <div class="inner-tabs-bar">
      <div class="inner-tabs">
        <button
          class="inner-tab"
          :class="{ active: innerTab === 'nifraim' }"
          @click="innerTab = 'nifraim'"
        >
          עמלות נפרעים
        </button>
        <button
          class="inner-tab"
          :class="{ active: innerTab === 'volume' }"
          @click="innerTab = 'volume'"
        >
          עמלות היקף
        </button>
      </div>
    </div>

    <div class="tab-content">
      <CommissionRateTable v-if="innerTab === 'nifraim'" />
      <VolumeRateTable v-if="innerTab === 'volume'" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import CommissionRateTable from '../commission/CommissionRateTable.vue'
import VolumeRateTable from '../commission/VolumeRateTable.vue'

const innerTab = ref('nifraim')
</script>

<style scoped>
.commission-rates-tab {
  max-width: 1100px;
  margin: 0 auto;
}

.inner-tabs-bar {
  display: flex;
  align-items: center;
  border-bottom: 2px solid var(--border-subtle);
  margin-bottom: 16px;
}

.inner-tabs {
  display: flex;
  gap: 4px;
}

.inner-tab {
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all 0.25s var(--transition);
  white-space: nowrap;
}

.inner-tab:hover { color: var(--text-secondary); }

.inner-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}
</style>
