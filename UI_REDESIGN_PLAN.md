# UI Redesign Plan for Agent Architecture Platform
## Phase 4b+ — Complete Visual Overhaul

---

## 1. Design Philosophy & Goals

### Core Principles
- **Agent-First**: UI revolves around the 4 independent agents (Auto Trend, XRP Swing, P2P Market, Manual)
- **Real-Time Clarity**: Live status, metrics, and actions at a glance
- **Information Density**: Professional trading terminal feel — dense but scannable
- **Mobile-First Responsive**: Works on phone, tablet, desktop
- **RTL-First Arabic Support**: Proper RTL layout, not just mirrored
- **Dark/Light Themes**: Full theme switching with persistence

### Visual Identity
- **Primary**: Deep navy/charcoal surfaces with electric blue accent (`#63b3ed`)
- **Success**: Emerald green (`#48bb78`) for running agents, profits
- **Warning**: Amber (`#f6ad55`) for paused agents, attention
- **Danger**: Crimson (`#fc8181`) for errors, stopped agents, losses
- **Typography**: System UI stack, monospace for numbers (tabular-nums)

---

## 2. Architecture Overview

### New Page Structure
```
/ (Dashboard)          → Agent Overview + Global Status
/agents                → Agent Control Panel (detailed)
/agents/auto-trend     → Auto Trend Agent Detail
/agents/xrp-swing      → XRP Swing Agent Detail
/agents/p2p-market     → P2P Market Agent Detail
/agents/manual         → Manual/Insights Agent Detail
/p2p                   → P2P Market Snapshot + Analytics
/intel                 → Macro + Scanner + Timing
/journal               → Trade Journal
/settings              → Global Settings + Theme
```

### Component Hierarchy
```
App.vue
├── AppHeader (sticky)
│   ├── Logo + Platform Status
│   ├── Agent Quick Bar (4 agents with status dots)
│   ├── Theme Toggle
│   ├── Language Toggle
│   └── Notification Bell
├── SideNav (collapsible, mobile drawer)
│   ├── Dashboard
│   ├── Agents (expandable)
│   ├── P2P Market
│   ├── Intelligence
│   ├── Journal
│   └── Settings
├── MainContent (router-view)
│   ├── DashboardView
│   ├── AgentDetailView
│   ├── P2PView
│   ├── IntelView
│   ├── JournalView
│   └── SettingsView
└── Toast/Alert System (global)
```

---

## 3. Design Tokens Update

### Extended Color System (tokens.css)
```css
:root {
  /* ── Theme: Dark (default) ───────────────────────────────────────────── */
  --color-bg: #0a0d14;
  --color-bg-elevated: #11151d;
  --color-surface: #151a24;
  --color-surface-hover: #1c2330;
  --color-surface-raised: #1e2632;
  --color-surface-overlay: #242d3d;
  
  --color-border: #2a3444;
  --color-border-subtle: #1e2838;
  --color-border-strong: #3d4a5e;
  --color-border-focus: #63b3ed;
  
  --color-text: #e8edf3;
  --color-text-primary: #ffffff;
  --color-text-secondary: #9caab8;
  --color-text-tertiary: #6d7d8d;
  --color-text-inverse: #0a0d14;
  --color-text-link: #63b3ed;
  
  /* ── Brand ───────────────────────────────────────────────────────────── */
  --color-brand: #63b3ed;
  --color-brand-strong: #90cdf4;
  --color-brand-subtle: rgba(99, 179, 237, 0.12);
  --color-brand-emphasis: #2b6cb0;
  
  /* ── Agent Status Colors ─────────────────────────────────────────────── */
  --color-agent-running: #48bb78;
  --color-agent-running-bg: rgba(72, 187, 120, 0.12);
  --color-agent-running-border: rgba(72, 187, 120, 0.3);
  --color-agent-paused: #f6ad55;
  --color-agent-paused-bg: rgba(246, 173, 85, 0.12);
  --color-agent-paused-border: rgba(246, 173, 85, 0.3);
  --color-agent-stopped: #718096;
  --color-agent-stopped-bg: rgba(113, 128, 150, 0.1);
  --color-agent-stopped-border: rgba(113, 128, 150, 0.2);
  --color-agent-error: #fc8181;
  --color-agent-error-bg: rgba(252, 129, 129, 0.12);
  --color-agent-error-border: rgba(252, 129, 129, 0.3);
  --color-agent-starting: #63b3ed;
  --color-agent-starting-bg: rgba(99, 179, 237, 0.12);
  
  /* ── Semantic ────────────────────────────────────────────────────────── */
  --color-success: #48bb78;
  --color-success-bg: rgba(72, 187, 120, 0.1);
  --color-success-border: rgba(72, 187, 120, 0.25);
  --color-warning: #f6ad55;
  --color-warning-bg: rgba(246, 173, 85, 0.1);
  --color-warning-border: rgba(246, 173, 85, 0.25);
  --color-danger: #fc8181;
  --color-danger-bg: rgba(252, 129, 129, 0.1);
  --color-danger-border: rgba(252, 129, 129, 0.25);
  --color-info: #63b3ed;
  --color-info-bg: rgba(99, 179, 237, 0.1);
  --color-info-border: rgba(99, 179, 237, 0.25);
  
  /* ── Spacing Scale ───────────────────────────────────────────────────── */
  --space-0: 0;
  --space-1: 0.125rem;   /* 2px */
  --space-2: 0.25rem;    /* 4px */
  --space-3: 0.375rem;   /* 6px */
  --space-4: 0.5rem;     /* 8px */
  --space-5: 0.75rem;    /* 12px */
  --space-6: 1rem;       /* 16px */
  --space-8: 1.5rem;     /* 24px */
  --space-10: 2rem;      /* 32px */
  --space-12: 2.5rem;    /* 40px */
  --space-16: 3rem;      /* 48px */
  
  /* ── Border Radius ───────────────────────────────────────────────────── */
  --radius-none: 0;
  --radius-xs: 2px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
  --radius-2xl: 16px;
  --radius-pill: 9999px;
  --radius-full: 50%;
  
  /* ── Typography ──────────────────────────────────────────────────────── */
  --font-sans: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
  
  --text-xs: 0.6875rem;    /* 11px */
  --text-sm: 0.8125rem;    /* 13px */
  --text-base: 0.9375rem;  /* 15px */
  --text-lg: 1.0625rem;    /* 17px */
  --text-xl: 1.25rem;      /* 20px */
  --text-2xl: 1.5rem;      /* 24px */
  --text-3xl: 1.875rem;    /* 30px */
  --text-4xl: 2.25rem;     /* 36px */
  
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
  
  /* ── Shadows ─────────────────────────────────────────────────────────── */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.35);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.45);
  --shadow-xl: 0 16px 48px rgba(0,0,0,0.5);
  --shadow-glow: 0 0 20px rgba(99, 179, 237, 0.3);
  --shadow-glow-success: 0 0 20px rgba(72, 187, 120, 0.3);
  --shadow-glow-warning: 0 0 20px rgba(246, 173, 85, 0.3);
  --shadow-glow-danger: 0 0 20px rgba(252, 129, 129, 0.3);
  
  /* ── Transitions ─────────────────────────────────────────────────────── */
  --transition-fast: 100ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;
  
  /* ── Z-Index ─────────────────────────────────────────────────────────── */
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-modal: 300;
  --z-popover: 400;
  --z-tooltip: 500;
  --z-toast: 600;
  
  /* ── Layout ──────────────────────────────────────────────────────────── */
  --header-height: 56px;
  --sidenav-width: 260px;
  --sidenav-collapsed: 72px;
  --content-max: 1600px;
  --sidebar-breakpoint: 1024px;
  --mobile-breakpoint: 768px;
}

/* ── Light Theme ───────────────────────────────────────────────────────── */
[data-theme="light"] {
  --color-bg: #f8fafc;
  --color-bg-elevated: #ffffff;
  --color-surface: #ffffff;
  --color-surface-hover: #f1f5f9;
  --color-surface-raised: #ffffff;
  --color-surface-overlay: #f8fafc;
  
  --color-border: #e2e8f0;
  --color-border-subtle: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-border-focus: #2563eb;
  
  --color-text: #1e293b;
  --color-text-primary: #0f172a;
  --color-text-secondary: #64748b;
  --color-text-tertiary: #94a3b8;
  --color-text-inverse: #ffffff;
  --color-text-link: #2563eb;
  
  --color-brand: #2563eb;
  --color-brand-strong: #3b82f6;
  --color-brand-subtle: rgba(37, 99, 235, 0.1);
  --color-brand-emphasis: #1d4ed8;
  
  --color-agent-running: #16a34a;
  --color-agent-running-bg: rgba(22, 163, 74, 0.1);
  --color-agent-running-border: rgba(22, 163, 74, 0.2);
  --color-agent-paused: #ea580c;
  --color-agent-paused-bg: rgba(234, 88, 12, 0.1);
  --color-agent-paused-border: rgba(234, 88, 12, 0.2);
  --color-agent-stopped: #94a3b8;
  --color-agent-stopped-bg: rgba(148, 163, 184, 0.1);
  --color-agent-stopped-border: rgba(148, 163, 184, 0.2);
  --color-agent-error: #dc2626;
  --color-agent-error-bg: rgba(220, 38, 38, 0.1);
  --color-agent-error-border: rgba(220, 38, 38, 0.2);
  --color-agent-starting: #2563eb;
  --color-agent-starting-bg: rgba(37, 99, 235, 0.1);
  
  --color-success: #16a34a;
  --color-success-bg: rgba(22, 163, 74, 0.1);
  --color-success-border: rgba(22, 163, 74, 0.2);
  --color-warning: #ea580c;
  --color-warning-bg: rgba(234, 88, 12, 0.1);
  --color-warning-border: rgba(234, 88, 12, 0.2);
  --color-danger: #dc2626;
  --color-danger-bg: rgba(220, 38, 38, 0.1);
  --color-danger-border: rgba(220, 38, 38, 0.2);
  --color-info: #2563eb;
  --color-info-bg: rgba(37, 99, 235, 0.1);
  --color-info-border: rgba(37, 99, 235, 0.2);
  
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.1);
  --shadow-xl: 0 16px 48px rgba(0,0,0,0.12);
  --shadow-glow: 0 0 20px rgba(37, 99, 235, 0.25);
  --shadow-glow-success: 0 0 20px rgba(22, 163, 74, 0.25);
  --shadow-glow-warning: 0 0 20px rgba(234, 88, 12, 0.25);
  --shadow-glow-danger: 0 0 20px rgba(220, 38, 38, 0.25);
}
```

---

## 4. Core Components Specification

### 4.1 AppHeader.vue
**Purpose**: Sticky top bar with global status and quick actions

**Structure**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  Logo    │  Agent Quick Bar (4 pills)  │  Theme  Lang  Bell  User  │
└─────────────────────────────────────────────────────────────────────┘
```

**Agent Quick Bar Items**:
- Each agent: Icon + Name + Status Dot + Badge (if running)
- Click → navigate to agent detail
- Hover → tooltip with key metrics
- Status colors: Running (green pulse), Paused (amber), Stopped (gray), Error (red pulse)

**Responsive**:
- Desktop: Full bar visible
- Tablet: Collapse agent names, show icons only
- Mobile: Hamburger menu for agents, only critical items visible

### 4.2 SideNav.vue
**Purpose**: Primary navigation, collapsible

**Structure**:
```
┌────────────────────┐
│  CryptoTrada       │
├────────────────────┤
│  📊 Dashboard      │
│  🤖 Agents    ▼    │
│    ├ Auto Trend    │
│    ├ XRP Swing     │
│    ├ P2P Market    │
│    └ Manual        │
│  🤝 P2P Market     │
│  🧠 Intelligence   │
│  📓 Journal        │
│  ⚙️ Settings       │
└────────────────────┘
```

**States**:
- Expanded (260px): Full labels + icons
- Collapsed (72px): Icons only, tooltips on hover
- Mobile: Slide-over drawer (full width)

### 4.3 AgentStatusPill.vue (Reusable)
**Purpose**: Compact agent status indicator

**Variants**:
- `size="sm"`: Header bar (icon + dot)
- `size="md"`: Dashboard cards (icon + name + dot + metrics)
- `size="lg"`: Agent detail header (full status + controls)

**Props**:
```typescript
interface AgentStatusPillProps {
  agent: AgentStatus;
  size: 'sm' | 'md' | 'lg';
  showMetrics?: boolean;
  showActions?: boolean;
  clickable?: boolean;
}
```

### 4.4 MetricCard.vue (Reusable)
**Purpose**: Standardized metric display

**Structure**:
```
┌─────────────────────┐
│  Label              │
│  ┌───────────────┐  │
│  │   Value       │  │  ← Large, tabular-nums, color-coded
│  └───────────────┘  │
│  Change: +5.2% ↗    │  ← Optional trend
└─────────────────────┘
```

### 4.5 DataTable.vue (Reusable)
**Purpose**: Sortable, filterable, virtualized table

**Features**:
- Column sorting (click header)
- Column resize (drag)
- Row selection (checkbox)
- Pagination / infinite scroll
- Sticky header
- Horizontal scroll on mobile
- RTL-aware column ordering

---

## 5. Page Specifications

### 5.1 DashboardView.vue (/)
**Layout**: Grid of agent cards + global metrics

```
┌────────────────────────────────────────────────────────────────────┐
│  Global Status Bar:  Platform Online  │  3/4 Agents Running       │
├──────────────┬──────────────┬──────────────┬──────────────────────┤
│  Auto Trend  │  XRP Swing   │  P2P Market  │  Manual              │
│  ● RUNNING   │  ● RUNNING   │  ○ STOPPED   │  ● RUNNING           │
│  6 positions │  In Trade    │  —           │  Insights Only       │
│  +$234.56    │  +$89.12     │              │                      │
│  [View]      │  [View]      │  [Start]     │  [View]              │
├──────────────┴──────────────┴──────────────┴──────────────────────┤
│  Recent Activity (merged from all agents)                          │
│  ▶ BTC  $67,234  +2.1%  5m ago    ◼ ETH  $3,421  -0.8%  12m ago  │
└────────────────────────────────────────────────────────────────────┘
```

**Components**:
- `GlobalStatusBar`: Platform health, connectivity, active agent count
- `AgentCard` × 4: Status, key metrics, primary action
- `ActivityFeed`: Merged real-time events from all agents

### 5.2 AgentDetailView.vue (/agents/:type)
**Layout**: Tabbed detail view per agent

**Tabs per Agent Type**:

| Agent | Tabs |
|-------|------|
| Auto Trend | Overview | Positions | Signals | History | Config |
| XRP Swing | Overview | Trade Monitor | Setup Analysis | History | Config |
| P2P Market | Overview | Snapshot | Analytics | Orders | Config |
| Manual | Overview | Insights | Watchlist | Notes | Config |

**Overview Tab Structure**:
```
┌────────────────────────────────────────────────────────────────────┐
│  Agent Header:  [Icon] Auto Trend    ● RUNNING    [Pause] [Stop]  │
│  Uptime: 2h 34m  │  Cycles: 28  │  Fast Cycles: 560  │  Errors: 0 │
├──────────────┬──────────────┬──────────────┬──────────────────────┤
│  Positions   │  Today P&L   │  Win Rate    │  Total Trades        │
│  6 / 6       │  +$1,234.56  │  68%         │  142                 │
├──────────────┴──────────────┴──────────────┴──────────────────────┤
│  [Tab Content: Positions / Signals / etc.]                         │
└────────────────────────────────────────────────────────────────────┘
```

### 5.3 P2PView.vue (/p2p)
**Enhanced from current P2PSnapshot + Analytics**

**Layout**:
```
┌────────────────────────────────────────────────────────────────────┐
│  Live Rates:  SELL 4,125  │  SPREAD +42  │  BUY 4,083  [Refresh]  │
├──────────────┬──────────────┬──────────────┬──────────────────────┤
│  1h Avg      │  24h Avg     │  Best Buyer  │  Best Seller         │
│  +38 SDG     │  +31 SDG     │  Ahmed +5    │  Omar -3             │
├──────────────┴──────────────┴──────────────┴──────────────────────┤
│  Rate Chart (buy/sell lines + spread area)                         │
├────────────────────────────────────────────────────────────────────┤
│  Buyers (top 10)                    │  Sellers (top 10)            │
│  #  Merchant      Pays              │  #  Merchant      Charges    │
│  1  Ahmed         4,125             │  1  Omar          4,083      │
│  2  Fatima        4,120             │  2  Khalid        4,085      │
└────────────────────────────────────────────────────────────────────┘
```

### 5.4 IntelView.vue (/intel)
**Three-panel layout**: Macro | Scanner | Timing

### 5.5 JournalView.vue (/journal)
**Enhanced TradeJournal with agent attribution**

### 5.6 SettingsView.vue (/settings)
**Sections**: General | Theme | Notifications | API Keys | Agents Config | About

---

## 6. Interaction Patterns

### 6.1 Agent Control Flow
```
User clicks "Start" on stopped agent
    │
    ├─► Optimistic UI: Show STARTING spinner
    │
    ├─► API POST /api/agents/auto_trend/start
    │
    ├─► Success: Update state to RUNNING, show toast
    │
    └─► Error: Revert to STOPPED, show error toast
```

### 6.2 Real-Time Updates
- SSE connection for alerts (existing)
- Polling for agent metrics (5s interval)
- WebSocket for live price updates (future)

### 6.3 Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `Cmd/Ctrl + K` | Command palette |
| `Cmd/Ctrl + 1-4` | Switch to agent tab |
| `Cmd/Ctrl + D` | Dashboard |
| `Cmd/Ctrl + P` | P2P Market |
| `Cmd/Ctrl + I` | Intelligence |
| `Cmd/Ctrl + J` | Journal |
| `Cmd/Ctrl + ,` | Settings |
| `?` | Show shortcuts help |

---

## 7. Responsive Breakpoints

```css
/* Mobile First */
@media (min-width: 480px)  { /* Small phone landscape */ }
@media (min-width: 640px)  { /* Large phone / small tablet */ }
@media (min-width: 768px)  { /* Tablet portrait */ }
@media (min-width: 1024px) { /* Tablet landscape / desktop */ }
@media (min-width: 1280px) { /* Desktop */ }
@media (min-width: 1536px) { /* Large desktop */ }
```

### Layout Adaptations

| Component | Mobile (<768px) | Tablet (768-1024px) | Desktop (>1024px) |
|-----------|-----------------|---------------------|-------------------|
| SideNav | Drawer | Collapsible rail | Expanded |
| Agent Cards | 1 col | 2 col | 4 col |
| Data Tables | Horizontal scroll | 2-col stack | Full |
| Charts | Full width | Side by side | Grid |
| Agent Detail Tabs | Scrollable tabs | Scrollable tabs | Full tabs |

---

## 8. RTL (Arabic) Support

### CSS Logical Properties (Already Used)
- `margin-inline-start` / `margin-inline-end`
- `padding-inline-start` / `padding-inline-end`
- `border-inline-start` / `border-inline-end`
- `inset-inline-start` / `inset-inline-end`

### Direction-Aware Components
- SideNav: Right side in RTL
- Tab order: Reversed
- Icon direction: Arrows flipped
- Number formatting: Arabic-Indic digits option

### Implementation
```css
/* In App.vue or global */
:root[dir="rtl"] {
  /* Logical properties handle most cases */
}

/* Explicit overrides where needed */
[dir="rtl"] .chevron-right { transform: rotate(180deg); }
[dir="rtl"] .sidebar { left: auto; right: 0; }
```

---

## 9. Theme System

### ThemeProvider (Composable)
```typescript
// composables/useTheme.ts
export function useTheme() {
  const theme = ref<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved as 'light' | 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  
  function setTheme(t: 'light' | 'dark') {
    theme.value = t;
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('theme', t);
  }
  
  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark');
  }
  
  return { theme, setTheme, toggleTheme };
}
```

### CSS Application
```html
<html data-theme="dark">  <!-- or "light" -->
```

---

## 10. Animation & Motion

### Principles
- **Purposeful**: Every animation communicates state change
- **Fast**: 100-300ms max
- **Respects prefers-reduced-motion**
- **Consistent easing**: `cubic-bezier(0.4, 0, 0.2, 1)` (Material)

### Key Animations
| Trigger | Animation | Duration |
|---------|-----------|----------|
| Agent state change | Status dot pulse + color transition | 300ms |
| Tab switch | Cross-fade + slide | 200ms |
| SideNav collapse | Width + icon fade | 250ms |
| Toast appear | Slide up + fade | 300ms |
| Metric value change | Number count-up | 500ms |
| Chart update | Line morph | 400ms |

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 11. Accessibility (WCAG 2.1 AA)

### Checklist
- [ ] Semantic HTML structure
- [ ] Focus visible outlines (`:focus-visible`)
- [ ] ARIA labels on icon-only buttons
- [ ] Live regions for status updates
- [ ] Color contrast ratios (4.5:1 text, 3:1 UI)
- [ ] Keyboard navigation for all interactive elements
- [ ] Screen reader announcements for agent state changes
- [ ] Reduced motion support
- [ ] High contrast mode support

### Focus Management
```css
:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}
```

---

## 12. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Update `tokens.css` with new design system
- [ ] Create `base.css` reset + global styles
- [ ] Build `ThemeProvider` composable
- [ ] Add theme toggle to header
- [ ] Verify dark/light modes work

### Phase 2: Layout Shell (Week 1-2)
- [ ] Build `AppHeader` with agent quick bar
- [ ] Build `SideNav` with collapsible states
- [ ] Implement router layout with transitions
- [ ] Add RTL support testing
- [ ] Mobile drawer implementation

### Phase 3: Core Components (Week 2)
- [ ] `AgentStatusPill` (all sizes)
- [ ] `MetricCard`
- [ ] `DataTable` (with virtualization)
- [ ] `Card` / `CardHeader` / `CardSection`
- [ ] `Button` variants (primary, secondary, ghost, danger)
- [ ] `Select`, `Input`, `Checkbox`, `Switch`
- [ ] `Toast` / `Alert` system
- [ ] `Modal` / `Drawer` components

### Phase 4: Dashboard & Agent Views (Week 2-3)
- [ ] `DashboardView` with 4 agent cards
- [ ] `AgentDetailView` with tabs
- [ ] Auto Trend: Positions, Signals, History, Config
- [ ] XRP Swing: Trade Monitor, Setup, History, Config
- [ ] P2P Market: Snapshot, Analytics, Config
- [ ] Manual: Insights, Watchlist, Config

### Phase 5: Feature Views (Week 3)
- [ ] `P2PView` (enhanced)
- [ ] `IntelView` (Macro + Scanner + Timing)
- [ ] `JournalView` (enhanced)
- [ ] `SettingsView` (all sections)

### Phase 6: Polish & QA (Week 3-4)
- [ ] Animation refinements
- [ ] Performance optimization (lazy loading, virtualization)
- [ ] Accessibility audit
- [ ] Cross-browser testing
- [ ] Mobile device testing
- [ ] RTL verification
- [ ] Theme switching verification
- [ ] Documentation

---

## 13. File Structure (New)

```
frontend/src/
├── app.vue                    # Root layout with header + sidenav + router-view
├── main.ts                    # App entry + theme init
├── router/
│   └── index.ts               # Route definitions
├── composables/
│   ├── useTheme.ts            # Theme management
│   ├── useAgent.ts            # Agent store actions
│   ├── useWebSocket.ts        # Real-time connection
│   └── useKeyboard.ts         # Shortcuts
├── components/
│   ├── layout/
│   │   ├── AppHeader.vue
│   │   ├── SideNav.vue
│   │   ├── SideNavItem.vue
│   │   └── MobileDrawer.vue
│   ├── ui/
│   │   ├── Button.vue
│   │   ├── ButtonGroup.vue
│   │   ├── Input.vue
│   │   ├── Select.vue
│   │   ├── Checkbox.vue
│   │   ├── Switch.vue
│   │   ├── Card.vue
│   │   ├── CardHeader.vue
│   │   ├── CardSection.vue
│   │   ├── MetricCard.vue
│   │   ├── DataTable.vue
│   │   ├── DataTableColumn.vue
│   │   ├── Tabs.vue
│   │   ├── TabPanel.vue
│   │   ├── Badge.vue
│   │   ├── Avatar.vue
│   │   ├── Tooltip.vue
│   │   ├── Popover.vue
│   │   ├── Modal.vue
│   │   ├── Drawer.vue
│   │   ├── Toast.vue
│   │   ├── ToastContainer.vue
│   │   ├── Spinner.vue
│   │   ├── Skeleton.vue
│   │   ├── Divider.vue
│   │   └── Icon.vue
│   ├── agent/
│   │   ├── AgentStatusPill.vue
│   │   ├── AgentCard.vue
│   │   ├── AgentHeader.vue
│   │   ├── AgentMetrics.vue
│   │   └── AgentActions.vue
│   └── charts/
│       ├── LineChart.vue
│       ├── AreaChart.vue
│       ├── BarChart.vue
│       └── Sparkline.vue
├── views/
│   ├── DashboardView.vue
│   ├── agents/
│   │   ├── AgentDetailView.vue
│   │   ├── AutoTrendView.vue
│   │   ├── XRPSwingView.vue
│   │   ├── P2PMarketView.vue
│   │   └── ManualView.vue
│   ├── P2PView.vue
│   ├── IntelView.vue
│   ├── JournalView.vue
│   └── SettingsView.vue
├── stores/
│   ├── platform.ts            # Enhanced with agent state
│   ├── theme.ts               # Theme state
│   └── ui.ts                  # UI state (sideNav, toasts, modals)
├── assets/styles/
│   ├── tokens.css             # Design tokens (updated)
│   ├── base.css               # Reset + base
│   ├── layout.css             # Grid, flex utilities
│   ├── components.css         # Shared component styles
│   └── utilities.css          # Helper classes
└── locales/
    ├── en.js
    └── ar.js
```

---

## 14. Migration Strategy

### From Current to New
1. **Parallel Development**: Build new components alongside existing
2. **Feature Flags**: Route `/new/*` to new views, keep old at `/`
3. **Component Library**: Extract shared UI components first
4. **Incremental Migration**: Replace one view at a time
5. **Data Layer**: Reuse existing Pinia store, extend with new actions

### Backward Compatibility
- Keep existing API contracts
- Legacy routes redirect to new equivalents
- Gradual deprecation of old components

---

## 15. Success Metrics

| Metric | Target |
|--------|--------|
| Lighthouse Performance | > 90 |
| Lighthouse Accessibility | 100 |
| Lighthouse Best Practices | > 95 |
| First Contentful Paint | < 1.5s |
| Time to Interactive | < 3s |
| Bundle Size (gzipped) | < 150KB |
| Theme Switch Time | < 100ms |
| Agent Action Latency (UI) | < 50ms |

---

## 16. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | High | High | Strict phase gates, weekly reviews |
| Performance on mobile | Medium | High | Virtualization, lazy loading, code splitting |
| RTL bugs | Medium | Medium | Dedicated RTL testing, logical properties |
| Theme flash on load | Low | Medium | Inline theme script in `index.html` |
| WebSocket complexity | Medium | Medium | Start with polling, upgrade later |
| Data migration | Low | High | API versioning, backward compat |

---

## 17. Next Steps

1. **Approve this plan** → Proceed to implementation
2. **Set up component library** → Storybook for UI components
3. **Create design tokens PR** → Foundation for all work
4. **Begin Phase 1** → Tokens + Theme + Layout shell

---

*Document Version: 1.0*  
*Created: 2026-08-11*  
*Author: Architect Mode*  
*Status: Ready for Review*