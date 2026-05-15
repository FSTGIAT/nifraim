// React island — WebGL shaders ONLY. Hebrew content (headline, CTAs) lives
// in ShaderHeroIsland.vue so it always renders even when WebGL is unavailable.
// This module is only mounted when WebGL2 is verified available.
import { MeshGradient } from '@paper-design/shaders-react'
import React from 'react'

// Silence dev-only React warnings from @paper-design/shaders-react 0.0.76.
// The library spreads its API props (backgroundColor, spotsPerColor, wireframe,
// etc.) onto the underlying <div>, which React doesn't recognize as DOM attrs.
// Stripped from production builds anyway — this just keeps the dev console clean.
if (typeof window !== 'undefined' && import.meta.env?.DEV) {
  const ORIGINAL_ERROR = console.error
  const SUPPRESSED = [
    'does not recognize the `backgroundColor`',
    'does not recognize the `spotsPerColor`',
    'Received `true` for a non-boolean attribute `wireframe`',
  ]
  console.error = (...args: unknown[]) => {
    const first = args[0]
    if (typeof first === 'string' && SUPPRESSED.some((p) => first.includes(p))) return
    ORIGINAL_ERROR(...args)
  }
}

// Nifraim-tinted demo palette: brand orange replaces brown.
const SHADER_COLORS_MAIN = ['#000000', '#E8660A', '#ffffff', '#3E2723', '#5D4037']
const SHADER_COLORS_WIRE = ['#000000', '#ffffff', '#E8660A', '#000000']

// Tiny error boundary so a shader runtime error doesn't blank the hero.
class ShaderBoundary extends React.Component<
  { children: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error('[ShaderHero] shader crashed, falling back to gradient', error)
  }
  render() {
    if (this.state.failed) return null
    return this.props.children
  }
}

function ShaderBackground() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      <MeshGradient
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
        colors={SHADER_COLORS_MAIN}
        speed={0.3}
        backgroundColor="#000000"
      />
      <MeshGradient
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          opacity: 0.6,
        }}
        colors={SHADER_COLORS_WIRE}
        speed={0.2}
        // String literal `"true"` — matches the upstream demo. Passing a JS
        // boolean here triggers a React warning because the lib forwards the
        // prop to the underlying <div>.
        wireframe={'true' as unknown as boolean}
        backgroundColor="transparent"
      />
    </div>
  )
}

export default function ShaderHero() {
  return (
    <ShaderBoundary>
      <ShaderBackground />
    </ShaderBoundary>
  )
}
