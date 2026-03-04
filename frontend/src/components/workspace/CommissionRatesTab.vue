<template>
  <div class="commission-rates-tab">
    <CommissionRateTable />
  </div>
</template>

<script setup>
import CommissionRateTable from '../commission/CommissionRateTable.vue'
</script>

<style scoped>
.commission-rates-tab {
  max-width: 900px;
  margin: 0 auto;
}
</style>
