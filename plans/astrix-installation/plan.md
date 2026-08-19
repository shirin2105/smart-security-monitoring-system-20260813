---
title: "Astryx Design System Installation and Agent Conventions"
description: "Installation record for @astryxdesign packages, CLI setup, AGENTS.md documentation generation, and architectural/styling conventions."
status: complete
priority: P2
created: 2026-08-18
tags: [frontend, ui-system, astryx, stylex, setup]
---

# Astryx Design System Installation & Setup

## 1. Overview & Actions Taken

To establish the Astryx Design System across the project frontend (`front-end`), the following setup steps were executed:

1. **Package Installation**:
   - Installed core and CLI packages in `front-end`:
     - `@astryxdesign/core` (v0.4.3)
     - `@stylexjs/stylex` (peer dependency for StyleX styling)
     - `@astryxdesign/theme-neutral` (default theme)
     - `@astryxdesign/cli` (CLI tooling v0.4.3)
   - Command: `npm install @astryxdesign/core @stylexjs/stylex @astryxdesign/theme-neutral @astryxdesign/cli`

2. **Agent Documentation Initialization**:
   - Ran `npx @astryxdesign/cli init` in `front-end`.
   - Generated `front-end/AGENTS.md` containing agent guidelines and CLI workflow instructions.

3. **System Diagnostic Verification**:
   - Executed `npx astryx doctor` to verify environment compatibility:
     - Node.js runtime (v26.1.0 >= v22.13.0 required) - **PASS**
     - `@astryxdesign/core` resolved (v0.4.3) - **PASS**
     - `@astryxdesign/cli` alignment (v0.4.3) - **PASS**
     - Peer dependencies satisfied (`@stylexjs/stylex`, `react`, `react-dom`) - **PASS**
     - Agent docs presence - **PASS**

---

## 2. Core Conventions & Rules Learned

### A. Component-First Layout & Structure
- **No `<div>` Layouts**: Layout and spacing must use Astryx built-in layout components instead of raw HTML `<div>` or `<span>`.
- **Frame First**: Run `astryx docs layout` prior to constructing any page frame, region widths, or breakpoint structures.
- **Dense Data Representation**: Dense data belongs in edge-to-edge row components (`Table`, `List`/`Item` with dividers), never wrapping each row in a `Card`. `Card` is reserved for standalone widgets, summary modules, and settings containers.
- **Status vs Badges**:
  - `StatusDot` / `Token`: Used for status indicators.
  - `Badge`: Reserved exclusively for numeric counts or enumerated states.

### B. Styling & Design Tokens
- **Custom Styling Hierarchy**:
  1. Component props first.
  2. `xstyle` prop using `stylex.create()` for component overrides.
  3. Token-backed Tailwind classes (e.g. `bg-surface`, `text-primary`, `rounded-lg`).
- **Zero Raw Values**: Never hardcode hex codes (`#ffffff`), pixel dimensions (`13px`), or arbitrary values (no `bg-[#fff]`, `p-[13px]`).
- **Semantic Tokens**: All colors, spacing, radius, typography, and shadows must use CSS custom properties (`var(--color-*)`, `var(--spacing-*)`, `var(--radius-*)`).
- **Data Attributes for Selectors**: Target component states using data attributes (`.astryx-button[data-variant="primary"]`) rather than legacy bare classes (`.primary`).

### C. Application Setup Prerequisites
To render components properly with styles loaded, add the following imports in the app entry point (e.g., `src/main.tsx` or root layout):

```tsx
import "@astryxdesign/core/reset.css";
import "@astryxdesign/core/astryx.css";

// Optional: Neutral Theme wiring
import { neutralTheme } from "@astryxdesign/theme-neutral/built";
import "@astryxdesign/theme-neutral/theme.css";
```

---

## 3. CLI Workflow Cheat Sheet

| Command | Description |
|---|---|
| `npx astryx build "<idea>"` | Discover matching page templates, blocks, and components for a UI requirement. |
| `npx astryx template <name> [--skeleton]` | Scaffold or view reference layout for a page/block recipe. |
| `npx astryx component <Name>` | View props, API, and code examples for any Astryx component. |
| `npx astryx search "<query>"` | Search components, hooks, docs, templates, and blocks. |
| `npx astryx docs <topic>` | View guidelines on `layout`, `tokens`, `styling`, `principles`, `theme`, etc. |
| `npx astryx doctor` | Diagnose environment and dependency configuration. |
| `npx astryx swizzle <Name>` | Eject component source for deep local customization. |
