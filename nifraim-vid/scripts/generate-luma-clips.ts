/**
 * Luma Dream Machine clip generator for Nifraim marketing video.
 *
 * Generates two AI clips:
 *   - Intro (~5s): Abstract data streams / insurance visuals in orange-dark tones
 *   - Outro (~5s): Golden particles converging into light, premium feel
 *
 * Usage:
 *   LUMALABS_API_KEY=<key> npx tsx scripts/generate-luma-clips.ts
 */

import LumaAI from 'lumaai';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const POLL_INTERVAL_MS = 5_000;
const MAX_POLLS = 120; // 10 minutes max

const API_KEY = process.env.LUMALABS_API_KEY;
if (!API_KEY) {
  console.error('Error: LUMALABS_API_KEY environment variable is required');
  process.exit(1);
}

const client = new LumaAI({ authToken: API_KEY });

const clips = [
  {
    name: 'luma-intro',
    prompt:
      'Elegant slow-motion macro shot of translucent glass documents and data cards floating weightlessly through soft ambient light. Subtle warm amber and cream tones on a deep navy dark background. Clean corporate aesthetic, shallow depth of field, gentle bokeh. Smooth dolly forward camera movement. Cinematic, premium, minimalist. 5 seconds.',
    outputFile: 'luma-intro.mp4',
  },
  {
    name: 'luma-outro',
    prompt:
      'Slow cinematic pull-back revealing an elegant dark marble desk with soft warm light casting long shadows. A single glowing amber accent light reflects on polished surfaces. Premium corporate atmosphere, muted warm tones, deep shadows. Luxurious and understated. Smooth camera movement. 5 seconds.',
    outputFile: 'luma-outro.mp4',
  },
];

async function pollUntilDone(id: string): Promise<string> {
  for (let i = 0; i < MAX_POLLS; i++) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

    const generation = await client.generations.get(id);
    console.log(`  Poll ${i + 1}: state=${generation.state}`);

    if (generation.state === 'completed') {
      const videoUrl = generation.assets?.video;
      if (!videoUrl) throw new Error('Completed but no video URL');
      return videoUrl;
    }

    if (generation.state === 'failed') {
      throw new Error(`Generation failed: ${generation.failure_reason || 'unknown'}`);
    }
  }

  throw new Error('Timed out waiting for generation');
}

async function downloadVideo(url: string, outputPath: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download error (${res.status})`);
  const buffer = Buffer.from(await res.arrayBuffer());
  writeFileSync(outputPath, buffer);
  console.log(`  Saved: ${outputPath} (${(buffer.length / 1024 / 1024).toFixed(1)} MB)`);
}

async function main() {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const publicDir = join(__dirname, '..', 'public');
  if (!existsSync(publicDir)) mkdirSync(publicDir, { recursive: true });

  for (const clip of clips) {
    console.log(`\nGenerating "${clip.name}"...`);
    console.log(`  Prompt: ${clip.prompt.slice(0, 80)}...`);

    const generation = await client.generations.create({
      model: 'ray-2',
      aspect_ratio: '16:9',
      prompt: clip.prompt,
    });
    console.log(`  Created generation: ${generation.id} (state: ${generation.state})`);

    const videoUrl = await pollUntilDone(generation.id!);
    await downloadVideo(videoUrl, join(publicDir, clip.outputFile));

    console.log(`  Done: ${clip.name}`);
  }

  console.log('\nAll clips generated successfully!');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
