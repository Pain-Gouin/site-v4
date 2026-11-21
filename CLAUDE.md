# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Pain'Gouin: Django 5.2 site (Python 3.13, managed with `uv`) for selling and delivering bakery products to a student residence. Features: user balances, deliveries/orders, manual and HelloAsso card top-ups, and an admin backoffice (django-unfold). The code and docs are in French; the README and `docs/DocumentationTechnique.md` are the detailed references.

## Guiding principle

The project must stay as clean and as simple to maintain as possible, because a new "respo web" (usually a self-taught student, not a professional) takes it over every year or two. When making changes:
- Prefer the simplest solution that works, using plain Django idioms and existing dependencies. Don't add new libraries, abstractions or layers unless they clearly reduce complexity.
- Keep code readable and consistent with the surrounding code. Fix or remove dead code rather than working around it.
- Keep the docs in sync: update `README.md` / `docs/DocumentationTechnique.md` (and the handover checklist) when a change affects setup, deployment, permissions or configuration. Documentation is written in French.

## Commands

Run everything through `uv run`. The devcontainer (`.devcontainer/`) sets up MariaDB, RabbitMQ, Mailpit and phpMyAdmin, and its `postCreateCommand` runs `uv sync`, `migrate`, `createcachetable`, `seed_db` and `create_default_admin` (login `admin@admin.com` / `admin`).

- Dev server with live Tailwind rebuild: `uv run manage.py tailwind dev`. Use this instead of plain `runserver`, otherwise new Tailwind classes won't be compiled.
- Migrations: `uv run manage.py makemigrations` then `uv run manage.py migrate`. Always commit generated migrations. They run automatically on container start in prod.
- Lint/format everything (ruff, djlint, file hygiene hooks): `uv run prek run --all-files`. This is the same check CI runs.
- Type check: `uv run mypy .`. The code is not yet type-clean, so don't treat existing errors as regressions.
- Regenerate fake dev data: `uv run manage.py seed_db` (uses factory_boy factories in `commande/factories.py`).
- Production CSS: `manage.py tailwind build` and then `collectstatic` (done by the Docker image).

There is effectively no test suite (`commande/tests/tests.py` is empty), so there is no single-test command to run. CI only runs the linters.

## Architecture

Three Django packages:
- `commande/` is the single app holding all business logic: `models.py`, `views.py`, `forms.py`, `admin.py` (about 1000 lines, the whole backoffice), `tasks.py` (Celery), `urls.py`, `utils/` (HelloAsso client, tokens, widgets).
- `paingouin/` holds the project config (`settings.py`, `celery.py`, root urls). Env vars are read through django-environ (defaults in `.env.dist`).
- `theme/` is the Tailwind 4 and Flowbite setup (django-tailwind). It needs Node, version in `.nvmrc`.

The top-level `templates/` overrides third-party templates. It forces django-yubin's admin views onto the original Django admin because they are incompatible with Unfold. Re-check these overrides when upgrading Django or yubin.

Domain model (`commande/models.py`): custom `User` (email login, `balance_cache` field), `ProductCategory` → `Product`, `Delivery`, `Order` → `OrderProduct` → `Product` (price and quantity are snapshotted per order), `HelloAssoCheckout`, `Transaction`.

### Money invariants (important)
- `Transaction` is an immutable ledger. `save()` on an existing row, `delete()`, and bulk `update()`/`delete()` all raise `PermissionDenied`. Never try to edit or delete transactions. Correct mistakes with a new compensating transaction (e.g. `REFUND`).
- `User.balance_cache` is kept in sync by `Transaction.save()` using an `F()` update. Create balance changes only through `Transaction` rows, never by writing `balance_cache` directly.
- Foreign keys from transactions use `on_delete=PROTECT`.

### HelloAsso payments
Top-up flow: `recharge` view creates a `HelloAssoCheckout` → user pays on HelloAsso → `helloasso_webhook_handler` (`/recharge/helloasso_webhook`) enqueues Celery tasks in `commande/tasks.py` → `checkout.refresh_from_api()` updates the status and creates the `Transaction`. `refresh_transactions` is a periodic task (celery beat) that re-polls pending/initiated checkouts. The `PROD` env var picks the HelloAsso production or sandbox API. Credentials live in the association drive, not in the repo.

### Async work and email
Celery (RabbitMQ broker) runs the HelloAsso tasks and django-yubin's queued email. In dev, mail goes to Mailpit. Email templates are MJML (django-mjml-template, a Rust port, no Node needed) in `commande/templates/mail/`. The MySQL server needs its timezone tables loaded for the yubin admin log views to work.

### Permissions
Django's permission system is **not** used. Access is gated by `is_staff` (backoffice) and `is_superuser` (full access), and per-model restrictions are enforced by a custom `CustomModelAdmin` base class in `admin.py`. Staff must not be able to do destructive or inconsistent things (deleting transactions, deleting products referenced by orders).

### Runtime configuration
Site constants editable at runtime (delivery cutoff time, legal and contact info, etc.) use django-constance with the database backend (`CONSTANCE_CONFIG` in `settings.py`), edited from the admin "Constantes" tab. Prefer adding a constance entry over hard-coding such values.

## Conventions
- Ruff has a very broad rule set (`pyproject.toml`), max line length 120. Migrations and `static/` are excluded from linting. Templates are formatted by djlint (django profile, 2-space indent).
- Branches: `main` is the development branch and `prod` is deployed. A PR to `prod` builds a `dev` image that must be manually tested and approved (comment `\tested`) before merge. Merging to `prod` publishes the image to GHCR, and Watchtower redeploys it. Back up the DB before deploying migrations.
- The `.claude/` dev container variant (`.devcontainer/claude/`) ships Playwright MCP restricted to `http://localhost:8000`.
