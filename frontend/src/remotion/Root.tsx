import { Composition, registerRoot } from 'remotion'
import { HeroProduct } from './HeroProduct'

// Remotion CLI registry. Only used at render time (`npm run render:hero*`) — the landing page
// itself ships the rendered .webm/.mp4, not this file.
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
    </>
  )
}

registerRoot(RemotionRoot)
