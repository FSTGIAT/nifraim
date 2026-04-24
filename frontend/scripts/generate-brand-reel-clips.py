#!/usr/bin/env python3
"""
Regenerate the two Luma Ray-2 clips used by the BrandReel composition.

Usage:
    cd frontend
    LUMALABS_API_KEY=... npm run gen:brand-reel-clips
    # or directly:
    LUMALABS_API_KEY=... python3 scripts/generate-brand-reel-clips.py

Output:
    frontend/public/landing/brand-reel/clip-a.mp4   (5s — "Numbers on Paper")
    frontend/public/landing/brand-reel/clip-b.mp4   (5s — "Papers Dissolve into Data",
                                                    chained from clip A's final frame)

Both clips are 5s because Ray-2 only accepts '5s' or '9s'. BrandReel.tsx wraps each in a
<Sequence durationInFrames={120}> so the rendered video only shows the first 4s of each.
"""

from __future__ import annotations
import os
import sys
import time
from pathlib import Path

try:
    import requests
    from lumaai import LumaAI
except ImportError as e:
    sys.stderr.write(
        f"missing dependency: {e.name}\n"
        "install with:  pip install lumaai requests\n"
    )
    sys.exit(1)

OUT_DIR = Path(__file__).resolve().parents[1] / "public" / "landing" / "brand-reel"

PROMPT_A = (
    "Cinematic wide shot, warm sunlit modern Tel Aviv office with cream walls and "
    "light-oak conference table. Four Israeli professionals in their 30s — two men "
    "(one bearded in a button-down shirt, one clean-shaven in a charcoal sweater) and "
    "two women (one with dark wavy hair and thin glasses, one with straight dark hair "
    "in a cream blazer) — urgently working around the table, which is completely "
    "covered with dozens of printed spreadsheets showing rows of financial data: "
    "shekel amounts in large print (₪12,400 · ₪54,300 · ₪89,200), "
    "bold percentages (92%, 78%, 65%, 54%), insurance policy numbers, dates. Hands "
    "move rapidly between stacks, papers slide across the table with slight motion "
    "blur, one person flips through a thick binder, another points at a laptop "
    "spreadsheet while stacking pages. Controlled urgency — numbers everywhere. Warm "
    "natural window light from the left, shallow depth of field, "
    "documentary-photorealistic cinematic style, no visible logos or brand names."
)

PROMPT_B = (
    "Continuation of the same warm Tel Aviv office scene. The printed numbers, shekel "
    "amounts, and percentages on every paper on the table begin to SEPARATE from the "
    "pages — glowing warm-orange digits, characters and data points rise off the "
    "documents like fireflies, forming swirling streams of financial data flowing "
    "through the air. The paper documents gently fade into pale golden light as their "
    "numbers coalesce into a single bright orange-amber data current flowing and "
    "spiraling toward a central point one meter above the table's center. The four "
    "professionals lean back in their chairs, calm wonder on their faces, watching "
    "the transformation. Warm atmospheric dust particles in the light beam. Cream "
    "palette with glowing orange-amber data particles, shallow depth of field, "
    "photorealistic cinematic, the air above the table shimmers with thousands of "
    "floating numbers streaming toward a central glowing point, no visible UI "
    "screens or text labels."
)


def poll_until_done(client: LumaAI, generation_id: str, label: str):
    print(f"[{label}] polling {generation_id}...", flush=True)
    while True:
        g = client.generations.get(id=generation_id)
        state = getattr(g, "state", None)
        if state == "completed":
            print(f"[{label}] completed", flush=True)
            return g
        if state == "failed":
            raise RuntimeError(
                f"[{label}] generation failed: {getattr(g, 'failure_reason', 'unknown')}"
            )
        print(f"[{label}] state={state}, waiting 5s", flush=True)
        time.sleep(5)


def download(url: str, dest: Path):
    # Luma's CDN returns 403 for urllib/requests defaults; spoof a browser UA.
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  -> {dest}  ({size_mb:.1f} MB)", flush=True)


def main() -> int:
    api_key = os.environ.get("LUMALABS_API_KEY")
    if not api_key:
        sys.stderr.write("LUMALABS_API_KEY not set\n")
        return 1

    client = LumaAI(auth_token=api_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[clip-a] creating generation...", flush=True)
    gen_a = client.generations.create(
        prompt=PROMPT_A,
        model="ray-2",
        aspect_ratio="16:9",
        duration="5s",
        resolution="720p",
    )
    done_a = poll_until_done(client, gen_a.id, "clip-a")

    print("[clip-b] creating generation (chained from clip-a)...", flush=True)
    gen_b = client.generations.create(
        prompt=PROMPT_B,
        model="ray-2",
        aspect_ratio="16:9",
        duration="5s",
        resolution="720p",
        keyframes={"frame0": {"type": "generation", "id": gen_a.id}},
    )
    done_b = poll_until_done(client, gen_b.id, "clip-b")

    for label, gen in [("clip-a", done_a), ("clip-b", done_b)]:
        url = getattr(gen.assets, "video", None) if gen.assets else None
        if not url:
            raise RuntimeError(f"[{label}] no video URL in assets: {gen.assets}")
        download(url, OUT_DIR / f"{label}.mp4")

    print("\nAll clips written to:", OUT_DIR)
    print("Next: cd frontend && npm run render:brand-reel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
