import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

/**
 * What the AI assistant currently knows about the screen you are looking at.
 *
 * The per-view summary used to be a full-width card above every comparison
 * (`AiInsightCard`), which meant the AI's presence cost a band of the page on
 * every dashboard and existed nowhere else. The assistant is now one global
 * widget, so the CONTEXT has to travel instead of the card: whichever view can
 * describe itself publishes here, and the widget and sheet read it.
 *
 * A view that publishes nothing is not an error — the assistant still opens,
 * just without view context, exactly as it does from the home screen.
 */
export const useAiContextStore = defineStore('aiContext', () => {
  const viewTitle = ref('')
  const viewContextString = ref('')
  const summary = ref('')
  const suggestions = ref([])

  const open = ref(false)
  const initialQuestion = ref('')

  /** True when the current screen can tell the AI what it is showing. */
  const hasContext = computed(() => !!viewContextString.value)

  /** Called by a view that can describe itself. Pass null to clear on unmount. */
  function publish(ctx) {
    viewTitle.value = ctx?.viewTitle || ''
    viewContextString.value = ctx?.viewContextString || ''
    summary.value = ctx?.summary || ''
    suggestions.value = ctx?.suggestions || []
  }

  function clear() {
    publish(null)
  }

  /** Open the conversation, optionally seeded with a question. */
  function openSheet(question = '') {
    initialQuestion.value = question || ''
    open.value = true
  }

  return {
    viewTitle, viewContextString, summary, suggestions,
    open, initialQuestion, hasContext,
    publish, clear, openSheet,
  }
})
