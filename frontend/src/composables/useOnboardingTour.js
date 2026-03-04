import { ref, computed, nextTick, onUnmounted } from 'vue'

const TOUR_STEPS = [
  {
    id: 'welcome',
    type: 'center',
    title: 'Nifraim-ברוכים הבאים ל',
    description: 'מערכת חכמה לניהול והתאמת נתוני ביטוח.\nבואו נכיר את הכלים העיקריים בסיור קצר.',
    icon: 'layers',
  },
  {
    id: 'production',
    type: 'spotlight',
    target: '[data-tour="production-uploader"]',
    placement: 'bottom',
    switchTab: 'production',
    title: 'העלאת פרודוקציה',
    description: 'כאן מעלים את קובץ הפרודוקציה מהסוכנות. פשוט גוררים קובץ Excel לאזור הזה.',
  },
  {
    id: 'comparison',
    type: 'spotlight',
    target: '[data-tour="tab-comparison"]',
    placement: 'bottom',
    title: 'השוואת נפרעים',
    description: 'לאחר העלאת פרודוקציה, כאן מעלים דוחות נפרעים מחברות הביטוח ומשווים מול הפרודוקציה.',
  },
  {
    id: 'commission-rates',
    type: 'spotlight',
    target: '[data-tour="tab-commission-rates"]',
    placement: 'bottom',
    title: 'טבלת עמלות',
    description: 'ניהול שיעורי עמלות לפי חברה ומוצר. הנתונים משמשים לחישוב הפרשי עמלות.',
  },
  {
    id: 'company-emails',
    type: 'spotlight',
    target: '[data-tour="tab-company-emails"]',
    placement: 'bottom',
    title: 'אימיילים לחברות',
    description: 'שמירת כתובות אימייל של אנשי קשר בחברות הביטוח לשליחת בירורים ישירות מהמערכת.',
  },
  {
    id: 'settings',
    type: 'spotlight',
    target: '[data-tour="settings-gear"]',
    placement: 'bottom',
    title: 'הגדרות',
    description: 'הגדרות אישיות כמו ספק דוא"ל מועדף לשליחת מיילים מהמערכת.',
  },
  {
    id: 'done',
    type: 'center',
    title: '!הכל מוכן',
    description: 'עכשיו אפשר להתחיל! העלו קובץ פרודוקציה כדי לצאת לדרך.',
    icon: 'check',
  },
]

export function useOnboardingTour({ activeTab }) {
  const isActive = ref(false)
  const currentStepIndex = ref(0)
  const spotlightRect = ref(null)
  const tooltipPosition = ref(null)
  // Track when spotlight is fully ready so overlay can fade out
  const spotlightReady = ref(false)
  let resizeTimer = null

  const currentStep = computed(() =>
    isActive.value ? TOUR_STEPS[currentStepIndex.value] : null
  )

  const totalSteps = TOUR_STEPS.length

  function shouldShowTour() {
    return localStorage.getItem('onboarding_completed') !== 'true'
  }

  function markCompleted() {
    localStorage.setItem('onboarding_completed', 'true')
  }

  async function findTarget(selector) {
    // Try up to 6 times with 300ms intervals (1.8s total) to handle loading states
    for (let i = 0; i < 6; i++) {
      const el = document.querySelector(selector)
      if (el) return el
      await new Promise(r => setTimeout(r, 300))
    }
    return null
  }

  async function measureTarget(step) {
    if (step.type === 'center') {
      spotlightRect.value = null
      tooltipPosition.value = null
      spotlightReady.value = false
      return true
    }

    const el = await findTarget(step.target)
    if (!el) {
      // Target not found — fall back to center-style display
      spotlightRect.value = null
      tooltipPosition.value = null
      spotlightReady.value = false
      return true // still show step as center fallback
    }

    computePositions(el, step)
    spotlightReady.value = true
    return true
  }

  function computePositions(el, step) {
    const rect = el.getBoundingClientRect()
    const padding = 8

    spotlightRect.value = {
      top: rect.top - padding,
      left: rect.left - padding,
      width: rect.width + padding * 2,
      height: rect.height + padding * 2,
      borderRadius: 12,
    }

    // Tooltip positioning
    const tooltipWidth = 340
    const tooltipGap = 16
    const viewportMargin = 16

    let top, left

    if (step.placement === 'bottom') {
      top = rect.bottom + tooltipGap
      left = rect.left + rect.width / 2 - tooltipWidth / 2
    } else if (step.placement === 'top') {
      top = rect.top - tooltipGap
      left = rect.left + rect.width / 2 - tooltipWidth / 2
    } else {
      top = rect.bottom + tooltipGap
      left = rect.left + rect.width / 2 - tooltipWidth / 2
    }

    // Clamp to viewport
    if (left < viewportMargin) left = viewportMargin
    if (left + tooltipWidth > window.innerWidth - viewportMargin) {
      left = window.innerWidth - viewportMargin - tooltipWidth
    }

    tooltipPosition.value = {
      top: `${top}px`,
      left: `${left}px`,
      width: `${tooltipWidth}px`,
      placementAbove: step.placement === 'top',
    }
  }

  async function goToStep(index) {
    const step = TOUR_STEPS[index]
    if (!step) return

    // Switch tab if needed
    if (step.switchTab && activeTab.value !== step.switchTab) {
      activeTab.value = step.switchTab
      await nextTick()
      // Wait for tab animation to settle
      await new Promise(r => setTimeout(r, 450))
    }

    // Clear spotlight before changing step so overlay stays dimmed during transition
    spotlightRect.value = null
    tooltipPosition.value = null
    spotlightReady.value = false

    currentStepIndex.value = index
    await nextTick()
    await measureTarget(step)
  }

  async function startTour() {
    isActive.value = true
    currentStepIndex.value = 0
    spotlightRect.value = null
    tooltipPosition.value = null
    spotlightReady.value = false
    window.addEventListener('resize', onResize)
    await goToStep(0)
  }

  async function nextStep() {
    if (currentStepIndex.value < totalSteps - 1) {
      await goToStep(currentStepIndex.value + 1)
    } else {
      completeTour()
    }
  }

  async function prevStep() {
    if (currentStepIndex.value > 0) {
      await goToStep(currentStepIndex.value - 1)
    }
  }

  function skipTour() {
    markCompleted()
    closeTour()
  }

  function completeTour() {
    markCompleted()
    closeTour()
    // Return to production tab
    activeTab.value = 'production'
  }

  function closeTour() {
    isActive.value = false
    spotlightRect.value = null
    tooltipPosition.value = null
    spotlightReady.value = false
    currentStepIndex.value = 0
    window.removeEventListener('resize', onResize)
  }

  function onResize() {
    clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => {
      if (isActive.value && currentStep.value) {
        measureTarget(currentStep.value)
      }
    }, 100)
  }

  function onKeydown(e) {
    if (!isActive.value) return
    if (e.key === 'Escape') {
      skipTour()
    } else if (e.key === 'ArrowLeft') {
      // RTL: left = next
      nextStep()
    } else if (e.key === 'ArrowRight') {
      // RTL: right = prev
      prevStep()
    }
  }

  function cleanup() {
    window.removeEventListener('resize', onResize)
    clearTimeout(resizeTimer)
  }

  onUnmounted(cleanup)

  return {
    // State
    isActive,
    currentStep,
    currentStepIndex,
    totalSteps,
    spotlightRect,
    tooltipPosition,
    spotlightReady,
    // Actions
    shouldShowTour,
    startTour,
    nextStep,
    prevStep,
    skipTour,
    completeTour,
    onKeydown,
    cleanup,
  }
}
