<template>
  <div class="run-progress">
    <ol class="stages">
      <li
        v-for="s in STAGES"
        :key="s.key"
        class="stage"
        :class="stageClass(s.key)"
      >
        <span class="stage-dot" aria-hidden="true">
          <svg
            v-if="stageStatus(s.key) === 'done'"
            width="10" height="10" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
          ><polyline points="20 6 9 17 4 12"/></svg>
          <span v-else-if="stageStatus(s.key) === 'active'" class="stage-pulse"></span>
        </span>
        <span class="stage-label">{{ s.label }}</span>
      </li>
    </ol>

    <div v-if="run?.status === 'success'" class="banner banner--ok">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <span>הסתיים בהצלחה — הדוח נוסף להעלאות.</span>
    </div>
    <div v-else-if="run?.status === 'failed' || run?.status === 'timeout'" class="banner banner--err">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>{{ run?.status === 'timeout' ? 'פסק זמן' : 'נכשל' }}: {{ run?.error_message || 'שגיאה לא ידועה' }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const props = defineProps({
  runId: { type: String, required: true },
})
const emit = defineEmits(['success', 'failure'])

const store = usePortalAutomationStore()

const STAGES = [
  { key: 'login',    label: 'כניסה' },
  { key: 'otp',      label: 'קוד SMS' },
  { key: 'download', label: 'הורדה' },
  { key: 'parse',    label: 'עיבוד' },
]

const run = computed(() =>
  store.activeRun && store.activeRun.id === props.runId ? store.activeRun : null,
)

function stageStatus(name) {
  if (!run.value || !run.value.stage) return 'idle'
  const order = STAGES.map((s) => s.key)
  const cur = order.indexOf(run.value.stage)
  const idx = order.indexOf(name)
  if (idx < cur) return 'done'
  if (idx === cur) return 'active'
  return 'idle'
}
function stageClass(name) {
  return `stage--${stageStatus(name)}`
}

watch(
  () => run.value?.status,
  (s) => {
    if (s === 'success') emit('success', run.value)
    if (s === 'failed' || s === 'timeout') emit('failure', run.value)
  },
)
</script>

<style scoped>
.run-progress {
  font-family: 'Heebo', sans-serif;
  padding: 8px 10px 4px;
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.16);
  border-radius: 10px;
}

.stages {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.stage {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
}
.stage-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.06);
  color: var(--text-muted);
  flex-shrink: 0;
}
.stage--done {
  background: rgba(46, 132, 74, 0.10);
  border-color: rgba(46, 132, 74, 0.28);
  color: #1B5E20;
}
.stage--done .stage-dot { background: #1B5E20; color: #fff; }
.stage--active {
  background: rgba(245, 124, 0, 0.10);
  border-color: rgba(245, 124, 0, 0.30);
  color: var(--primary-deep, #E65100);
}
.stage--active .stage-dot { background: transparent; }
.stage-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--primary, #F57C00);
  animation: stagePulse 1.2s ease-in-out infinite;
}
@keyframes stagePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 124, 0, 0.50); transform: scale(1); }
  50%      { box-shadow: 0 0 0 5px rgba(245, 124, 0, 0); transform: scale(1.15); }
}

.banner {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}
.banner--ok  { background: rgba(46, 132, 74, 0.10); color: #1B5E20; border: 1px solid rgba(46, 132, 74, 0.24); }
.banner--err { background: rgba(194, 57, 52, 0.08);  color: #C23934; border: 1px solid rgba(194, 57, 52, 0.24); }
</style>
