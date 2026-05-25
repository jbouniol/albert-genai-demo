# Lessons learned — Sentinel Demo

> Format : `[YYYY-MM-DD] | symptôme observé | règle pour éviter la prochaine fois`
> À relire au démarrage de chaque session (CLAUDE.md §0).

---

## 2026-05-24
- `uv` n'est pas un vrai binaire sur la machine de Jo — c'est une fonction shell qui active un venv partagé (`/Users/jo/Desktop/Intro to GenAI/.uv/`) et redirige `uv add` vers `pip install`. **Règle** : ne jamais supposer `uv sync`/`uv run`. Utiliser le Python du venv partagé directement (`/Users/jo/Desktop/Intro to GenAI/.uv/bin/python`) ou `pip install` après avoir sourcé `activate`.
- Avoir un `.env` ≠ avoir du quota. La clé OpenAI peut être valide mais le compte en `insufficient_quota`. **Règle** : avant la soutenance, vérifier https://platform.openai.com/usage et garder au moins 10$ de crédit. Le smoke test Phase 0 ne détecte pas ce cas (l'erreur 429 ne tombe qu'au moment d'un vrai appel).
- Premier draft du summary tool a noyé le signal "nouveau contact suspect" parce que Jake_M_15 apparaît jour 2 → classé comme "known contact" dans la baseline 0-13. **Règle** : pour le pattern grooming, distinguer EXPLICITEMENT les contacts "established" (présents day 0, actifs ≥14 jours) des "emerged during window" (first_day > 0). Le pattern grooming est dans la 2e catégorie, pas dans la baseline statistique.
- Premier draft a aussi flaggé des "primary app SWITCHED" pour des amis qui utilisaient juste plusieurs apps aléatoirement. **Règle** : seuil de 50% minimum pour considérer qu'un contact a un "primary app" sur une fenêtre — sinon le switch n'est pas réel, c'est du bruit. Sinon le LLM est noyé par des faux signaux.

## 2026-05-25
- Penser à streamer l'Analyzer pour l'effet "ChatGPT" parait évident, mais l'Analyzer retourne du Pydantic structuré (`text_format=AnalysisResult`). Le stream renvoie alors le JSON brut (`{"signals":[{"name":...`) — moche pour un jury. **Règle** : ne streamer que les sorties **prose pure** (Communicator's notification message, qui n'utilise pas `text_format=`). Pour le jury, le climax = la notification parent qui se tape en temps réel sur Lucas, pas du JSON.
- Streamlit 1.57 déprécie `use_container_width=True` au profit de `width="stretch"`. Le warning ne casse rien aujourd'hui mais sera supprimé après 2025-12-31. **Règle** : utiliser `width="stretch"` (forward-compatible) dès le début, surtout pour un projet qu'on veut pouvoir rejouer sur d'autres machines.
- Premier draft du `CachedLLMClient` avait un `parents[2]` pour trouver `data/llm_cache/` — résultait en `src/data/llm_cache/`, pas `data/llm_cache/` à la racine. **Règle** : `Path(__file__).resolve().parents[N]` est piégeux. Toujours vérifier en `print(CACHE_DIR)` qu'on tape bien la racine repo (`/Users/jo/Desktop/albert-genai-demo/data/llm_cache`).
- Une démo qui dépend de l'API en live n'est pas une démo, c'est une roulette. **Règle** : tout projet de démo doit avoir un mode `--cached` dès la Phase MVP, pas en polish. Sinon un quota épuisé / panne réseau / rate limit le jour J = backup vidéo Loom obligatoire. Le mode cached avec `time.sleep(0.005)` char-par-char préserve l'effet typing même en backup → indistinguable d'un vrai call pour le jury.
