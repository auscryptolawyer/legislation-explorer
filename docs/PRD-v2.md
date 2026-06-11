# Legislation Explorer — v2 Feature PRD

## Scope
Features 1, 2, 6, 7, 9, 10 as requested. Plus fix ITAA 1936 schedules display.

---

## 1. Auto-Hyperlink Cross-References (Feature 1)
**Status:** Partially exists, needs expansion.

### Current State
- `backend/main.py` has `link_legislation_refs()` using regex `LEG_SECTION_RE`.
- Only links patterns like `s 8-1` within the same act.
- Does NOT handle: cross-act refs (`GST Act s 9-5`), subsection refs (`s 8-1(2)`), schedule refs (`Schedule 1, item 1`), or definition term links.

### Requirements
1. **Cross-act links**: `ITAA 1936 s 6-5` → link to `/itaa-1936/s6-5`. `GST Act s 9-40` → `/gst-1999/s9-40`. `TAA 1953 s 14ZZ` → `/taa-1953/s14ZZ`.
2. **Subsection links**: `s 8-1(2)` → `/itaa-1997/s8-1(2)`. `s 6-5(1)(a)` → `/itaa-1997/s6-5(1)(a)`.
3. **Definition links**: Bold+italic defined terms in non-dictionary sections should link to the definition section (s 995-1 or s 6).
4. **Schedule links**: `Schedule 1, item 1` → `/itaa-1997/sched1-item1` (or whatever path structure we settle on).

### Implementation
- Backend: expand `LEG_SECTION_RE` and `link_legislation_refs()`.
- Need a mapping of act short names → act IDs: `ITAA 1997` → `itaa-1997`, `ITAA 1936` → `itaa-1936`, `GST Act` → `gst-1999`, etc.
- Frontend: no changes needed if backend pre-processes markdown.

---

## 2. More Acts + Fix ITAA 1936 Schedules (Feature 2)
**Status:** Data-dependent.

### Current State
- Acts with data: `itaa-1997` (4638 sections), `itaa-1936` (781 sections), `gst-1999` (827 sections).
- Missing: FBT Act, SIS Act, TAA 1953.

### ITAA 1936 Schedules Bug
- The ITAA 1936 tree has 8 parts. Schedules (Schedule 1, Schedule 2A, etc.) are completely absent from the tree.
- Schedule files may exist on disk but aren't linked in `tree.json`.
- **Fix**: Investigate if schedule markdown files exist. If yes, add them to `tree.json` as top-level items (after parts). If no, document as data gap.

### New Acts
- **FBT Assessment Act 1986**: Check if data exists in pipeline output or needs scraping.
- **SIS Act 1993**: Same.
- **TAA 1953**: Same.
- **Acceptance criteria**: Each new act needs `data/<act-id>/tree.json` + `data/<act-id>/sections/*.md`.

---

## 6. Keyboard Shortcuts (Feature 6)
**Status:** Not implemented.

### Requirements
| Key | Action |
|-----|--------|
| `j` | Next section (same as "Next" button) |
| `k` | Previous section (same as "Previous" button) |
| `/` | Focus search input |
| `esc` | Close mobile drawer / blur search |
| `n` | Toggle commentary panel |
| `p` | Pin current section (split view, see Feature 7) |

### Implementation
- Add `useEffect` with `keydown` listener in `App.tsx`.
- Ignore shortcuts when user is typing in an input/textarea.
- Show a small shortcut help panel (triggered by `?`).

---

## 7. Split View / Pin Section (Feature 7)
**Status:** Not implemented.

### Requirements
- Click a "pin" button (or press `p`) to pin the current section in a side panel.
- Pinned section stays visible while browsing other sections in the main panel.
- Allow up to 2 pinned sections.
- Each pin shows: section title (clickable), close button, scrollable content.
- Persist pinned sections in `localStorage` by act+section.

### UI
- Below the main content or as a right-side panel (desktop only).
- Mobile: show pinned sections as tabs at the top.

---

## 9. Clickable Breadcrumbs (Feature 9)
**Status:** Partially exists, needs interactivity.

### Current State
- Content header shows: `ITAA 1997 › Part 3-1 › Division 40` as static text.

### Requirements
- Each breadcrumb segment is clickable.
- Clicking `Part 3-1` scrolls the drawer to that part and expands it.
- Clicking `Division 40` scrolls the drawer to that division and expands it.
- Add a "Copy citation" button that copies: `Income Tax Assessment Act 1997 (Cth), s 8-1`.

---

## 10. Search by Section Number (Feature 10)
**Status:** Not implemented.

### Current State
- Search uses FTS5 full-text search on content + title.
- Typing "8-1" returns sections that mention "8-1" in content, not necessarily section 8-1 itself.

### Requirements
- Exact match: if query is a valid section ID pattern (`8-1`, `6-5(1)`, `160ZZU`), jump directly to that section.
- Pattern: `/^\d+[A-Z]?(?:-\d+)?(?:\(\d+\))?(?:\([a-z]\))?$/i`
- Show exact match as first result with a "Jump to section" label.

---

## Task Registry

| ID | Feature | Status | Assignee | Notes |
|----|---------|--------|----------|-------|
| 1.1 | Expand cross-ref regex (same-act subsections) | Not started | TBD | Backend |
| 1.2 | Cross-act reference linking | Not started | TBD | Backend |
| 1.3 | Definition term linking in body text | Not started | TBD | Backend |
| 2.1 | Fix ITAA 1936 schedules in tree.json | Not started | TBD | Data investigation |
| 2.2 | Add FBT Act data | Not started | TBD | Data-dependent |
| 2.3 | Add SIS Act data | Not started | TBD | Data-dependent |
| 2.4 | Add TAA 1953 data | Not started | TBD | Data-dependent |
| 6.1 | Keyboard shortcut handler | Not started | TBD | Frontend |
| 6.2 | Shortcut help panel (`?`) | Not started | TBD | Frontend |
| 7.1 | Pin state + localStorage | Not started | TBD | Frontend |
| 7.2 | Pin panel UI | Not started | TBD | Frontend |
| 9.1 | Clickable breadcrumb segments | Not started | TBD | Frontend |
| 9.2 | Copy citation button | Not started | TBD | Frontend |
| 10.1 | Exact section number search | Not started | TBD | Backend + Frontend |
