import { Steps } from '@ark-ui/react/steps'
import './ActivationCard.css'

/**
 * ActivationCard — compact new-user activation card (React island, mounted by
 * ActivationChecklist.vue). Uses Ark UI <Steps> for the horizontal stepper and
 * shows ONLY the current step's action below it. Pastel, RTL, no orange.
 *
 * Props (all from the Vue host):
 *   steps:        [{ id, label, hint, cta, done }]   // Hebrew copy lives in the host
 *   completedCount, total, currentIndex, allDone
 *   onAction(stepId), onClose()
 */

const ACCENT = {
  phone: { c: '#4E9DD0', soft: 'rgba(78,157,208,0.14)' },
  portal: { c: '#8E6FD6', soft: 'rgba(183,156,235,0.16)' },
  run: { c: '#1FA88C', soft: 'rgba(143,217,198,0.20)' },
  register: { c: '#2E844A', soft: '#EBF7EE' },
}

function Icon({ id }) {
  const p = {
    width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none',
    stroke: 'currentColor', strokeWidth: 1.9, strokeLinecap: 'round', strokeLinejoin: 'round',
  }
  if (id === 'phone') return (<svg {...p}><rect x="6" y="3" width="12" height="18" rx="3" /><line x1="11" y1="18" x2="13" y2="18" /></svg>)
  if (id === 'portal') return (<svg {...p}><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M9 8h.01M15 8h.01M9 12h.01M15 12h.01M9 16h6" /></svg>)
  if (id === 'run') return (<svg {...p}><path d="M12 3v12" /><path d="M7 11l5 5 5-5" /><path d="M5 21h14" /></svg>)
  return null
}

function CheckSm() {
  return (<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 13l4 4L19 7" /></svg>)
}
function Chevron() {
  return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg>)
}
function Close() {
  return (<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18M6 6l12 12" /></svg>)
}

export function ActivationCard({ steps = [], completedCount = 0, total = 4, currentIndex = 0, allDone = false, onAction, onClose }) {
  const current = !allDone && currentIndex >= 0 ? steps[currentIndex] : null
  const accent = current ? (ACCENT[current.id] || ACCENT.run) : ACCENT.register

  return (
    <div className="actc" dir="rtl">
      <button type="button" className="actc-close" aria-label="הסתר" onClick={onClose}><Close /></button>

      <div className="actc-head">
        <div className="actc-titles">
          <h3 className="actc-title">הפעלת האוטומציה</h3>
          <p className="actc-sub">{allDone ? 'הכול מוכן — האוטומציה פעילה.' : 'עוד כמה צעדים וההורדה תרוץ לבד.'}</p>
        </div>
        <span className="actc-counter">{completedCount}/{total}</span>
      </div>

      <Steps.Root count={total} step={completedCount} className="actc-steps">
        <Steps.List className="actc-steps-list">
          {steps.map((s, i) => {
            const state = s.done ? 'done' : (i === currentIndex ? 'current' : 'todo')
            const a = ACCENT[s.id] || ACCENT.run
            return (
              <Steps.Item key={s.id} index={i} className="actc-item">
                <Steps.Indicator className={`actc-ind actc-ind--${state}`} style={{ '--accent': a.c }}>
                  {s.done ? <CheckSm /> : <span className="actc-ind-num">{i + 1}</span>}
                </Steps.Indicator>
                <Steps.Separator className={`actc-sep${i < completedCount ? ' is-done' : ''}`} hidden={i === total - 1} />
              </Steps.Item>
            )
          })}
        </Steps.List>
      </Steps.Root>

      {allDone ? (
        <div className="actc-done">
          <span className="actc-done-badge"><CheckSm /></span>
          <div className="actc-current-text">
            <span className="actc-current-label">האוטומציה פעילה</span>
            <span className="actc-current-hint">כל החברות יורדות ומתאחדות ל-2 קבצים בלחיצה אחת.</span>
          </div>
        </div>
      ) : current ? (
        <div className="actc-current" style={{ '--accent': accent.c, '--accent-soft': accent.soft }}>
          <span className="actc-current-chip"><Icon id={current.id} /></span>
          <div className="actc-current-text">
            <span className="actc-current-label">{current.label}</span>
            <span className="actc-current-hint">{current.hint}</span>
          </div>
          <button type="button" className="actc-cta" onClick={() => onAction && onAction(current.id)}>
            <span>{current.cta}</span><Chevron />
          </button>
        </div>
      ) : null}
    </div>
  )
}

export default ActivationCard
