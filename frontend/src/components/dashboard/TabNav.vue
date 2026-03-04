<template>
  <nav class="tab-nav">
    <router-link to="/dashboard" class="tab-pill" :class="{ active: $route.path === '/dashboard' }">
      רשומות
    </router-link>
    <router-link to="/analytics" class="tab-pill" :class="{ active: $route.path === '/analytics' }">
      ניתוח
    </router-link>
  </nav>
</template>

<style scoped>
.tab-nav {
  display: flex;
  gap: 4px;
  background: var(--bg-surface);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 4px;
}

.tab-pill {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.tab-pill:hover {
  color: var(--text);
}

.tab-pill.active {
  background: var(--card-bg);
  color: var(--text);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  font-weight: 600;
}
</style>
