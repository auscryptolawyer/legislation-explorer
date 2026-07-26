# UI Fixes — Legislation Explorer

## Files to change
- `frontend/src/App.tsx` — sidebar layout, hamburger, sign-in position, responsive
- `frontend/src/components/SearchPanel.tsx` — filter options layout

## Changes

### 1. Move sign-in to bottom of left sidebar pane
Currently sign-in is at top-right of main content area. Move it to the sidebar bottom section (near Settings/Bug buttons). Remove the top-right sign-in button/user display. The sidebar should show:
- Act picker (top)
- Tree (scrollable middle)
- Settings | Bug | Sign in / User info (bottom bar)

### 2. Hamburger menu → small filter icon next to search bar
Currently the mobile hamburger (☰) is a big button. Make it a very small filter icon next to the search input. The `filterButtonSvg` (three lines) is already defined in SearchPanel.tsx — use that same SVG. Size: ~24x24px.

### 3. Show all filter options, remove checkbox toggle
Currently filters have a "Best matches (cross-act ranking)" checkbox. When unchecked, act checkboxes appear. Remove this gating. Always show:
- Sort options: Best match / By section / By act (radio buttons)
- Source filters: checkboxes for each act
- Stretch: the whole filter panel collapses/expands via the small filter icon

### 4. Fix hamburger/search overlap
The hamburger button is positioned `fixed` at top:12, left:12 with z-index:110. On mobile when the search bar is at the top, this overlaps. Move the hamburger to be inside the search row, or make it the small filter icon next to the search input itself.

### 5. Fix X button / act picker overlap
The mobile close button (✕) is positioned at `left: mobileSidebarWidth - 56`. When the sidebar is narrow (280px min), this overlaps with the act picker dropdown. The close button should be at the top of the sidebar, outside the act picker container, or the act picker should have right padding to avoid the X.

### 6. Responsive padding/content reorg
- At narrow widths (<480px), the sidebar bottom buttons should stack vertically
- The act picker should remain readable at 280px
- Content area padding should reduce at narrow widths: `padding: '16px 12px 24px'` on mobile
- Tree items should have compact padding on mobile

## Implementation notes
- Use the existing `isMobile` state (window.innerWidth < 768)
- Keep all existing functionality (Settings, Bug report, MCP tokens)
- Keep the shortActName display format
- Don't break auth flow — sign in/out should still work