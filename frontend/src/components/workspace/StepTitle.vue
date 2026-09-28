<template>
  <!-- A setup-step title, with the product names "Nifraim ROBOT" and
       "Nifraim Mail Agent" / "Nifraim Sms App" set as two-colour wordmarks (ink + the step's colour). -->
  <span class="st">
    <template v-for="(part, i) in parts" :key="i">
      <span v-if="part === ROBOT" class="st-brand" dir="ltr"><span class="st-b1">Nifraim</span> <span class="st-b2">ROBOT</span></span>
      <span v-else-if="part === SMS" class="st-brand" dir="ltr"><span class="st-b1">Nifraim</span> <span class="st-b4">Sms App</span></span>
      <span v-else-if="part === MAIL" class="st-brand" dir="ltr"><span class="st-b1">Nifraim</span> <span class="st-b3">Mail Agent</span></span>
      <template v-else-if="split && !hasBrand">
        <span class="st-ink">{{ firstWord(part) }}</span><span v-if="restOf(part)" class="st-rest" :style="{ color: accent }">{{ restOf(part) }}</span>
      </template>
      <template v-else>{{ part }}</template>
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const ROBOT = 'Nifraim ROBOT'
const MAIL = 'Nifraim Mail Agent'
const SMS = 'Nifraim Sms App'
const props = defineProps({
  title: { type: String, default: '' },
  // Page titles: two colours even without a brand — first word ink, the rest
  // in the step's colour ("מדף" · "ההסכמים").
  split: { type: Boolean, default: false },
  accent: { type: String, default: '#181818' },
})
const parts = computed(() => props.title.split(/(Nifraim ROBOT|Nifraim Mail Agent|Nifraim Sms App)/).filter(Boolean))
const hasBrand = computed(() => parts.value.some((x) => x === ROBOT || x === MAIL || x === SMS))
const firstWord = (t) => t.trim().split(/\s+/)[0]
const restOf = (t) => t.trim().split(/\s+/).slice(1).join(' ')
</script>

<style scoped>
.st-brand { font-family: 'Rubik', 'Heebo', sans-serif; font-weight: 800; letter-spacing: -0.01em; white-space: nowrap; unicode-bidi: isolate; }
.st-rest { margin-inline-start: 0.26em; }
.st-b1 { color: var(--text-primary, #181818); }
.st-b2 { color: #6C2E87; letter-spacing: 0.06em; }   /* = SETUP_ACCENTS.worker.deep */
.st-b3 { color: #2F6C94; }
.st-b4 { color: #35719A; }                             /* = SETUP_ACCENTS.phone.deep */                             /* = SETUP_ACCENTS.mail.deep (--tab-mail-ink) */
</style>
