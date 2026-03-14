<template>
  <div class="portal-tab">
    <PortalLinksManager :show="true" :embedded="true" @close="() => {}" />
  </div>
</template>

<script setup>
import PortalLinksManager from './PortalLinksManager.vue'
</script>

<style scoped>
.portal-tab {
  min-height: 400px;
}
</style>
