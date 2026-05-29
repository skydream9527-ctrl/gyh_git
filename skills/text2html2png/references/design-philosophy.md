# Design Philosophy

These charts are screenshots — static images people paste into docs, Slack, presentations. Unlike web pages, the viewer can't scroll or interact. This means every pixel matters: wasted space is permanently wasted, unclear hierarchy can't be rescued by hovering, and visual inconsistency can't be fixed by resizing the browser.

## First Principle: Compact, Symmetric, Full

This is the **highest priority rule** that overrides all other layout decisions.

Why these three? Because the output is a fixed-size image. Loose spacing that looks "airy" on a web page becomes "empty and unprofessional" in a screenshot pasted into a doc. Asymmetric layouts that feel "dynamic" on screen become "messy and hard to parse" when you can't interact with them. Missing content creates dead zones that make people wonder if the image loaded correctly.

1. **Compact** — Elements pack tightly. Card-to-card gaps stay minimal. The chart looks dense and solid, not scattered with air pockets. When 8px works, don't use 12px. Why: users paste these into documents where space is precious. A compact chart communicates "this person organized their thoughts well."
2. **Symmetric** — Cards in the same row are equal width. Left-right balance. Visual center of gravity stays in the middle. No 70/30 column splits, no one-big-one-small. Why: symmetric layout lets the reader's eye scan predictably — they know where to look next without thinking.
3. **Full** — Every area of the chart carries content. No visible "empty zones". If content is sparse, proactively enrich it (add descriptions, stats, summary banners) to fill the chart. Why: empty zones in a static image look like bugs, not design choices.

**When to break this rule**: Only when **content semantics** require it — NOT because of style preference. For example:
- A timeline naturally alternates left/right → acceptable asymmetry, but still compact and full
- A single metric needs emphasis → can be larger, but surrounding area must still be filled
- Style (editorial, neon, etc.) does NOT override this principle — styles control colors, fonts, and effects, not layout structure

## Visual Identity

Every chart should have a clear visual identity. Choose a bold aesthetic direction for colors, typography, and effects — but always within the compact-symmetric-full framework. Why: when all charts look the same, none of them are memorable. A distinctive visual identity makes the reader feel "someone designed this for me" rather than "a tool generated this."

---

## Typography

**Avoid generic fonts** (Inter, Roboto, Arial, Helvetica, system-ui as standalone). Why: these are the default choices of every AI tool and template generator. When someone sees Inter + white background + purple accent, they immediately think "ChatGPT made this." A distinctive font is the single easiest way to make a chart look human-designed.

**Each style has its own font pairing** — a distinctive display font + a refined body font. See individual style files for specifics. Why: font pairing creates visual rhythm — the contrast between a decorative title font and a clean body font signals intentional design.

**Font loading**: Use Google Fonts via `<link>` in HTML `<head>`. Always include appropriate CJK font for Chinese content. Why: system fonts render differently across OS/browser. Google Fonts ensures the chart looks the same everywhere, which matters since the output is a screenshot.

**Hierarchy rules**:
- Main title > Subtitle > Card title > Body text > Auxiliary text
- Font sizes must decrease progressively, no skipping levels
- Title: bold/black weight; body: regular/medium; auxiliary: light or muted color
- Why: clear hierarchy tells the reader what to read first, second, third. Without it, all text competes for attention and the chart becomes noise.

**Title alignment**: Main title and subtitle center-aligned (`text-align: center`). Why: these charts are standalone screenshots, not part of a web page. A centered title makes the image feel like a complete poster or card — it has a clear visual axis. A left-aligned title makes it look like a fragment cropped from a longer document.

---

## Color

**Dominant + Accent pattern**:
- Pick 1 dominant color that sets the tone
- Pick 1-2 sharp accent colors for highlights, CTAs, key metrics
- Never distribute colors evenly — one color must clearly dominate
- Why: evenly distributed colors create a rainbow effect where nothing stands out. A dominant color gives the chart a "mood" and makes accent colors pop as visual anchors for key information.

**Restraint**:
- Max 3-4 primary colors per chart (not counting shades/tints)
- Use same-family shades for secondary elements
- Semantic colors (success/warning/error) should be subtle unless the chart is specifically about status
- Why: every new color is a new "category" the reader has to decode. More than 4 and they stop trying.

**Contrast**:
- Text on colored backgrounds must pass WCAG AA (4.5:1 ratio minimum)
- Key information should never be conveyed by color alone — use weight, size, or icons as backup
- Why: these charts get pasted into all kinds of contexts — projected in bright rooms, printed in grayscale, viewed by colorblind colleagues. Accessible contrast ensures the chart works everywhere.

---

## Layout

**All styles follow the same layout principle**: compact, symmetric, full.

Style only controls visual appearance (colors, fonts, textures, effects) — NOT layout structure.

**Layout rules (universal)**:
- All cards same width within a row (`flex: 1`)
- Equal spacing between elements
- Centered alignment for headers and banners
- Grid-based composition
- No unequal column splits (no 70/30, no 60/40) unless content semantics demand it

**When content requires asymmetry** (rare):
- Timelines: left-right alternation is inherent to the chart type, not a style choice
- Dashboard with one hero metric: the hero can be wider, but remaining cards must fill the row
- Even in these cases, the overall chart must still look dense and full — no empty zones

---

## Spacing & Density

**Compact first — use the minimum spacing that maintains readability.** Why these specific values? They come from testing: below these minimums, borders start touching and text crowds; above these maximums, the chart starts looking like a web page with too much whitespace for a static image.

| Element | Target | Max | Note |
|---------|--------|-----|------|
| body padding | 20-24px | 28px | Prefer 20px when content is dense |
| Card gap | 8px | 12px | Default to 8px, only use 10-12px if cards have borders that crowd |
| Card internal padding | 12-14px | 18px | Keep cards tight internally |
| Title → first content | 10-12px | 14px | Title is part of the content, not floating above it |
| Stats row → main content | 8-10px | 12px | Stats and content are one unit |
| Arrow/connector height | 20-24px | 28px | Arrows are transitions, not breathing room |
| Bottom banner → last content | 8-10px | 12px | Banner hugs the content |

**Anti-patterns**:
- Visible empty space > 20px between content blocks → too loose
- body padding > card gap → feels like content is swimming in a frame
- "Breathing room" used as justification for large gaps → compact IS the breathing room

---

## Connectors & Labels

Connectors (arrows, lines) show relationships between elements. They are the structural backbone of any chart — without them, the reader can't understand the flow.

**Priority order** (when space is tight, sacrifice lower priorities first):
1. **Connection line + arrowhead** — must always be complete and visible. Never omit or clip an arrow.
2. **Label position** — place labels beside the connector (left/right or above), not overlapping the line. If a label sits on top of an arrow, it obscures the connection it's describing.
3. **Label presence** — if there's genuinely no room for a label without crowding, omit it. The information can go in the node's description instead.

**Implementation**:
- Arrows and labels should be separate elements, not crammed into a single SVG where they compete for pixels
- Use `min-height` + `padding` on connector containers, not fixed `height` — let content decide the space
- Labels use small font (9-10px), muted color, positioned adjacent to the arrow rather than overlapping it

This applies to all chart types that use connectors: architecture, flowchart, org-chart, timeline.

---

## Visual Details

**Backgrounds**: Add subtle texture, gradient, or pattern rather than flat solid colors. Why: a flat #ffffff background makes the chart look like a wireframe or draft. Even a tiny amount of texture (paper grain, radial gradient) signals "this is a finished design."
- warm: slight paper-like grain
- dark: subtle radial gradient from center
- editorial: off-white with faint geometric pattern
- neon: deep gradient mesh
- paper: visible paper texture
- glass: layered gradient with blur

**Borders & Shadows**:
- All cards within one chart must have identical border-radius and shadow depth
- Border thickness must be uniform (1px or 1.5px, pick one per chart)
- Shadows should be subtle — `0 1px 3px rgba(0,0,0,0.1)` level, not dramatic
- Why: inconsistent borders/shadows make the chart look like it was assembled from different templates. Uniformity signals "one designer made this."

**Icons & Decorators**:
- Use emoji or simple SVG icons to add visual interest to card headers
- One icon style per chart (don't mix emoji and SVG)
- Icons should support comprehension, not just decorate
- Why: an icon next to a card title helps the reader scan — they recognize the icon faster than reading the text. But mixing styles (emoji here, SVG there) creates visual noise.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | What to Do Instead |
|--------------|-------------|-------------------|
| tagline + banner 内容重复 | 像复读机，浪费空间 | 根据内容判断：丰富内容 → 两个都用但内容不同（tagline 点题，banner 总结升华）；只有一个核心观点 → 只保留一个，不要为了填模板而重复 |
| Rainbow colors | No hierarchy, looks like a toy | Dominant + 1-2 accents |
| Equal-sized everything | — | This is actually GOOD — symmetric equal cards are the default. Only vary sizes when content demands it. |
| Excessive drop shadows | Dated, heavy | Subtle or no shadows |
| Rounded corners > 16px | Looks childish | 8-12px for cards, 4-6px for small elements |
| All-caps body text | Hard to read | Reserve all-caps for short labels only |
| Generic gradient backgrounds | Screams "template" | Style-specific texture/pattern |
| Centering everything | Body text reads better left-aligned | Left-align body text, center titles/stats/banners |
