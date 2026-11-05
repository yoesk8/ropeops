# Local development setup

Tested on: Intel Mac mini, macOS 15.7, 32 GB RAM (12 GB+ recommended).

## Prerequisites

- Docker Desktop, Node LTS, pnpm, git, GitHub CLI
- On Intel Macs Homebrew is Tier 3 (builds from source), so use official installers.
- Keep the repo OUT of iCloud-synced folders (Desktop/Documents). Repo lives in ~/work/ropeops.

## First run

1. ./setup.sh (creates .env files, generates SECRET_KEY, installs packages)
2. docker compose -f docker-compose-local.yml up -d
3. pnpm dev (separate terminal)

## Ports

| App                        | URL                                     |
| -------------------------- | --------------------------------------- |
| Web                        | http://localhost:3000                   |
| Space (client portal base) | http://localhost:3002/spaces/           |
| Live (real-time)           | 3100 (clashes with Paperclip's default) |

## Troubleshooting

- EADDRINUSE: an old `pnpm dev` is still running. Stop it with `pkill -f turbo; pkill -f vite`.
- Files named "x 2.md" mean iCloud sync conflicts. Move the repo out of Desktop.
