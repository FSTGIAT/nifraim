import { AbsoluteFill } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { fontFamily, FADE_FRAMES } from './constants/tokens';

import { BrandIntro } from './scenes/BrandIntro';
import { UploadInsightsScene } from './scenes/UploadInsightsScene';
import { FileComparisonScene } from './scenes/FileComparisonScene';
import { CommissionDashboardScene } from './scenes/CommissionDashboardScene';
import { CustomerPortalScene } from './scenes/CustomerPortalScene';
import { MetricsCTAOutro } from './scenes/MetricsCTAOutro';
import { ChapterTitle } from './components/ChapterTitle';

// Chapter title cards shown before each feature scene
const ChapterUpload = () => <ChapterTitle title="העלאה ותובנות" subtitle="קובץ אחד — כל התמונה" />;
const ChapterComparison = () => <ChapterTitle title="השוואת קבצים" subtitle="זיהוי שינויים אוטומטי" />;
const ChapterCommission = () => <ChapterTitle title="ניתוח עמלות" subtitle="בקרה מול נפרעים" />;
const ChapterPortal = () => <ChapterTitle title="פורטל לקוחות" subtitle="DASHBOARD אישי לכל לקוח" />;

const scenes = [
  { id: 'brand-intro', Component: BrandIntro, duration: 100 },
  { id: 'ch-upload', Component: ChapterUpload, duration: 48 },
  { id: 'upload-insights', Component: UploadInsightsScene, duration: 120 },
  { id: 'ch-comparison', Component: ChapterComparison, duration: 48 },
  { id: 'file-comparison', Component: FileComparisonScene, duration: 120 },
  { id: 'ch-commission', Component: ChapterCommission, duration: 48 },
  { id: 'commission-dashboard', Component: CommissionDashboardScene, duration: 120 },
  { id: 'ch-portal', Component: ChapterPortal, duration: 48 },
  { id: 'customer-portal', Component: CustomerPortalScene, duration: 120 },
  { id: 'metrics-cta', Component: MetricsCTAOutro, duration: 220 },
];

const fadeTransition = {
  presentation: fade(),
  timing: linearTiming({ durationInFrames: FADE_FRAMES }),
};

export const NifraimCommercial: React.FC = () => {
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
