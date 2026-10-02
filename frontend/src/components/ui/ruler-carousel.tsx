// Ruler Carousel — a history band: items on an endless ruler. The list is
// tripled so it wraps forever; ticks run along the top and bottom (one per
// item, taller every 5th, the tallest at the centre in the accent colour);
// the strip glides on a CRITICALLY damped spring (stiffness 260, damping 33 —
// the original 20 overshoots and the titles visibly wobble); the active item
// is full size, the rest recede (scale .75, opacity .4).
//
// Adapted for Nifraim (a Vue app, mounted through
// components/calls/RulerCarouselIsland.vue): inline styles instead of
// Tailwind, motion from `framer-motion`, icons from `lucide-react`, and the
// keyboard scoped to the component (it listens only while focused — it
// never takes keys from the app). RTL: the first item sits at the centre and
// the next ones line up to its LEFT, so "next" points left, as in Hebrew.
import { useEffect, useRef, useState } from "react"
import { animate, motion, useMotionValue, useTransform, type MotionValue } from "framer-motion"
import { FastForward, Rewind } from "lucide-react"

export interface RulerItem { id: string; label: string; live?: boolean }
export interface RulerColors { text: string; faint: string; tick: string; accent: string; button: string }
export interface RulerCarouselProps {
  items: RulerItem[]
  active?: number
  onActive?: (index: number) => void
  onOpen?: (index: number, el: HTMLElement | null) => void
  colors?: Partial<RulerColors>
  itemWidth?: number
  gap?: number
  reducedMotion?: boolean
  freshId?: string | null // a just-added item springs in at the centre
}

const DEF: RulerColors = { text: "#181818", faint: "rgba(24,24,24,0.55)", tick: "rgba(24,24,24,0.28)", accent: "#A63A86", button: "rgba(24,24,24,0.06)" }

function Ticks({ n, pos, step, colors, side }: { n: number; pos: MotionValue<number>; step: number; colors: RulerColors; side: "top" | "bottom" }) {
  // one tick per item slot, plus four minor ticks between neighbours
  const marks = []
  for (let k = 0; k < n * 3; k++) {
    for (let m = 0; m < 5; m++) marks.push({ k, m })
  }
  return (
    <div style={{ position: "relative", height: 22, overflow: "hidden" }} aria-hidden="true">
      {marks.map(({ k, m }) => (
        <Tick key={`${k}-${m}`} pos={pos} at={k + m / 5} step={step} major={m === 0} fifth={m === 0 && k % 5 === 0} colors={colors} side={side} />
      ))}
      <span style={{
        position: "absolute", left: "50%", width: 2, marginLeft: -1, height: 22, borderRadius: 2, background: colors.accent,
        [side === "top" ? "bottom" : "top"]: 0,
      }} />
    </div>
  )
}

function Tick({ pos, at, step, major, fifth, colors, side }: {
  pos: MotionValue<number>; at: number; step: number; major: boolean; fifth: boolean; colors: RulerColors; side: "top" | "bottom"
}) {
  const x = useTransform(pos, (p) => Math.round((p - at) * step))
  const h = fifth ? 16 : major ? 11 : 5
  return (
    <motion.span style={{
      position: "absolute", left: "50%", width: 1, height: h, background: colors.tick, x,
      [side === "top" ? "bottom" : "top"]: 0,
    }} />
  )
}

function Item({ item, k, pos, step, width, colors, active, fresh, onClick }: {
  item: RulerItem; k: number; pos: MotionValue<number>; step: number; width: number; colors: RulerColors; active: boolean
  fresh: boolean; onClick: (el: HTMLElement) => void
}) {
  const x = useTransform(pos, (p) => Math.round((p - k) * step - width / 2))
  return (
    <motion.button
      type="button"
      tabIndex={-1}
      data-k={k}
      onClick={(e) => onClick(e.currentTarget)}
      initial={fresh ? { scale: 0.4, opacity: 0, y: -18 } : false}
      animate={{ scale: active ? 1 : 0.75, opacity: active ? 1 : 0.4, y: 0 }}
      transition={fresh ? { type: "spring", stiffness: 260, damping: 33 } : { duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
      style={{
        position: "absolute", left: "50%", top: 0, width, height: "100%", x,
        willChange: "transform", backfaceVisibility: "hidden",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
        padding: "0 10px", border: "none", background: "transparent", cursor: "pointer",
        fontFamily: "Heebo, sans-serif", fontSize: 22, fontWeight: active ? 800 : 600, letterSpacing: "-0.02em",
        color: active ? colors.text : colors.faint, direction: "rtl", borderRadius: 12,
      }}
    >
      {item.live && (
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: colors.accent, flex: "none", animation: "rcPulse 1.4s ease-in-out infinite" }} />
      )}
      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.label}</span>
    </motion.button>
  )
}

export function RulerCarousel({
  items, active = 0, onActive, onOpen, colors: custom, itemWidth = 240, gap = 48, reducedMotion = false, freshId = null,
}: RulerCarouselProps) {
  const colors: RulerColors = { ...DEF, ...(custom || {}) }
  const n = items.length
  const step = itemWidth + gap
  const pos = useMotionValue(n + active) // the middle copy
  const [cur, setCur] = useState(n + active)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const real = n ? ((cur % n) + n) % n : 0

  // report a move to the parent ONLY when the user moved the ruler — never echo a
  // parent-driven change back (that echo, with a stale index after the list grew,
  // made parent and ruler bounce between two items every frame: the "shaking").
  const report = (k: number) => { if (n) onActive?.(((k % n) + n) % n) }
  const go = (target: number) => {
    setCur(target)
    report(target)
    const done = () => {
      // stay inside the middle copy so the ring never runs out
      if (target < n || target >= 2 * n) {
        const wrapped = ((target % n) + n) % n + n
        pos.set(wrapped)
        setCur(wrapped)
      }
    }
    if (reducedMotion) { pos.set(target); done(); return }
    animate(pos, target, { type: "spring", stiffness: 260, damping: 33, restDelta: 0.001 }).then(done)
  }

  // follow the parent (a filter, a new call at the front)
  const lastN = useRef(n)
  useEffect(() => {
    if (!n) return
    // a changed list re-anchors on the middle copy; a changed index only if it differs
    if (lastN.current !== n || active !== real) { pos.stop(); pos.set(n + active); setCur(n + active) }
    lastN.current = n
  }, [active, n]) // eslint-disable-line react-hooks/exhaustive-deps

  const next = () => go(cur + 1)
  const prev = () => go(cur - 1)
  const onKey = (e: React.KeyboardEvent) => {
    // RTL: left = forward (next), right = back
    if (e.key === "ArrowLeft") { e.preventDefault(); next() }
    else if (e.key === "ArrowRight") { e.preventDefault(); prev() }
    else if (e.key === "Enter") {
      e.preventDefault()
      const el = rootRef.current?.querySelector<HTMLElement>(`[data-k="${cur}"]`) || null
      onOpen?.(real, el)
    }
  }

  if (!n) return null
  const triple = [0, 1, 2].flatMap((c) => items.map((it, i) => ({ it, k: c * n + i })))
  const btn: React.CSSProperties = {
    width: 34, height: 34, borderRadius: "50%", border: "none", display: "grid", placeItems: "center",
    background: colors.button, color: colors.text, cursor: "pointer",
  }

  return (
    <div ref={rootRef} tabIndex={0} onKeyDown={onKey} role="listbox" aria-label="היסטוריית שיחות"
         style={{ position: "relative", width: "100%", outline: "none", fontFamily: "Heebo, sans-serif", direction: "ltr" }}>
      <style>{"@keyframes rcPulse{50%{opacity:.25;transform:scale(.8)}}"}</style>
      <Ticks n={n} pos={pos} step={step} colors={colors} side="top" />
      <div style={{ position: "relative", height: 64, overflow: "hidden",
                    maskImage: "linear-gradient(to right, transparent, #000 14%, #000 86%, transparent)",
                    WebkitMaskImage: "linear-gradient(to right, transparent, #000 14%, #000 86%, transparent)" }}>
        {triple.map(({ it, k }) => (
          <Item key={`${k}:${it.id}`} item={it} k={k} pos={pos} step={step} width={itemWidth} colors={colors} active={k === cur}
                fresh={!reducedMotion && !!freshId && it.id === freshId && k === n + active}
                onClick={(el) => { if (k === cur) onOpen?.(real, el); else go(k) }} />
        ))}
      </div>
      <Ticks n={n} pos={pos} step={step} colors={colors} side="bottom" />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, marginTop: 10, direction: "rtl" }}>
        <button type="button" style={btn} onClick={prev} aria-label="הקודמת">
          <Rewind size={16} style={{ transform: "scaleX(-1)" }} />
        </button>
        <span style={{ fontSize: 13, fontWeight: 700, color: colors.faint, minWidth: 54, textAlign: "center", direction: "ltr", fontVariantNumeric: "tabular-nums" }}>
          {real + 1} / {n}
        </span>
        <button type="button" style={btn} onClick={next} aria-label="הבאה">
          <FastForward size={16} style={{ transform: "scaleX(-1)" }} />
        </button>
      </div>
    </div>
  )
}

export default RulerCarousel
