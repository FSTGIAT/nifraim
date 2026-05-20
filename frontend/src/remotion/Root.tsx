import { Composition, registerRoot } from 'remotion'
import { HeroProduct } from './HeroProduct'
import { HeroMesh } from './landing/HeroMesh'
import { Feature01AutoLoad } from './landing/Feature01AutoLoad'
import { Feature02Agreements } from './landing/Feature02Agreements'
import { Feature03Audit } from './landing/Feature03Audit'
import { Feature04Insights } from './landing/Feature04Insights'
import { Feature05AiDiagram } from './landing/Feature05AiDiagram'
import { AutomationIntro, AUTOMATION_INTRO_DURATION } from './AutomationIntro'

// Remotion CLI registry. Only used at render time (`npm run render:hero*`, `render:feature-*`)
// — the landing page itself ships the rendered .webm/.mp4, not these components.

// Shared dimensions for the 5 Chapter-04 feature mini-clips (16:9 to match card aspect).
const FEATURE = { durationInFrames: 90, fps: 30, width: 1376, height: 768 } as const

const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="hero-product"
        component={HeroProduct}
        durationInFrames={120}
        fps={30}
        width={1024}
        height={1280}
      />
      <Composition
        id="hero-mesh"
        component={HeroMesh}
        durationInFrames={180}
        fps={30}
        width={1024}
        height={1280}
      />
      <Composition id="feature-01-autoload" component={Feature01AutoLoad} {...FEATURE} />
      <Composition id="feature-02-agreements" component={Feature02Agreements} {...FEATURE} />
      <Composition id="feature-03-audit" component={Feature03Audit} {...FEATURE} />
      <Composition id="feature-04-insights" component={Feature04Insights} {...FEATURE} />
      <Composition id="feature-05-ai" component={Feature05AiDiagram} {...FEATURE} />
      <Composition
        id="automation-intro"
        component={AutomationIntro}
        durationInFrames={AUTOMATION_INTRO_DURATION}
        fps={30}
        width={1080}
        height={600}
      />
    </>
  )
}

registerRoot(RemotionRoot)
