# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-02

### Added

- `python manage.py mermaid_erd` management command and `mermaid-erd` standalone CLI
  (works without adding the app to `INSTALLED_APPS`).
- Mermaid `erDiagram` output covering ForeignKey, nullable FK, OneToOne, ManyToMany (auto and
  custom `through`), self references, multi-table inheritance, proxy models, GenericForeignKey,
  unmanaged models, UUID primary keys, composite primary keys (Django 5.2) and same-named
  models in different apps.
- Mermaid `classDiagram` output with one namespace per app and inheritance arrows.
- Selection: app / `app.Model` targets, glob `--exclude`, `--include-builtin`, `--no-proxy`,
  `--focus` with `--depth`.
- Content options: `--fields`, `--types`, `--field-names`, `--sort-fields`, `--max-fields`,
  `--comments`, `--verbose-names`, `--generic-edges`, `--qualified`, `--direction`, `--no-banner`.
- Output: `-o`, `--md`, idempotent `--inject` marker blocks, `--check` with unified diff for CI.
- Optional `--svg` / `--png` through a local mermaid-cli or mermaid.ink (standard library only).
- `settings.MERMAID_ERD` project defaults.
- Automatic escaping of model, app and field names that are Mermaid keywords.
- pre-commit hook `mermaid-erd-check`.

[0.1.0]: https://github.com/Aaron-lab-c/django-mermaid-erd/releases/tag/v0.1.0
