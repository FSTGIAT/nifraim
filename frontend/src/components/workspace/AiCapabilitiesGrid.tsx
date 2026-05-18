// AiCapabilitiesGrid — 3×3 explainer tiles for the Production tab empty state.
// Mounted as a React island by AiCapabilitiesGridIsland.vue.
//
// Each card renders its own @paper-design/shaders-react `Warp` shader so the
// whole grid feels alive (literal port of the reference prompt). The section
// itself sits on a light cream background to match the rest of the app, which
// is light-themed; the cards layer a translucent black overlay so Hebrew text
// reads at AAA contrast over the colorful shader underneath.
//
// Caveat: 9 simultaneous WebGL contexts is borderline on browser limits — when
// WebGL2 is unavailable (older drivers, headless, low-end mobile) we fall back
// to a CSS gradient per card with the same dark overlay, so layout never breaks.
'use client'

import * as React from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Warp } from '@paper-design/shaders-react'
import {
  Mail,
  UserRound,
  FileText,
  GitCompareArrows,
  Sparkles,
  Workflow,
  Library,
  Film,
  TrendingUp,
  Lightbulb,
} from 'lucide-react'

interface Props {
  webgl?: boolean
}

interface Capability {
  icon: React.ReactNode
  title: string
  body: string
  tip: string
  center?: boolean
}

const ICON_SIZE = 26

const CAPABILITIES: Capability[] = [
  {
    icon: <Mail size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'כתיבת מיילים חכמה',
    body: 'ה-AI מנסח מייל ללקוחות לפי הנתונים בפועל ופותח אותו לעריכה.',
    tip: 'בקש "שלח מייל לחברות שלא שילמו החודש".',
  },
  {
    icon: <UserRound size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'פורטל לקוח חכם',
    body: 'קישור אישי שמאפשר ללקוח לשאול את ה-AI שאלות על התיק שלו 24/7.',
    tip: 'צור קישור, שלח ב-WhatsApp עם סיסמה — והלקוח שואל את ה-AI ישירות.',
  },
  {
    icon: <FileText size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'חילוץ נתונים מ-PDF',
    body: 'העלה הסכם עמלות, ה-AI קורא אותו וממלא את טבלת העמלות אוטומטית.',
    tip: 'גרור PDF לצ\'אט בהשוואת קבצים — השיעורים יתעדכנו לבד.',
  },
  {
    icon: <GitCompareArrows size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'השוואת קבצים עם הסבר',
    body: 'ה-AI מסביר למה לקוחות שילמו פחות החודש ומזהה דפוסים שלא רואים בעין.',
    tip: 'אחרי השוואת קבצים, שאל "מה הסיבות לירידה החודש?".',
  },
  {
    icon: <Sparkles size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'שאל את ה-AI על הנתונים שלך',
    body: 'שיחה חופשית מעל כל הפרודוקציה, הנפרעים, ההיקפים והגיוסים — בעברית.',
    tip: 'שאל "אילו לקוחות חייבים יותר מ-1,000 ש״ח?" וקבל רשימה מיידית.',
    center: true,
  },
  {
    icon: <Workflow size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'אוטומציה לפורטלי חברות',
    body: 'ה-AI מתחבר לבד לפורטלי חברות הביטוח, מטפל ב-OTP ומוריד את הקבצים.',
    tip: 'הזן פרטי גישה פעם אחת — ההורדה החודשית כבר רצה לבד.',
  },
  {
    icon: <Library size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'ספריית ידע AI',
    body: 'כל הנתונים שלך מאוחדים — שאל את ה-AI על כל חברה, מוצר או לקוח.',
    tip: 'פתח את לשונית "ספריית AI" ולחץ על קטגוריה כדי לשאול עליה.',
  },
  {
    icon: <Film size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'תובנות וויזואליות',
    body: 'ה-AI מייצר אנימציות Remotion חיות שמציגות תובנות מורכבות בצורה ויזואלית.',
    tip: 'כשה-AI עונה, פתח את כפתור הסרטון כדי לראות הסבר ויזואלי על התשובה.',
  },
  {
    icon: <TrendingUp size={ICON_SIZE} strokeWidth={1.75} />,
    title: 'מעקב מגמות אוטומטי',
    body: 'כל העלאת קובץ פרודוקציה נשמרת כסנפשוט. צפה במגמות פרמיה וצבירה לאורך זמן.',
    tip: 'פתח פורטל לקוח כלשהו וגלגל ל-"מגמות" כדי לראות את הגרף לאורך זמן.',
  },
]

type ShaderConfig = {
  proportion: number
  softness: number
  distortion: number
  swirl: number
  swirlIterations: number
  shape: 'checks' | 'dots'
  shapeScale: number
  speed: number
  colors: string[]
}

// Nine pastel/luminous palettes — same hue families as before, pushed into
// higher-lightness HSL so the colors read airy and bright instead of muddy.
// Pair with the lifted veil (rgba ~0.22 → 0.55) so each shader breathes.
const SHADER_CONFIGS: ShaderConfig[] = [
  // 0 — Peach (mail)
  {
    proportion: 0.35, softness: 0.95, distortion: 0.16, swirl: 0.7,
    swirlIterations: 9, shape: 'checks', shapeScale: 0.10, speed: 0.6,
    colors: ['hsl(28, 95%, 70%)', 'hsl(20, 100%, 80%)', 'hsl(40, 95%, 78%)', 'hsl(15, 100%, 85%)'],
  },
  // 1 — Soft coral / rose (portal)
  {
    proportion: 0.40, softness: 1.10, distortion: 0.18, swirl: 0.85,
    swirlIterations: 10, shape: 'dots', shapeScale: 0.12, speed: 0.55,
    colors: ['hsl(10, 95%, 72%)', 'hsl(350, 95%, 80%)', 'hsl(20, 100%, 82%)', 'hsl(0, 95%, 86%)'],
  },
  // 2 — Apricot (PDF extraction)
  {
    proportion: 0.32, softness: 0.85, distortion: 0.14, swirl: 0.65,
    swirlIterations: 8, shape: 'checks', shapeScale: 0.11, speed: 0.5,
    colors: ['hsl(15, 85%, 70%)', 'hsl(25, 95%, 78%)', 'hsl(5, 90%, 80%)', 'hsl(20, 100%, 85%)'],
  },
  // 3 — Pink / blush (comparison)
  {
    proportion: 0.42, softness: 1.00, distortion: 0.20, swirl: 0.80,
    swirlIterations: 11, shape: 'dots', shapeScale: 0.10, speed: 0.6,
    colors: ['hsl(330, 95%, 75%)', 'hsl(345, 95%, 82%)', 'hsl(310, 85%, 78%)', 'hsl(320, 100%, 86%)'],
  },
  // 4 — CENTER · luminous gold / amber (chat marquee)
  {
    proportion: 0.45, softness: 1.20, distortion: 0.22, swirl: 0.95,
    swirlIterations: 13, shape: 'checks', shapeScale: 0.09, speed: 0.7,
    colors: ['hsl(38, 95%, 70%)', 'hsl(45, 100%, 78%)', 'hsl(28, 100%, 75%)', 'hsl(48, 100%, 85%)'],
  },
  // 5 — Lavender (automation)
  {
    proportion: 0.38, softness: 1.05, distortion: 0.17, swirl: 0.75,
    swirlIterations: 10, shape: 'dots', shapeScale: 0.11, speed: 0.55,
    colors: ['hsl(258, 85%, 75%)', 'hsl(275, 90%, 82%)', 'hsl(245, 95%, 78%)', 'hsl(285, 95%, 86%)'],
  },
  // 6 — Tangerine sorbet (library)
  {
    proportion: 0.36, softness: 0.90, distortion: 0.16, swirl: 0.75,
    swirlIterations: 9, shape: 'checks', shapeScale: 0.12, speed: 0.55,
    colors: ['hsl(25, 100%, 72%)', 'hsl(35, 100%, 80%)', 'hsl(15, 100%, 76%)', 'hsl(40, 100%, 85%)'],
  },
  // 7 — Sky / aqua (visual insights)
  {
    proportion: 0.40, softness: 1.10, distortion: 0.18, swirl: 0.8,
    swirlIterations: 10, shape: 'dots', shapeScale: 0.10, speed: 0.55,
    colors: ['hsl(190, 90%, 70%)', 'hsl(205, 90%, 80%)', 'hsl(175, 95%, 75%)', 'hsl(195, 100%, 86%)'],
  },
  // 8 — Buttercream gold (trends)
  {
    proportion: 0.34, softness: 0.95, distortion: 0.15, swirl: 0.7,
    swirlIterations: 9, shape: 'checks', shapeScale: 0.11, speed: 0.5,
    colors: ['hsl(45, 90%, 72%)', 'hsl(50, 100%, 80%)', 'hsl(35, 95%, 76%)', 'hsl(55, 100%, 86%)'],
  },
]

export default function AiCapabilitiesGrid({ webgl = true }: Props) {
  const reduce = useReducedMotion()

  return (
    <section dir="rtl" className="aicg-root">
      <header className="aicg-head">
        <h2 className="aicg-title">מה ה-AI במערכת יכול לעשות עבורך?</h2>
      </header>

      <div className="aicg-grid">
        {CAPABILITIES.map((c, i) => {
          const cfg = SHADER_CONFIGS[i % SHADER_CONFIGS.length]
          return (
            <motion.article
              key={i}
              className={'aicg-card' + (c.center ? ' aicg-card--center' : '')}
              initial={reduce ? false : { opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{
                duration: 0.45,
                delay: reduce ? 0 : i * 0.05,
                ease: [0.16, 1, 0.3, 1],
              }}
              whileHover={
                reduce
                  ? undefined
                  : {
                      scale: 1.06,
                      y: -10,
                      zIndex: 2,
                      transition: { type: 'spring', stiffness: 280, damping: 18, mass: 0.8 },
                    }
              }
              whileTap={reduce ? undefined : { scale: 1.03 }}
              style={{ transformOrigin: 'center' }}
            >
              {/* Shader layer (or a CSS gradient fallback when WebGL2 is absent). */}
              <div className="aicg-bg" aria-hidden="true">
                {webgl ? (
                  <Warp
                    style={{ width: '100%', height: '100%' }}
                    proportion={cfg.proportion}
                    softness={cfg.softness}
                    distortion={cfg.distortion}
                    swirl={cfg.swirl}
                    swirlIterations={cfg.swirlIterations}
                    shape={cfg.shape}
                    shapeScale={cfg.shapeScale}
                    scale={1}
                    rotation={0}
                    speed={reduce ? 0 : cfg.speed}
                    colors={cfg.colors}
                  />
                ) : (
                  <div
                    className="aicg-bg-fallback"
                    style={{
                      background: `linear-gradient(135deg, ${cfg.colors[0]} 0%, ${cfg.colors[1]} 45%, ${cfg.colors[3]} 100%)`,
                    }}
                  />
                )}
                {/* Dark veil keeps Hebrew text at AAA contrast on top of any palette. */}
                <div className="aicg-veil" />
              </div>

              <div className="aicg-card-body">
                <div className="aicg-icon" aria-hidden="true">
                  {c.icon}
                </div>
                <h3 className="aicg-card-title">{c.title}</h3>
                <p className="aicg-card-text">{c.body}</p>
                <div className="aicg-tip">
                  <Lightbulb size={14} strokeWidth={2} aria-hidden="true" />
                  <span>{c.tip}</span>
                </div>
              </div>
            </motion.article>
          )
        })}
      </div>
    </section>
  )
}
