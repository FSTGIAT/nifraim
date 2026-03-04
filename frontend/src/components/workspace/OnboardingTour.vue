<template>
  <Teleport to="body">
    <Transition name="tour-fade">
      <div
        v-if="isActive"
        class="tour-overlay"
        :class="{
          'tour-overlay--dimmed': !spotlightReady,
        }"
        @click.self="onOverlayClick"
      >
        <!-- Spotlight cutout -->
        <div
          v-if="spotlightRect"
          class="tour-spotlight"
          :style="spotlightStyle"
        ></div>

        <!-- Tooltip card for spotlight steps (target found) -->
        <div
          v-if="currentStep?.type === 'spotlight' && spotlightRect && tooltipPosition"
          class="tour-tooltip"
          :class="{ 'tour-tooltip--above': tooltipPosition.placementAbove }"
          :style="tooltipStyle"
        >
          <div class="tour-tooltip-arrow" :class="{ 'tour-tooltip-arrow--above': tooltipPosition.placementAbove }"></div>
          <h3 class="tour-tooltip-title">{{ currentStep.title }}</h3>
          <p class="tour-tooltip-desc">{{ currentStep.description }}</p>
          <div class="tour-tooltip-footer">
            <div class="tour-dots">
              <span
                v-for="(step, i) in totalSteps"
                :key="i"
                class="tour-dot"
                :class="{
                  'tour-dot--active': i === currentStepIndex,
                  'tour-dot--done': i < currentStepIndex,
                }"
              ></span>
            </div>
            <div class="tour-actions">
              <button v-if="currentStepIndex > 0" class="tour-btn tour-btn--ghost" @click="$emit('prev')">
                הקודם
              </button>
              <button class="tour-btn tour-btn--primary" @click="$emit('next')">
                {{ currentStepIndex < totalSteps - 1 ? 'הבא' : 'סיום' }}
              </button>
            </div>
          </div>
          <button class="tour-skip" @click="$emit('skip')">דלג</button>
        </div>

        <!-- Fallback: spotlight step but target not found — show as center card -->
        <div
          v-if="currentStep?.type === 'spotlight' && !spotlightRect"
          class="tour-center-card"
        >
          <h2 class="tour-center-title">{{ currentStep.title }}</h2>
          <p class="tour-center-desc">{{ currentStep.description }}</p>
          <div class="tour-center-footer">
            <div class="tour-dots tour-dots--center">
              <span
                v-for="(step, i) in totalSteps"
                :key="i"
                class="tour-dot"
                :class="{
                  'tour-dot--active': i === currentStepIndex,
                  'tour-dot--done': i < currentStepIndex,
                }"
              ></span>
            </div>
            <div class="tour-center-actions">
              <button v-if="currentStepIndex > 0" class="tour-btn tour-btn--ghost" @click="$emit('prev')">
                הקודם
              </button>
              <button class="tour-btn tour-btn--primary" @click="$emit('next')">
                {{ currentStepIndex < totalSteps - 1 ? 'הבא' : 'סיום' }}
              </button>
            </div>
          </div>
          <button class="tour-skip tour-skip--center" @click="$emit('skip')">דלג</button>
        </div>

        <!-- Center card for welcome/done steps -->
        <Transition name="tour-card">
          <div
            v-if="currentStep?.type === 'center'"
            class="tour-center-card"
            :key="currentStep.id"
          >
            <div class="tour-center-icon" :class="'tour-center-icon--' + currentStep.icon">
              <svg v-if="currentStep.icon === 'layers'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
              <svg v-else-if="currentStep.icon === 'check'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <h2 class="tour-center-title">{{ currentStep.title }}</h2>
            <p class="tour-center-desc">{{ currentStep.description }}</p>
            <button
              class="tour-btn tour-btn--primary tour-btn--lg"
              @click="currentStep.id === 'welcome' ? $emit('next') : $emit('complete')"
            >
              {{ currentStep.id === 'welcome' ? 'התחל סיור' : '!בוא נתחיל' }}
            </button>
            <button
              v-if="currentStep.id === 'welcome'"
              class="tour-skip tour-skip--center"
              @click="$emit('skip')"
            >
              דלג על הסיור
            </button>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isActive: { type: Boolean, default: false },
  currentStep: { type: Object, default: null },
  currentStepIndex: { type: Number, default: 0 },
  totalSteps: { type: Number, default: 0 },
  spotlightRect: { type: Object, default: null },
  tooltipPosition: { type: Object, default: null },
  spotlightReady: { type: Boolean, default: false },
})

defineEmits(['next', 'prev', 'skip', 'complete'])

const spotlightStyle = computed(() => {
  if (!props.spotlightRect) return {}
  const r = props.spotlightRect
  return {
    top: `${r.top}px`,
    left: `${r.left}px`,
    width: `${r.width}px`,
    height: `${r.height}px`,
    borderRadius: `${r.borderRadius}px`,
  }
})

const tooltipStyle = computed(() => {
  if (!props.tooltipPosition) return {}
  return {
    top: props.tooltipPosition.top,
    left: props.tooltipPosition.left,
    width: props.tooltipPosition.width,
  }
})

function onOverlayClick() {
  // Only allow clicking overlay to dismiss on center steps — do nothing for spotlight
}
</script>

<style scoped>
/* Overlay always covers the screen; dim by default, transparent when spotlight takes over */
.tour-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  pointer-events: auto;
  background: transparent;
  transition: background 0.35s ease;
}

/* Dimmed state: used for center steps and while spotlight is loading */
.tour-overlay--dimmed {
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Spotlight cutout with box-shadow */
.tour-spotlight {
  position: fixed;
  z-index: 5001;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.55);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: none;
}

.tour-spotlight::after {
  content: '';
  position: absolute;
  inset: -2px;
  border: 2px solid var(--primary);
  border-radius: inherit;
  animation: tour-pulse 2s ease-in-out infinite;
}

@keyframes tour-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(1, 118, 211, 0.3); }
  50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(1, 118, 211, 0); }
}

/* Tooltip card */
.tour-tooltip {
  position: fixed;
  z-index: 5002;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
  padding: 20px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.tour-tooltip-arrow {
  position: absolute;
  top: -7px;
  right: 50%;
  width: 14px;
  height: 14px;
  background: #fff;
  border: 1px solid var(--border);
  border-bottom: none;
  border-right: none;
  transform: translateX(50%) rotate(45deg);
}

.tour-tooltip-arrow--above {
  top: auto;
  bottom: -7px;
  border: 1px solid var(--border);
  border-top: none;
  border-left: none;
  transform: translateX(50%) rotate(45deg);
}

.tour-tooltip-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.tour-tooltip-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
  white-space: pre-line;
}

.tour-tooltip-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Progress dots */
.tour-dots {
  display: flex;
  gap: 6px;
}

.tour-dots--center {
  justify-content: center;
  margin-bottom: 16px;
}

.tour-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-subtle);
  transition: all 0.3s ease;
}

.tour-dot--active {
  background: var(--primary);
  transform: scale(1.3);
}

.tour-dot--done {
  background: var(--accent-cyan);
}

/* Action buttons */
.tour-actions {
  display: flex;
  gap: 8px;
}

.tour-btn {
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.tour-btn--primary {
  background: var(--primary);
  color: #fff;
}

.tour-btn--primary:hover {
  background: var(--primary-deep);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(1, 118, 211, 0.3);
}

.tour-btn--ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.tour-btn--ghost:hover {
  background: var(--bg-surface);
  border-color: var(--text-muted);
}

.tour-btn--lg {
  padding: 12px 32px;
  font-size: 16px;
  border-radius: var(--radius-sm);
}

/* Skip button */
.tour-skip {
  display: block;
  margin-top: 10px;
  margin-right: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: color 0.2s;
}

.tour-skip:hover {
  color: var(--text-secondary);
}

.tour-skip--center {
  margin: 12px auto 0;
  font-size: 13px;
}

/* Center card */
.tour-center-card {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
  padding: 40px 32px;
  max-width: 420px;
  width: 90%;
  text-align: center;
  z-index: 5002;
}

.tour-center-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  color: #fff;
}

.tour-center-icon--layers {
  background: linear-gradient(135deg, var(--primary), var(--accent-cyan));
}

.tour-center-icon--check {
  background: linear-gradient(135deg, var(--accent-emerald), var(--accent-cyan));
}

.tour-center-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 10px;
  letter-spacing: -0.3px;
}

.tour-center-desc {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-bottom: 28px;
  white-space: pre-line;
}

.tour-center-footer {
  margin-top: 8px;
}

.tour-center-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* Transitions */
.tour-fade-enter-active {
  transition: opacity 0.3s ease;
}
.tour-fade-leave-active {
  transition: opacity 0.2s ease;
}
.tour-fade-enter-from,
.tour-fade-leave-to {
  opacity: 0;
}

.tour-card-enter-active {
  animation: tour-card-in 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.tour-card-leave-active {
  animation: tour-card-out 0.2s ease;
}

@keyframes tour-card-in {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@keyframes tour-card-out {
  from {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
  to {
    opacity: 0;
    transform: scale(0.95) translateY(-8px);
  }
}
</style>
