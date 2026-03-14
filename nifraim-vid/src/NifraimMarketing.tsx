import { AbsoluteFill } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { fontFamily, FADE_FRAMES } from './constants/tokens';

import { LumaIntroScene } from './scenes/LumaIntroScene';
import { MarketingBrandIntro } from './scenes/MarketingBrandIntro';
import { UploadInsightsScene } from './scenes/UploadInsightsScene';
import { MarketingComparisonScene } from './scenes/MarketingComparisonScene';
import { MarketingPortalScene } from './scenes/MarketingPortalScene';
import { LumaOutroScene } from './scenes/LumaOutroScene';
import { ChapterTitle } from './components/ChapterTitle';

const ChapterUpload = () => <ChapterTitle title="העלאה ותובנות" subtitle="קובץ אחד — כל התמונה" />;
const ChapterComparison = () => <ChapterTitle title="השוואה וניתוח" subtitle="זיהוי פערים אוטומטי" />;

const scenes = [
  { id: 'luma-intro', Component: LumaIntroScene, duration: 150 },
  { id: 'brand-intro', Component: MarketingBrandIntro, duration: 90 },
  { id: 'ch-upload', Component: ChapterUpload, duration: 48 },
  { id: 'upload-insights', Component: UploadInsightsScene, duration: 120 },
  { id: 'ch-comparison', Component: ChapterComparison, duration: 48 },
  { id: 'marketing-comparison', Component: MarketingComparisonScene, duration: 150 },
  { id: 'marketing-portal', Component: MarketingPortalScene, duration: 120 },
  { id: 'luma-outro', Component: LumaOutroScene, duration: 180 },
];

const fadeTransition = {
  presentation: fade(),
  timing: linearTiming({ durationInFrames: FADE_FRAMES }),
};

export const NifraimMarketing: React.FC = () => {
  return (
    <AbsoluteFill style={{ fontFamily, direction: 'rtl', background: '#0d0d0d' }}>
      <TransitionSeries>
        {scenes.map((scene, i) => {
          const elements = [];
          elements.push(
            <TransitionSeries.Sequence
              key={scene.id}
              durationInFrames={scene.duration}
            >
              <scene.Component />
            </TransitionSeries.Sequence>,
          );
          if (i < scenes.length - 1) {
            elements.push(
              <TransitionSeries.Transition
                key={`t-${scene.id}`}
                presentation={fadeTransition.presentation}
                timing={fadeTransition.timing}
              />,
            );
          }
          return elements;
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
