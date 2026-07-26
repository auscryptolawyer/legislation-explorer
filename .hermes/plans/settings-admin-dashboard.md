# Settings & Admin Dashboard — Feature Plan

## Branches

Two feature branches off master:

1. `feature/user-settings` — user-facing settings panel
2. `feature/admin-dashboard` — admin monitoring + controls

## User Settings (`feature/user-settings`)

### Backend: user_preferences table

New SQLite table at `backend/user_prefs.db` (or extend `mcp_tokens.db`):

```sql
CREATE TABLE user_preferences (
    email TEXT PRIMARY KEY,
    display_name TEXT DEFAULT '',
    default_act TEXT DEFAULT 'itaa-1997',
    theme TEXT DEFAULT 'dark',
    accent_color TEXT DEFAULT '#279e88',
    heading_font TEXT DEFAULT 'Montserrat',
    body_font TEXT DEFAULT 'Lora',
    updated_at REAL NOT NULL
);
```

Endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/user/prefs` | Get current user's prefs |
| PUT | `/api/user/prefs` | Update prefs (partial merge) |
| POST | `/api/user/prefs/reset` | Reset to defaults |

### Frontend: Settings panel

A new settings panel (replace/supplement the current gear dropdown) with sections:

**Profile tab:**
- Email (read-only, from SSO)
- Display name (text input)
- Default act (dropdown — same acts list as the sidebar picker)

**Appearance tab:**
- Theme toggle: Dark / Light
- Accent color: swatch picker (6-8 preset colours + custom hex input)
  - Presets: `#279e88` (teal, current), `#2563eb` (blue), `#7c3aed` (purple), `#059669` (green), `#d97706` (amber), `#dc2626` (red)
- Heading font: dropdown (Montserrat, Inter, Roboto, system-ui)
- Body font: dropdown (Lora, Merriweather, Georgia, serif, system-ui)
- Reset button: restores all appearance defaults

**Critical — responsive design:**
- All colour/font changes must be tested at narrow sidebar widths (280px) and full-width views
- Settings panel should scroll, not overflow
- Font sizes in `rem`, not `px`, so they scale with container
- Colour swatches need visible labels (not just coloured circles) for accessibility
- Light mode needs a full set of `COLORS` tokens — every component uses these, so the swap is one place

### Implementation notes

- `COLORS` object in `common/types.ts` — change to use CSS custom properties or a React context
- All components reference `COLORS.*` — no hardcoded colours (audit current code for stragglers)
- Font changes: apply via CSS variable on a wrapper div, cascade down
- localStorage cache for fast load; server is source of truth for cross-device sync
- Light mode palette:
  - `bg: '#f8f9fa'` (near-white), `surface: '#ffffff'` (white), `text: '#1a1a2e'` (dark), `heading: '#0a1214'` (near-black), `accent: '#279e88'` (same), `border: '#e2e8f0'` (light grey), `textMuted: '#64748b'` (slate)

## Admin Dashboard (`feature/admin-dashboard`)

### All-token dashboard

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/tokens` | All tokens across all users |
| POST | `/api/admin/tokens/{id}/revoke` | Revoke any token |

- Shows: token ID, name, created_by, request_count, last_used, created_at, revoked status
- Column-sortable table
- Revoke button per row
- Hall of Fame stats at top

Gate behind `require_user` + check email is Harry's (`harrison.dell@cadenalegal.com.au`).

### System health

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/health` | Full system health payload |

Response shape:

```json
{
  "backend": {
    "uptime_seconds": 12345,
    "version": "2.3.1",
    "auth_enabled": true
  },
  "database": {
    "cases": 7377,
    "case_paragraphs": 226619,
    "rulings": 5888,
    "mcp_tokens": 12,
    "last_backup": "2026-07-26",
    "search_index_built": "2026-07-25"
  },
  "legislation": [
    {"act": "itaa-1997", "compilation_no": 123, "compilation_date": "2026-04-01"},
    {"act": "itaa-1936", "compilation_no": 89, "compilation_date": "2026-04-01"},
    {"act": "gst-1999", "compilation_no": 228, "compilation_date": "2026-04-01"}
  ],
  "last_scrape": {
    "ato_rulings": "2026-07-25",
    "cases": "2026-07-24"
  }
}
```

- DB row counts via SELECT COUNT(*) on PostgreSQL + SQLite
- Uptime from process start time (`/proc/self/stat` or server start timestamp)
- Last backup: check `data/cadena_db_backup_*.sql.gz` modification time
- Search index: `SEARCH_DB` file mtime

### Re-index

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/admin/reindex` | Rebuild FTS index |

- Calls `init_search_index()` from `backend/services/search_service.py`
- Returns `{"status": "reindexing", "message": "..."}`
- Runs in background thread, returns immediately
- A subsequent health check shows `search_index_built` updated

### Error log viewer

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/logs?lines=50` | Last N lines of backend stderr |

- Runs `journalctl --user -u legislation-explorer --no-pager -n {lines}`
- Returns parsed lines as JSON array
- Filter by level (ERROR/WARNING/INFO) via query param
- Rate-limited (max 200 lines, cache 30s)

### User list

Need a login_log table:

```sql
CREATE TABLE login_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    name TEXT,
    login_at REAL NOT NULL
);
```

- Logged in `auth.py` `callback()` function
- Endpoint: `GET /api/admin/users` — returns all unique users with their last login time and total login count

### Admin gating

All `/api/admin/*` routes gated behind:

```python
def require_admin(request: Request):
    user = require_user(request)
    if user.get("email") != "harrison.dell@cadenalegal.com.au":
        raise HTTPException(403, "Admin access required")
    return user
```

## Design constraints (carried over from user's notes)

- **Container resizing:** All settings panels must look good at narrow sidebar widths (280px) and full-width views
- **Colour/font customisation:** Must not break existing layouts — every component uses `COLORS.*` tokens so a single token swap propagates everywhere
- **Responsive:** Settings must scroll, not overflow; colour swatches need labels not just colours