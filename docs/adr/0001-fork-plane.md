# ADR 0001: Build RopeOps on a fork of Plane, a project management tool for rope access and window cleaners
Date: 2026-11-05 · Status: Accepted

## Context
I need a multi-tenant project management base fast, so the team can focus on rope access and window cleaning features.

## Decision
Fork makeplane/plane, the most-starred open-source PM app (Django + React, AGPL-3.0).

## Consequences
+ Workspaces, projects, work items, roles and a public-views app come for free.
+ An active upstream ships fixes I can merge monthly.
- AGPL-3.0: our modified source must stay public.
- Custom code must stay separate from core so upstream merges stay easy.
