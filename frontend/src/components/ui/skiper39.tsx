"use client";

import { gsap } from "gsap";
import React, { useEffect, useRef } from "react";

// Nifraim notes (2026-09-29):
// - No Tailwind in this app → the original classes became inline styles.
// - `ink` recolours the sprite's black line art (white fills stay), so the
//   crowd wears the host surface's colour (Mail Agent = #2F6C94).
// - `exclude` drops sprite cells by index (e.g. the peeps holding a knife).
// - The sprite is vendored (assets/crowd/open-peeps.png — Open Peeps, CC0),
//   not hot-linked, and the loop stops under prefers-reduced-motion.

interface CrowdCanvasProps {
  src: string;
  rows?: number;
  cols?: number;
  ink?: string;
  exclude?: number[];
  scale?: number;      // peep size vs. the sprite cell (the original draws them 1:1)
  maxCrowd?: number;   // how many walk at once (the original walks ALL of them)
  style?: React.CSSProperties;
}

function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || "");
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : null;
}

/** Black lines → ink; light fills stay light. One pass on an offscreen canvas. */
function tintSprite(img: HTMLImageElement, ink: string): CanvasImageSource {
  const rgb = hexToRgb(ink);
  if (!rgb) return img;
  const c = document.createElement("canvas");
  c.width = img.naturalWidth;
  c.height = img.naturalHeight;
  const x = c.getContext("2d");
  if (!x) return img;
  x.drawImage(img, 0, 0);
  const d = x.getImageData(0, 0, c.width, c.height);
  const p = d.data;
  for (let i = 0; i < p.length; i += 4) {
    if (!p[i + 3]) continue;
    const l = (p[i] + p[i + 1] + p[i + 2]) / 765; // 0 = line, 1 = fill
    p[i] = rgb[0] + (255 - rgb[0]) * l;
    p[i + 1] = rgb[1] + (255 - rgb[1]) * l;
    p[i + 2] = rgb[2] + (255 - rgb[2]) * l;
  }
  x.putImageData(d, 0, 0);
  return c;
}

const CrowdCanvas = ({ src, rows = 15, cols = 7, ink, exclude = [], scale = 1, maxCrowd = Infinity, style }: CrowdCanvasProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const config = { src, rows, cols };

    // UTILS
    const randomRange = (min: number, max: number) => min + Math.random() * (max - min);
    const randomIndex = (array: any[]) => randomRange(0, array.length) | 0;
    const removeFromArray = (array: any[], i: number) => array.splice(i, 1)[0];
    const removeItemFromArray = (array: any[], item: any) => removeFromArray(array, array.indexOf(item));
    const removeRandomFromArray = (array: any[]) => removeFromArray(array, randomIndex(array));
    const getRandomFromArray = (array: any[]) => array[randomIndex(array) | 0];

    // TWEEN FACTORIES
    const resetPeep = ({ stage, peep }: { stage: any; peep: any }) => {
      const direction = Math.random() > 0.5 ? 1 : -1;
      // depth spread in the original's px, scaled with the peeps (else small peeps float mid-air)
      const offsetY = (100 - 250 * gsap.parseEase("power2.in")(Math.random())) * scale;
      const startY = stage.height - peep.height + offsetY;
      let startX: number;
      let endX: number;

      if (direction === 1) {
        startX = -peep.width;
        endX = stage.width;
        peep.scaleX = 1;
      } else {
        startX = stage.width + peep.width;
        endX = 0;
        peep.scaleX = -1;
      }

      peep.x = startX;
      peep.y = startY;
      peep.anchorY = startY;

      return { startX, startY, endX };
    };

    const normalWalk = ({ peep, props }: { peep: any; props: any }) => {
      const { startX, startY, endX } = props;
      const xDuration = 10;
      const yDuration = 0.25;

      const tl = gsap.timeline();
      tl.timeScale(randomRange(0.5, 1.5));
      tl.to(peep, { duration: xDuration, x: endX, ease: "none" }, 0);
      tl.to(peep, { duration: yDuration, repeat: xDuration / yDuration, yoyo: true, y: startY - 10 }, 0);
      void startX;
      return tl;
    };

    const walks = [normalWalk];

    type Peep = {
      image: CanvasImageSource;
      rect: number[];
      width: number;
      height: number;
      x: number;
      y: number;
      anchorY: number;
      scaleX: number;
      walk: any;
      setRect: (rect: number[]) => void;
      render: (ctx: CanvasRenderingContext2D) => void;
    };

    const createPeep = ({ image, rect }: { image: CanvasImageSource; rect: number[] }): Peep => {
      const peep: Peep = {
        image,
        rect: [],
        width: 0,
        height: 0,
        x: 0,
        y: 0,
        anchorY: 0,
        scaleX: 1,
        walk: null,
        setRect: (r: number[]) => {
          peep.rect = r;
          peep.width = r[2] * scale;
          peep.height = r[3] * scale;
        },
        render: (c: CanvasRenderingContext2D) => {
          c.save();
          c.translate(peep.x, peep.y);
          c.scale(peep.scaleX, 1);
          c.drawImage(peep.image, peep.rect[0], peep.rect[1], peep.rect[2], peep.rect[3], 0, 0, peep.width, peep.height);
          c.restore();
        },
      };
      peep.setRect(rect);
      return peep;
    };

    // MAIN
    const img = document.createElement("img");
    const stage = { width: 0, height: 0 };
    const allPeeps: Peep[] = [];
    const availablePeeps: Peep[] = [];
    const crowd: Peep[] = [];
    let alive = true;

    const createPeeps = (sheet: CanvasImageSource) => {
      const { naturalWidth: width, naturalHeight: height } = img;
      const total = config.rows * config.cols;
      const rectWidth = width / config.rows;
      const rectHeight = height / config.cols;
      const skip = new Set(exclude);
      for (let i = 0; i < total; i++) {
        if (skip.has(i)) continue;
        allPeeps.push(
          createPeep({
            image: sheet,
            rect: [(i % config.rows) * rectWidth, ((i / config.rows) | 0) * rectHeight, rectWidth, rectHeight],
          }),
        );
      }
    };

    const removePeepFromCrowd = (peep: Peep) => {
      removeItemFromArray(crowd, peep);
      availablePeeps.push(peep);
    };

    const addPeepToCrowd = (): Peep => {
      const peep = removeRandomFromArray(availablePeeps);
      const walk = getRandomFromArray(walks)({ peep, props: resetPeep({ peep, stage }) }).eventCallback(
        "onComplete",
        () => {
          removePeepFromCrowd(peep);
          addPeepToCrowd();
        },
      );
      peep.walk = walk;
      crowd.push(peep);
      crowd.sort((a, b) => a.anchorY - b.anchorY);
      return peep;
    };

    const initCrowd = () => {
      while (availablePeeps.length && crowd.length < maxCrowd) {
        addPeepToCrowd().walk.progress(Math.random());
      }
    };

    const render = () => {
      if (!canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.scale(devicePixelRatio, devicePixelRatio);
      crowd.forEach((peep) => peep.render(ctx));
      ctx.restore();
    };

    const resize = () => {
      if (!canvas) return;
      stage.width = canvas.clientWidth;
      stage.height = canvas.clientHeight;
      canvas.width = stage.width * devicePixelRatio;
      canvas.height = stage.height * devicePixelRatio;
      crowd.forEach((peep) => peep.walk.kill());
      crowd.length = 0;
      availablePeeps.length = 0;
      availablePeeps.push(...allPeeps);
      initCrowd();
    };

    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    const init = () => {
      if (!alive) return;
      createPeeps(ink ? tintSprite(img, ink) : img);
      resize();
      if (reduced) {
        crowd.forEach((peep) => peep.walk.pause());
        render();
        return;
      }
      gsap.ticker.add(render);
    };

    img.onload = init;
    img.src = config.src;

    const handleResize = () => resize();
    window.addEventListener("resize", handleResize);

    return () => {
      alive = false;
      window.removeEventListener("resize", handleResize);
      gsap.ticker.remove(render);
      crowd.forEach((peep) => {
        if (peep.walk) peep.walk.kill();
      });
    };
  }, [src, rows, cols, ink, scale, maxCrowd]);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: "absolute", bottom: 0, height: "90vh", width: "100%", ...style }}
    />
  );
};

const Skiper39 = ({ src }: { src: string }) => {
  return (
    <div style={{ position: "relative", height: "100%", width: "100%", background: "#fff", color: "#000" }}>
      <div style={{ position: "absolute", bottom: 0, height: "100%", width: "100%" }}>
        <CrowdCanvas src={src} rows={15} cols={7} />
      </div>
    </div>
  );
};

export { CrowdCanvas, Skiper39 };
export default Skiper39;

/**
 * Skiper 39 Canvas_Landing_004 — React + Canvas
 * Inspired by and adapted from https://codepen.io/zadvorsky/pen/xxwbBQV
 * illustration by https://www.openpeeps.com/
 * We respect the original creators. This is an inspired rebuild with our own taste and does not claim any ownership.
 * These animations aren't associated with the codepen.io . They're independent recreations meant to study interaction design
 *
 * License & Usage:
 * - Free to use and modify in both personal and commercial projects.
 * - Attribution to Skiper UI is required when using the free version.
 * - No attribution required with Skiper UI Pro.
 *
 * Author: @gurvinder-singh02
 * Website: https://gxuri.me
 * Twitter: https://x.com/Gur__vi
 */
