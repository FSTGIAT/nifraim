# brand-reel/

Luma Ray-2 source clips for the 3-beat BrandReel composition.

| File | Content | Duration |
|---|---|---|
| `clip-a.mp4` | "Numbers on Paper" — four people urgently working with numbered spreadsheets | 5s (only first 4s used) |
| `clip-b.mp4` | "Papers Dissolve into Data" — chained from clip A, numbers lift off as orange particles | 5s (only first 4s used) |

Committed to git (1–3 MB each) so the render is reproducible without a Luma API call. Regenerate with:

```bash
cd frontend
LUMALABS_API_KEY=... npm run gen:brand-reel-clips
```

Then re-render the final 12s video:

```bash
npm run render:brand-reel   # writes public/landing/brand-reel.mp4
```
