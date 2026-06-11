# Definition Popup — Scope Document

## Objective
When a user clicks (or hovers over) a defined term in any section’s body text, a popup appears showing the definition text extracted from the relevant dictionary section. Clicking inside the popup navigates to the dictionary section itself.

## Current State
- **Backend** already links defined terms in markdown: `[*term*](/act/s995-1#anchor)`
- **Frontend** renders this via `ReactMarkdown` → plain `<a>` tag that navigates away
- **Backend** has `/api/definition/{act}/{term}` returning `{anchor, section}` metadata only
- Definition text lives in dictionary sections:
  - ITAA 1997 → `995-1`
  - GST 1999 → `195-1`
  - ITAA 1936 → `s6`

## Proposed Architecture

### 1. Backend — New Endpoint: `GET /api/definition-text/{act}/{term}`

**Input:** `act` (slug), `term` (URL-encoded term text)

**Output:**
```json
{
  "term": "taxable supply",
  "act": "gst-1999",
  "section": "195-1",
  "anchor": "s195-1-1",
  "text": "taxable supply has the meaning given by section 9-5.",
  "path": "/gst-1999/s195-1#s195-1-1"
}
```

**How `text` is extracted:**
1. Look up the term in `load_definitions(act)` → get `section` and `anchor`.
2. Load the dictionary section markdown file (e.g. `data/gst-1999/sections/.../195-1.md`).
3. Find the anchor `<a id="...">` in the file.
4. Extract the paragraph/line(s) immediately following the anchor that constitute the definition.
5. Strip markdown formatting (bold, blockquotes) and return plain text.

**Edge cases:**
- Term not found → 404
- Anchor not in section file → 404
- Multi-line definitions (e.g. `accounting principles:` with sub-paragraphs (a), (b)) → extract until the next blank line or next term.
- Colon-style vs predicate-style definitions handled uniformly.

**Implementation location:** `backend/routes/api.py` (add to `api_router`).

**Estimated effort:** Small — reuse existing `load_definitions`, `get_act_section_content`, simple regex extraction.

---

### 2. Backend — Enrich Existing `/api/definition/{act}/{term}`

Optionally add `text` to the existing endpoint to save a round-trip. However, the existing endpoint is a lightweight metadata lookup; adding file I/O slows it down. **Recommendation:** keep them separate. The popup calls `/api/definition-text/...` lazily.

---

### 3. Frontend — Custom Link Renderer

**Problem:** `ReactMarkdown` renders `[*term*](/act/ssection#anchor)` as a plain `<a>` tag. We need to intercept clicks on definition links.

**Solution:** Provide a custom `components` prop to `ReactMarkdown` that overrides `<a>` rendering.

```tsx
const DefinitionLink = ({ href, children }: { href: string; children: React.ReactNode }) => {
  const isDefLink = href.match(/^\/[a-z0-9-]+\/s\d+(-\d+)?#/)
  if (!isDefLink) return <a href={href}>{children}</a>

  const [act, rest] = href.slice(1).split('/s')
  const [section, anchor] = rest.split('#')
  const term = extractTermFromChildren(children) // strip asterisks

  return (
    <DefinitionPopover
      term={term}
      act={act}
      section={section}
      anchor={anchor}
      onNavigate={() => window.location.href = href}
    >
      <a href={href} onClick={(e) => e.preventDefault()} style={{ color: COLORS.accent, cursor: 'pointer' }}>
        {children}
      </a>
    </DefinitionPopover>
  )
}
```

**In `ReactMarkdown`:**
```tsx
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  rehypePlugins={[rehypeRaw]}
  components={{ a: DefinitionLink }}
>
  {sectionData.body}
</ReactMarkdown>
```

---

### 4. Frontend — `DefinitionPopover` Component

**Behaviour:**
- **Trigger:** Click (or hover-debounce) on a definition link
- **Content:** Fetches `/api/definition-text/{act}/{term}` and displays the returned `text`
- **Layout:** Floating card positioned near the link, max-width 400px, Cadena brand styling
- **Actions:**
  - Click anywhere inside the card → navigate to the definition section (`path` from API response)
  - Click outside or press Escape → close
  - "Go to definition ↗" explicit button inside card

**State management:**
- Use a ref-based popover (not React state for position) to avoid re-rendering the entire markdown body on hover.
- Cache fetched definition texts in a local `Map` so repeated hovers don’t re-fetch.

**Styling (Cadena palette):**
```
Background: #0b1b1f
Border: 1px solid #253d3d
Text: #aebec2
Accent link: #279e88
Shadow: 0 8px 24px rgba(0,0,0,0.4)
Border-radius: 8px
Padding: 16px
```

**File:** `frontend/src/components/DefinitionPopover.tsx`

---

### 5. API Client Update

Add to `frontend/src/api.ts`:
```ts
definitionText: (act: string, term: string) => fetchJson(`/definition-text/${encodeURIComponent(act)}/${encodeURIComponent(term)}`),
```

---

## Data Flow

```
User clicks *taxable supply*
  → DefinitionLink intercepts click
    → DefinitionPopover opens, calls GET /api/definition-text/gst-1999/taxable%20supply
      → Backend:
        1. load_definitions("gst-1999") → {anchor: "s195-1-1", section: "195-1"}
        2. Load 195-1.md, find <a id="s195-1-1"></a>
        3. Extract: "taxable supply has the meaning given by section 9-5."
        4. Return JSON
      → Frontend renders popover with text
    → User clicks inside popover
      → window.location = /gst-1999/s195-1#s195-1-1
```

## Open Questions / Decisions

1. **Hover vs click trigger?**
   - Hover is nicer but risks accidental triggers on dense text.
   - **Recommendation:** Click to open, hover shows a subtle underline hint.

2. **How much text to extract?**
   - Some definitions are one line. Others span multiple paragraphs (e.g. "accounting principles" with (a)/(b) sub-items).
   - **Recommendation:** Extract from the anchor until the next top-level term or a blank line. Cap at ~500 chars with a "…" truncation indicator.

3. **What about ITAA 1936 s6?**
   - ITAA 1936 definitions are in section 6, which has a different structure (often one continuous paragraph).
   - **Recommendation:** Same extraction logic, tested against s6 format.

4. **Non-dictionary defined terms (auto-linked by `auto_link_definitions`)?**
   - These are also rendered as `[*term*](/act/ssection#anchor)` links.
   - **Recommendation:** The custom `<a>` renderer handles all definition links uniformly — no extra work needed.

## Implementation Order

1. **Backend:** `GET /api/definition-text/{act}/{term}` endpoint + unit test
2. **Frontend:** `DefinitionPopover` component (UI only, mock data)
3. **Frontend:** Custom `<a>` renderer in `ReactMarkdown` usage
4. **Frontend:** Wire up API call in popover
5. **Integration test:** Verify popup opens, text displays, navigation works across all 3 acts

## Files to Touch

| File | Change |
|------|--------|
| `backend/routes/api.py` | Add `/api/definition-text/{act}/{term}` route |
| `backend/services/data_loader.py` | Add `get_definition_text(act, term)` helper |
| `frontend/src/api.ts` | Add `definitionText()` method |
| `frontend/src/components/DefinitionPopover.tsx` | **New** — popover component |
| `frontend/src/App.tsx` | Pass custom `components={{a: DefinitionLink}}` to ReactMarkdown |
