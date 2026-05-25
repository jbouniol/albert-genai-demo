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

## Phase 2 — Skills + premier agent (Analyzer)  (~5h) — 🟡 CODE DONE, BLOQUÉ SUR QUOTA OPENAI
- [x] 4 skills markdown : grooming.md, harassment.md, addiction.md, normal_life_event.md (~200 mots chacun, signaux nommés en kebab-case)
- [x] Extension `models.py` : Baseline, Signal, AnalysisResult (Pydantic frozen, compatible `responses.parse` strict)
- [x] `src/sentinel/tools/baseline.py` — compute_baseline (jours 0-13)
- [x] `src/sentinel/tools/summary.py` — summarize_window (texte ~1700 chars avec deltas, peak hours, response time first_7 vs last_7, contacts established vs emerged)
- [x] `src/sentinel/llm/client.py` — ajout méthode `parse()` (wrapper sur `responses.parse` avec text_format Pydantic)
- [x] `src/sentinel/agents/base.py` — BaseAgent (ABC, charge les skills depuis filesystem)
- [x] `src/sentinel/agents/analyzer.py` — Analyzer (charge les 4 skills, calcule baseline+summary, appelle parse() avec AnalysisResult)
- [x] `scripts/run_analyzer.py` — CLI avec affichage Rich (Panel overall + Table signals)
- [x] Validation summary visuelle sur les 3 profils : signatures claires et différenciées
- [ ] **BLOQUÉ** : compte OpenAI en `insufficient_quota` → recharger sur https://platform.openai.com/account/billing
- [ ] **À FAIRE PAR JO après recharge** : `"/Users/jo/Desktop/Intro to GenAI/.uv/bin/python" scripts/run_analyzer.py lucas` → vérifier ≥3 signaux grooming + matches_normal_life_event=False
- [ ] **À FAIRE PAR JO après recharge** : idem sur emma (→ matches_normal_life_event=True) et mia (→ ≥2 signaux harassment)
- [ ] Tag git : `v0.3-analyzer`

## Phase 3 — Multi-agent + LangGraph  (~5h) — 🟡 CODE DONE, BLOQUÉ SUR QUOTA OPENAI
- [x] Collector, Scorer, Communicator (pattern BaseAgent)
- [x] AgentState TypedDict (LangGraph-compatible)
- [x] `src/sentinel/orchestrator/graph.py` — LangGraph (5 nodes: __start__, collector, analyzer, scorer, communicator)
- [x] Edge conditionnel score>0.65 → Communicator
- [x] `scripts/run_cli_demo.py`
- [x] PNG du graphe (`graph.png`, 17920 bytes, via mermaid.ink)
- [x] `ScoreResult` model (score, level: WATCH/MONITOR/ALERT/HIGH_ALERT, rationale)
- [x] Ruff vert + import sanity check OK
- [ ] **BLOQUÉ** : même quota OpenAI insuffisant → recharger sur https://platform.openai.com/account/billing
- [ ] **À FAIRE PAR JO après recharge** : `"/Users/jo/Desktop/Intro to GenAI/.uv/bin/python" scripts/run_cli_demo.py lucas` → vérifier 4 agents, score ≥0.65, notif parent visible
- [ ] **À FAIRE PAR JO après recharge** : idem emma → score ≤0.40, Communicator skip
- [ ] **À FAIRE PAR JO après recharge** : idem mia → score 0.55-0.70
- [ ] Tag git : `v0.4-mvp` ⭐

## Phase 4 — UI Streamlit split-screen  (~8h) — 🟡 CODE DONE, BLOQUÉ SUR QUOTA OPENAI
- [x] `app/streamlit_demo.py` — layout 4 zones (charts/reasoning haut, gauge/notif bas)
- [x] Streaming CoT token-par-token sur le **Communicator** (decision : prose pure, plus dramatique que JSON Analyzer)
- [x] `LLMClient.stream_call()` via `responses.stream()` + fallback `text_stream`
- [x] `Communicator.run(on_text_delta=...)` route vers stream_call quand callback fourni
- [x] Plotly graphes 21 jours : sleep+screen dual-axis, app sessions stacked area, contacts heatmap
- [x] Score gauge Plotly Indicator avec 4 zones colorées (WATCH/MONITOR/ALERT/HIGH_ALERT)
- [x] Mockup notification iOS-style (HTML dark mode inline)
- [x] Sélecteur profil + toggle cached + bouton Run dans sidebar
- [x] Footer caption : modèles + latence + mode (cached/live)
- [x] `plotly>=5.20` ajouté à pyproject.toml + installé (6.7.0)
- [x] Streamlit bumped >=1.32 ; passage à `width="stretch"` (deprecation use_container_width)
- [x] Ruff vert ; import smoke test OK
- [ ] **BLOQUÉ** : quota OpenAI (même blocker que Phase 2/3)
- [ ] **À FAIRE PAR JO après recharge** : `"/Users/jo/Desktop/Intro to GenAI/.uv/bin/python" -m streamlit run app/streamlit_demo.py` → tester Lucas, vérifier streaming visible
- [ ] Validation : démo Lucas comprise par un non-tech en 30s
- [ ] Tag git : `v0.5-ui`

## Phase 5 — Polish & hardening  (~4h) — 🟡 CODE DONE, BLOQUÉ SUR QUOTA OPENAI
- [x] `CachedLLMClient(LLMClient)` subclass — override `call`/`parse`/`stream_call`
- [x] Cache key = `(profile_id, agent_name)` ; path `data/llm_cache/{profile_id}/{agent}.{json|txt}`
- [x] Stream replay : `time.sleep(0.005)` char-par-char → effet typing préservé en cached
- [x] `SentinelLLMError` typed (timeout/ratelimit/quota/unknown) ; classification dans `_classify_openai_error`
- [x] `_safe()` wrapper dans LLMClient autour de chaque appel OpenAI
- [x] Quiet mode via `SENTINEL_QUIET=1` env → `Console(quiet=True)` ; Streamlit l'active automatiquement
- [x] Streamlit affiche erreur friendly + bouton "Switch to cached mode and rerun"
- [x] `scripts/stability_run.py` — 10× par profil, asserts par profil (Lucas>0.65 10/10, Emma<0.40 10/10, Mia harassment ≥8/10), seed cache avec `--seed-cache`
- [x] `data/llm_cache/` déjà gitignored
- [x] Ruff vert ; CLI help de stability_run OK
- [ ] **BLOQUÉ** : quota OpenAI
- [ ] **À FAIRE PAR JO après recharge** : `python scripts/stability_run.py --runs 10 --seed-cache` (~$1.50, peuple le cache pour la démo)
- [ ] **À FAIRE PAR JO après recharge** : toggle cached dans Streamlit → vérifier réponse <2s + effet typing préservé
- [ ] Validation : 10/10 Lucas > 0.65 ; 10/10 Emma < 0.40 ; Mia harassment ≥8/10
- [ ] Tag git : `v0.6-stable`

## Phase 6 — Backup vidéo + répétitions  (~3h)
- [ ] Enregistrement Loom 60-90s (Lucas)
- [ ] `PRESENTATION_SCRIPT.md`
- [ ] Bouton "Play backup video" dans Streamlit
- [ ] 3 répétitions chronométrées
- [ ] Q&A drill (4 questions CLAUDE.md §11)

## Buffer (Day 9-10)
- [ ] Imprévus inévitables
