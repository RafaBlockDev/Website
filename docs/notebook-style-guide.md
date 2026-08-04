# Notebook style guide

Scope: `src/content/notebook/**`. This does not apply to Research or
Projects, which have their own conventions (case-study structure, formal
abstract/contributions/limitations fields).

The goal of a Notebook entry is to read like an actual investigation,
something you'd find in someone's real working notes, not a tutorial and not
an AI-generated explainer. If a paragraph could be pasted into any other
article about the same topic without changes, cut it or make it specific to
what you actually did.

## Narrative arc

Not mandatory visible headings. Use them as a checklist, not a template to
fill mechanically. Some entries won't need all thirteen.

1. Real motivation: why you were doing this at all
2. Concrete question: what you actually wanted to know
3. What you expected going in
4. Experimental setup
5. Main result
6. Unexpected observation
7. Interpretation (kept separate from the observation itself)
8. Intervention or comparison
9. What did not improve
10. Practical implications
11. Specific limitations
12. Short conclusion
13. References or reproduction notes

## Writing rules

- Open with a real problem or a real decision you had to make. Never open
  with a definition ("Cosine similarity is a metric that...").
- Use first person for decisions, expectations, and mistakes: "I assumed,"
  "I expected," "I was wrong about."
- Keep observation and interpretation visibly separate. State the number,
  then say what you think it means; don't fuse them into one claim.
- Use exact numbers. "MRR rose from 0.818 to 0.831," not "MRR improved
  slightly."
- Every entry needs at least one failure, contradiction, or result you
  couldn't resolve. An entry where everything worked reads as fiction.
- No marketing language and no overreaching conclusions. If the result is
  narrow, say it's narrow.
- Cut these on sight: "in today's world," "X plays a crucial role," "this
  comprehensive guide," "let's dive in," and any sentence that would still
  be true if you swapped in a different topic.
- Don't fragment into too many headings. A run of three or four paragraphs
  under one heading is normal; a heading every paragraph is not.
- Don't restate the same conclusion in three sections. Say it once, well,
  where it belongs (usually the interpretation section and the conclusion,
  not both at length).
- Short, varied paragraph length. Avoid a wall of uniform four-line
  paragraphs.
- Keep the conclusion brief: a few sentences, not a recap of the whole
  piece.
- State uncertainty honestly: what you don't know, what could break the
  result, what a different corpus/model/scale would change.
- No em dashes and no middle dots (·) in prose. Use a period, comma, colon,
  or parentheses instead; picking the right one is part of the editing
  work, not a detail to skip. Long unbroken dashes are one of the more
  obvious tells of AI-generated writing, and this site avoids them
  everywhere, not just in Notebook.

## Visual rules

- Every figure should answer exactly one question. If you can't state that
  question in a sentence, the figure is trying to do too much.
- Quantitative charts: Observable Plot only (`@observablehq/plot`). No other
  charting library, no raw hand-built SVG standing in for a chart. Plot's
  own output *is* SVG under the hood; that's the library, not a violation.
- Exact values: use an HTML `<table>`, not a chart trying to also serve as a
  data table. Charts are for shape and comparison; tables are for numbers
  someone might want to copy.
- Dense secondary evidence (full matrices, full per-query tables, full
  per-k breakdowns) goes inside a native `<details>` element, collapsed by
  default. Never make a large matrix the primary figure.
- Labels must stay readable at mobile width. Check truncation, not just
  desktop.
- Avoid dashboard aesthetics: no gradients, heavy shadows, card grids,
  oversized legends, or decorative color for its own sake. Muted/accent two
  or three-color palettes only, matching the site's existing `paper` /
  `ink` / `accent` tokens.
- Don't add a new charting or visualization dependency for one figure.

## Code rules

- Only include code that explains a method or a decision that isn't obvious
  from prose: a scoring formula, a non-obvious transform, a subtle bug.
- No installation boilerplate, no full import blocks, no unrelated file
  I/O. A four-line function is more useful than forty lines of setup.
- Link to the full experiment/repro instructions instead of inlining
  everything; keep the inline snippet to the part worth reading twice.

## Frontmatter

Required fields per `src/content.config.ts`'s `notebook` collection:
`title`, `date`, `summary`, `tags`, `math`, `draft`. `updatedDate` and
`ogImage` are optional; add `updatedDate` whenever you materially edit a
published entry after its date, not for typo fixes.

- `date` / `updatedDate`: plain `YYYY-MM-DD`, no time component.
- `summary`: one to three factual sentences describing what you tested and
  what you found, not a teaser.
- `tags`: lowercase, kebab-case, specific to the entry (avoid generic tags
  like `ai` or `tech`).
- `math: true` only if the entry actually contains KaTeX. This is currently
  a semantic flag (the layout imports KaTeX's CSS unconditionally), so set
  it accurately for future use rather than for any current effect.
- `draft: true` for anything not ready, including the template file itself.

## Template

Copy `src/content/notebook/_template.mdx`, fill it in, delete the
instructional comments, set `draft: false` when it's ready.
