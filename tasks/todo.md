# TODO — Sentinel Demo

> Roadmap source : message utilisateur du 2026-05-24.
> Status actuel : **Phase 0 — en cours**.

---

## Phase 0 — Setup & Fondations  (~3h) — EN COURS
- [x] Structure de dossiers conforme CLAUDE.md §4
- [x] pyproject.toml (deps + ruff)
- [x] .env.example + .gitignore
- [x] src/sentinel/config.py — MODELS + THRESHOLDS
- [x] src/sentinel/llm/client.py — wrapper LLMClient
- [x] scripts/smoke_test.py
- [x] tasks/todo.md + tasks/lessons.md
- [x] Installer deps manquantes (langgraph 1.2.1, streamlit 1.57.0, pytest 9.0.3, ruff 0.15.14) dans le venv partagé
- [x] `pip install -e .` → `sentinel-demo 0.1.0` installé en éditable
- [x] `ruff check .` → All checks passed
- [x] Import sanity check (LLMClient, MODELS, HITL_TRIGGER) → OK
- [ ] **À FAIRE PAR JO** : `cp .env.example .env` + ajouter `OPENAI_API_KEY=sk-...`
- [ ] **À FAIRE PAR JO** : `"/Users/jo/Desktop/Intro to GenAI/.uv/bin/python" scripts/smoke_test.py` → vérifier panels Rich INPUT/OUTPUT
- [ ] Tag git : `v0.1-setup` (après smoke test green)

## Phase 1 — Générateur de données + 3 profils  (~4h) — ✅ FAIT
- [x] Pydantic models (ContactInteraction, DailyMetadata, MetadataWindow) dans `src/sentinel/data/models.py` — frozen, AppName Literal
- [x] `src/sentinel/data/generator.py` — constantes (WINDOW_START=2026-05-03, 5 apps, seeds par profil) + 4 helpers + 3 fonctions
- [x] Sauvegarde JSON dans `src/sentinel/data/profiles/` (emma 1240 msgs, lucas 1237 msgs, mia 1429 msgs)
- [x] `tests/test_generator.py` — 26 tests, tous verts (communs + signatures par profil)
- [x] Inspection visuelle Lucas : progression grooming nette (sleep 8.16→5.67h, switch Discord→Snapchat au J+10, Jake 0→102 msgs)
- [x] Ruff vert + déterminisme confirmé
- [ ] **À FAIRE PAR JO** : `git add -A && git commit -m "Phase 1: data generator + 3 profiles" && git tag v0.2-data`

## Phase 2 — Skills + premier agent (Analyzer)  (~5h)
- [ ] 4 skills markdown : grooming.md, harassment.md, addiction.md, normal_life_event.md
- [ ] `src/sentinel/agents/base.py` — BaseAgent
- [ ] `src/sentinel/agents/analyzer.py`
- [ ] `scripts/run_analyzer.py`
- [ ] Validation : analyzer sur Lucas → ≥3 signaux grooming détectés ; sur Emma → normal_life_event
- [ ] Tag git : `v0.3-analyzer`

## Phase 3 — Multi-agent + LangGraph  (~5h) — 🎯 MVP MILESTONE
- [ ] Collector, Scorer, Communicator (pattern BaseAgent)
- [ ] AgentState Pydantic
- [ ] `src/sentinel/orchestrator/graph.py` — LangGraph
- [ ] Edge conditionnel score>0.65 → Communicator
- [ ] `scripts/run_cli_demo.py`
- [ ] PNG du graphe (pour slides)
- [ ] Validation : Lucas → 4 agents + notif parent ; Emma → 3 agents, skip Communicator
- [ ] Tag git : `v0.4-mvp` ⭐

## Phase 4 — UI Streamlit split-screen  (~8h sur 2 jours)
- [ ] `app/streamlit_demo.py` — layout 3 zones
- [ ] Streaming CoT (`st.write_stream`)
- [ ] Plotly graphes 21 jours
- [ ] Score gauge animé
- [ ] Mockup notification iOS-style
- [ ] Sélecteur profil + bouton Lancer
- [ ] Footer logs (modèle/tokens/latence)
- [ ] Validation : démo Lucas comprise par un non-tech en 30s
- [ ] Tag git : `v0.5-ui`

## Phase 5 — Polish & hardening  (~4h)
- [ ] Run de stabilité 10× par profil
- [ ] Mode `--cached` pour rejouer outputs LLM
- [ ] Gestion d'erreur OpenAI (timeout, rate limit)
- [ ] Logs propres en terminal
- [ ] Validation : 10/10 Lucas > 0.65 ; 10/10 Emma < 0.40
- [ ] Tag git : `v0.6-stable`

## Phase 6 — Backup vidéo + répétitions  (~3h)
- [ ] Enregistrement Loom 60-90s (Lucas)
- [ ] `PRESENTATION_SCRIPT.md`
- [ ] Bouton "Play backup video" dans Streamlit
- [ ] 3 répétitions chronométrées
- [ ] Q&A drill (4 questions CLAUDE.md §11)

## Buffer (Day 9-10)
- [ ] Imprévus inévitables
