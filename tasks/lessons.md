# Lessons learned — Sentinel Demo

> Format : `[YYYY-MM-DD] | symptôme observé | règle pour éviter la prochaine fois`
> À relire au démarrage de chaque session (CLAUDE.md §0).

---

## 2026-05-24
- `uv` n'est pas un vrai binaire sur la machine de Jo — c'est une fonction shell qui active un venv partagé (`/Users/jo/Desktop/Intro to GenAI/.uv/`) et redirige `uv add` vers `pip install`. **Règle** : ne jamais supposer `uv sync`/`uv run`. Utiliser le Python du venv partagé directement (`/Users/jo/Desktop/Intro to GenAI/.uv/bin/python`) ou `pip install` après avoir sourcé `activate`.
