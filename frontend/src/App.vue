<template>
  <div id="app-root">
    <div class="bg-mesh"></div>
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  /* Salesforce Lightning inspired palette */
  --green: #2E844A;
  --green-deep: #1B5E20;
  --green-light: #EBF7EE;
  --amber: #E8720A;
  --amber-light: #FFF3E0;
  --red: #EA001E;
  --red-deep: #C23934;
  --red-light: #FEF1EE;
  --gray: #706E6B;
  --light-gray: #DDDBDA;
  --bg: #F3F3F3;
  --bg-surface: #FFFFFF;
  --card-bg: #FFFFFF;
  --card-bg-solid: #FFFFFF;
  --glass: rgba(255, 255, 255, 0.95);
  --glass-border: #DDDBDA;
  --glass-hover: #F7F7F7;
  --border: #DDDBDA;
  --border-subtle: #E5E5E5;
  --text: #181818;
  --text-secondary: #3E3E3C;
  --text-muted: #706E6B;
  --primary: #0176D3;
  --primary-deep: #014486;
  --primary-glow: rgba(1, 118, 211, 0.1);
  --primary-light: #EBF5FE;
  --accent-cyan: #06A59A;
  --accent-violet: #7F56D9;
  --accent-rose: #E3066A;
  --accent-emerald: #2E844A;
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 4px 14px rgba(0, 0, 0, 0.1);
  --shadow-glow: 0 0 0 3px rgba(1, 118, 211, 0.15);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --transition: cubic-bezier(0.16, 1, 0.3, 1);
}

body {
  font-family: 'Heebo', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  color: var(--text);
  direction: rtl;
  min-height: 100vh;
  overflow-x: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app-root {
  min-height: 100vh;
  position: relative;
}

/* Clean background */
.bg-mesh {
  display: none;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes pulse-soft {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* LTR override for numbers */
.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

button {
  font-family: 'Heebo', sans-serif;
  cursor: pointer;
  border: none;
  background: none;
}

input, select, textarea {
  font-family: 'Heebo', sans-serif;
  outline: none;
}

a {
  text-decoration: none;
  color: var(--primary);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

/* Card utility */
.glass-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}
</style>
