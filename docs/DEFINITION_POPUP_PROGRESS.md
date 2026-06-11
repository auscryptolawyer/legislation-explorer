# Definition Popup Feature — Progress & Next Steps

## Status
**Backend: COMPLETE | Frontend: NOT STARTED**

## Done

### 1. Backend — Definition Text Extraction (`backend/services/data_loader.py`)
- Added `get_definition_text(act, term)` at line 565
- Loads definitions via `load_definitions(act)`
- Locates dictionary section file (995-1 / 195-1 / 6) via rglob
- Strips frontmatter, finds term by lowercase substring match
- Detects definition boundary by finding next term preceded by `.`, `;`, `:`, or newline
- Strips markdown noise (`<a id>`, `>`, `**`, extra whitespace)
- Caps output at 500 chars with "..."
- Returns `{term, act, section, anchor, text, path}`

### 2. Backend — API Endpoint (`backend/routes/api.py`)
- Added `GET /api/definition-text/{act}/{term}` at line 150
- Imports `get_definition_text` at module level (line 25)
- Returns 404 if term not found

### 3. Data Quality Fixes (prerequisite)
- Cleaned all PDF artifacts from 14,433 files
- Fixed 23 broken Master Tax Example titles
- Truncated leaked schedule/endnote text from GST 195-1.md (128,393 chars)
- Verified 0 remaining issues across all 7 acts
- Daily backups via `scripts/backup.sh` cron at 03:00

## Not Done — Frontend Implementation Required

### Step 1: `frontend/src/api.ts` (~line 50)
Add method:
```ts
definitionText: (act: string, term: string) => fetchJson(`/definition-text/${act}/${term}`)
```

### Step 2: `frontend/src/components/DefinitionPopover.tsx` (CREATE)
Component requirements:
- Props: `act`, `term`, `anchor`, `children` (the link text / italic term)
- State: `open`, `loading`, `definition` (fetched data)
- Render: children wrapped in a `<span>` with click handler
- Clicking children → fetches `/api/definition-text/{act}/{term}`, shows floating card
- Floating card styling (Cadena brand):
  - `position: absolute`, `zIndex: 1000`
  - `maxWidth: 400px`, `background: COLORS.surface`, `border: 1px solid COLORS.border`
  - `borderRadius: 6px`, `padding: 12px 16px`
  - `boxShadow: '0 4px 20px rgba(0,0,0,0.4)'`
  - Title: term in bold white
  - Body: definition text in `COLORS.text`, `fontSize: 13`, `lineHeight: 1.6`
  - Footer: "Go to definition →" link in `COLORS.accent`
- Clicking the card / "Go to definition" → navigates to `/{act}/s{section}#{anchor}`
- Click outside → closes popup
- Loading state: small spinner or "Loading..." text
- Error state: "Definition not found" in muted text

### Step 3: `frontend/src/App.tsx` — Modify `<a>` Renderer
Two `<a>` renderers exist (lines 527-557 for ruling view, lines 627-648 for section view).
Both need the same change:

Detect definition links by checking if `href` contains a dictionary section:
```ts
const isDefinitionLink = href && /\/(itaa-\d{4}|gst-\d{4})\/s(995-1|195-1|6(?:\.md)?)#/i.test(href);
```

If `isDefinitionLink`:
- Extract `term` from `children` (it will be wrapped in `<em>` or just text)
- Extract `anchor` from href hash
- Return `<DefinitionPopover act={...} term={...} anchor={...}>{children}</DefinitionPopover>`

Otherwise keep existing navigation logic.

### Step 4: Build & Test
```bash
cd /home/harrison/legislation-explorer/frontend
npm run build
```

Test cases:
1. ITAA 1997 section with defined terms (e.g. s6-5 "*assessable income*")
   - Click → popup shows definition text from 995-1
   - Click popup → navigates to 995-1#anchor
2. GST 1999 section with defined terms (e.g. s9-5 "*taxable supply*")
   - Click → popup shows definition text from 195-1
3. ITAA 1936 section with defined terms (e.g. s6 "*assessment*")
   - Click → popup shows definition text from section 6
4. Non-definition links continue to work as before
5. Mobile: popup renders within viewport, no overflow

## Key Technical Context
- Definition link format in markdown: `[*term*](/act/s995-1#anchor)`
- Backend auto-links definitions in `auto_link_definitions()` (markdown.py line 233)
- Dictionary sections: ITAA97=995-1, GST=195-1, ITAA36=6
- GST has a separate `definitions.json` at `data/gst-1999/definitions.json` (329 terms)
- ITAA97+ITAA36 use `data/definitions_all.json`
- The `children` prop in ReactMarkdown `<a>` renderer receives the rendered link content (may include `<em>` from `*term*`)
