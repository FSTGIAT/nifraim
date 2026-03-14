import "./index.css";
import { Composition } from "remotion";
import { NifraimCommercial } from "./NifraimCommercial";
import { NifraimMarketing } from "./NifraimMarketing";
import { NifraimTeaser } from "./NifraimTeaser";
import { FoxAnimation } from "./FoxAnimation";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="NifraimCommercial"
        component={NifraimCommercial}
        durationInFrames={950} /* 992 total - 45 overlap ≈ 947 effective */
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="NifraimMarketing"
        component={NifraimMarketing}
        durationInFrames={
          870
        } /* 906 total - 35 overlap (7 transitions × 5 frames) */
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="NifraimTeaser"
        component={NifraimTeaser}
        durationInFrames={240}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
