# Nifraim — Design System MASTER

> Read by the `ui-ux-pro-max` skill's Master + Overrides convention. **The full, authoritative
> rules live in the project skill `.claude/skills/nifraim-style/SKILL.md` — load it.** This file
> is the short form so any design skill picks up the project palette instead of inventing one.

- **Product**: on-prem enterprise insurance reconciliation dashboard. Hebrew, RTL, Heebo font.
- **Style**: calm, flat, precise; colour by *category* (per-tab identity), not by brand. No
  glassmorphism, no gradients on buttons, no emoji icons (inline Lucide-style SVGs).
- **Tokens**: `frontend/src/App.vue :root` — always use them.
- **Action colour**: inside a tab → that tab's `--tab-*` colour (`--tab-*-ink` for text/solid bg);
  outside tabs → ink `--primary` #181818.
- **ORANGE IS RETIRED (2026-09-26)** — never `#F57C00`/`#FF9800`/`#E65100` or any orange/amber
  stand-in. Do not recommend an orange palette for this project, whatever the product-type search says.
- **Semantic**: success `--green` #2E844A · error `--red` · warning `--amber` (warnings only).
- **Data / decoration**: `CHART_PALETTE` (`frontend/src/utils/chartPalette.js`, `--chart-1..15`).
- **Contrast**: text ≥ 4.5:1 on its background.

Page overrides: `design-system/pages/<page>.md` (none yet).
