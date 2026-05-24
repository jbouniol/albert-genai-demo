# CLAUDE.md — Sentinel Demo Project

> Constitution du projet pour Claude Code.
> Lis ce fichier intégralement avant toute modification.
> Toute déviation des règles "Hard Constraints" doit être explicitement justifiée et validée.
> Les règles d'orchestration multi-agents sont dans `ORCHESTRATOR.md`.

---

## 0. DÉMARRAGE DE SESSION

1. Lire `tasks/lessons.md` — appliquer toutes les leçons avant de toucher quoi que ce soit
2. Lire `tasks/todo.md` — comprendre l'état actuel
3. Si aucun des deux n'existe, les créer avant de commencer

---

## 0.1 WORKFLOW

### 1. Planifier d'abord
- Passer en mode plan pour toute tâche non triviale (3+ étapes)
- Écrire le plan dans `tasks/todo.md` avant d'implémenter
- Si quelque chose ne va pas, STOP et re-planifier — ne jamais forcer

### 2. Stratégie sous-agents
- Utiliser des sous-agents pour garder le contexte principal propre
- Une tâche par sous-agent
- Investir plus de compute sur les problèmes difficiles
- Voir `ORCHESTRATOR.md` pour les règles détaillées de délégation

### 3. Boucle d'auto-amélioration
- Après toute correction : mettre à jour `tasks/lessons.md`
- Format : `[date] | ce qui a mal tourné | règle pour l'éviter`
- Relire les leçons à chaque démarrage de session

### 4. Standard de vérification
- Se demander : « Est-ce qu'un staff engineer validerait ça ? »

### 5. Exiger l'élégance
- Pour les changements non triviaux : existe-t-il une solution plus élégante ?
- Si un fix semble bricolé : le reconstruire proprement
- Ne pas sur-ingénieriser les choses simples

### 6. Correction de bugs autonome
- Quand on reçoit un bug : le corriger directement
- Aller dans les logs, trouver la cause racine, résoudre
- Pas besoin d'être guidé étape par étape

---

## 0.2 PRINCIPES FONDAMENTAUX

- **Simplicité d'abord** — toucher un minimum de code
- **Pas de paresse** — causes racines uniquement, pas de fixes temporaires
- **Ne jamais supposer** — vérifier chemins, APIs, variables avant utilisation
- **Demander une seule fois** — une question en amont si nécessaire, ne jamais interrompre en cours de tâche

---

## 0.3 GESTION DES TÂCHES

1. **Planifier** → `tasks/todo.md`
2. **Vérifier** → confirmer avant d'implémenter
3. **Suivre** → marquer comme terminé au fur et à mesure
4. **Expliquer** → résumé de haut niveau à chaque étape
5. **Apprendre** → `tasks/lessons.md` après corrections

---

## 0.4 APPRENTISSAGES

(Claude remplit cette section au fil du temps)

---

## 1. CONTEXTE DU PROJET

### Cadre académique
- **Cours** : Introduction to GenAI 2026 — projet final
- **Livrable** : 10 min de présentation + 5 min de Q&A devant jury
- **Critères d'évaluation** : nécessité d'un agent, faisabilité technique, valeur business, profondeur de réflexion, anticipation Q&A
- **Bonus** : mockup + démo concrète

### Sujet — Agent "Sentinel"
Agent IA de **sécurité numérique pour adolescents** (marché US) qui détecte 3 risques comportementaux — **grooming, cyberharcèlement, addiction** — en analysant **exclusivement les métadonnées comportementales** (jamais le contenu des messages).

### Différenciateurs clés à marteler
1. **Privacy-by-design** : métadonnées only → à la fois USP business ET anti-prompt-injection by construction
2. **Baseline comportementale + LLM** : capable de distinguer "période d'examens" de "addiction" — impossible en rule-based
3. **Architecture multi-agent avec HITL calibré** : autonome sur collecte/analyse, humain dans la boucle au-dessus de 0.65

### Objectif spécifique de ce repo
Construire **la démo de 2 minutes** qui sera projetée pendant la soutenance. Le reste (slides, mockup parent) est traité ailleurs.

---

## 2. CAHIER DES CHARGES DE LA DÉMO

### Ce que la démo DOIT démontrer (non-négociable)
- [ ] **Vrai appel API OpenAI** visible dans les logs (pas de mock LLM)
- [ ] **Chain-of-thought streamée en temps réel** sur l'écran
- [ ] **Score de risque calculé** par LLM (donc non-déterministe, donc différent à chaque run = c'est le but)
- [ ] **3 profils de démo** différenciants : Emma (RAS), Lucas (grooming), Mia (harcèlement)
- [ ] **UI projetable en split-screen** : données comportementales (gauche) | raisonnement agent (droite) | score + alerte (bas)
- [ ] **Multi-agent orchestré** avec LangGraph (Collector → Analyzer → Scorer → Communicator)
- [ ] **Mockup notification parent** affichée en climax sur le profil Lucas
- [ ] **Logs structurés** de chaque chain-of-thought (auditable = guardrail démo)

### Ce qui PEUT être mocké (assumé, légitime)
- Données mobiles (générateur Python de 21 jours de métadonnées synthétiques)
- Interface mobile parent (composant HTML/Streamlit statique)
- Pas de vraie API iOS/Android/DNS

### Ce qui doit FONCTIONNER en moins de 90 secondes par profil
La démo doit tourner end-to-end en moins de 90s. Le jury n'attend pas.
Si un appel LLM prend 30s, on streame pour donner l'illusion de progression.

### Backup obligatoire
Une **vidéo Loom de 60-90 sec** enregistrée à l'avance au cas où la démo plante en live.
Génère le script d'enregistrement après la première démo qui tourne stable.

---

## 3. ARCHITECTURE TECHNIQUE

### Stack
- **Python** 3.11+
- **OpenAI** (>= 1.50) — endpoint `client.responses.create` (NOUVELLE API, pas chat.completions)
- **LangGraph** (>= 0.2) — state graph pour orchestration multi-agent
- **Pydantic** v2 — tous les data models
- **Streamlit** — UI démo (split-screen, projetable)
- **Rich** — logs colorés en terminal pour debug
- **python-dotenv** — gestion des clés API
- **Pytest** — tests unitaires sur la logique non-LLM

### Modèles LLM par agent (optimisation coût)
| Agent | Modèle | Pourquoi |
|---|---|---|
| Collector | `gpt-4o-mini` | Tâche structurelle simple, pas de raisonnement |
| Analyzer | `gpt-4o` | Raisonnement contextuel sur les patterns |
| Scorer | `gpt-4o` | Évaluation nuancée + explainability |
| Communicator | `gpt-4o-mini` | Rédaction du message parent, pas critique |

Coût estimé/run de démo : **~$0.05** (négligeable).

### Architecture multi-agent

```
┌──────────────────────────────────────────────────────┐
│              LANGGRAPH ORCHESTRATOR                  │
│                                                       │
│   ┌──────────┐    ┌──────────┐   ┌──────────┐       │
│   │COLLECTOR │───▶️│ANALYZER  │──▶️│ SCORER   │       │
│   │  Agent   │    │  Agent   │   │  Agent   │       │
│   └──────────┘    └──────────┘   └─────┬────┘       │
│        │               │                │            │
│        ▼               ▼                ▼            │
│   ┌────────────────────────────────────────┐         │
│   │            SHARED MEMORY                │         │
│   │  (baseline, history, chain-of-thought)  │         │
│   └────────────────────────────────────────┘         │
│                                         │            │
│                            score>0.65?  │            │
│                                         ▼            │
│                                  ┌──────────┐        │
│                                  │COMMUNIC. │        │
│                                  │  Agent   │        │
│                                  └──────────┘        │
└──────────────────────────────────────────────────────┘
```

### Rôle de chaque agent

#### COLLECTOR
- **Input** : profil utilisateur + 21 jours de métadonnées brutes
- **Output** : metadata structurée (Pydantic `MetadataWindow`)
- **Tools** : `fetch_screentime`, `fetch_dns`, `aggregate_by_day`
- **LLM use** : minimal — surtout pour normaliser des formats hétérogènes

#### ANALYZER
- **Input** : `MetadataWindow` du Collector + baseline historique
- **Output** : liste de signaux détectés avec leurs justifications
- **Tools** : `compute_baseline`, `detect_drift`, `pattern_match`
- **LLM use** : raisonnement principal — détecter les signatures comportementales
- **Skills** : `grooming.md`, `harassment.md`, `addiction.md`, `normal_life_event.md`

#### SCORER
- **Input** : signaux détectés
- **Output** : score 0.0–1.0 + niveau (WATCH/MONITOR/ALERT/HIGH ALERT) + explication
- **Tools** : `compute_score`, `explain_decision`
- **LLM use** : agrégation pondérée + justification en langage naturel

#### COMMUNICATOR (déclenché seulement si score > 0.65)
- **Input** : score + explication + profil parent
- **Output** : message de notification parent (court, factuel, non-anxiogène)
- **Tools** : `send_parent_notification` (mock dans la démo)
- **LLM use** : rédaction adaptée au ton attendu

### Memory
- **In-memory dict** pour la démo (pas de DB). Persistance entre runs via fichiers JSON dans `data/baselines/`.
- **Baseline par profil** : générée à partir des 14 premiers jours de données.
- **Sliding window de 7 jours** pour la détection de drift.
- ⚠️ Mentionner dans la slide architecture que la **summary périodique** serait la stratégie anti-context-rot en prod (cf. cours).

---

## 4. STRUCTURE DU REPO

```
sentinel-demo/
├── CLAUDE.md                      ← ce fichier
├── README.md                      ← quickstart pour le jury si on partage le repo
├── pyproject.toml                 ← deps + config ruff
├── .env.example                   ← OPENAI_API_KEY=...
├── .gitignore
│
├── src/sentinel/
│   ├── __init__.py
│   │
│   ├── agents/                    ← un fichier par agent
│   │   ├── __init__.py
│   │   ├── base.py                ← BaseAgent (wrapper LLM commun + logging)
│   │   ├── collector.py
│   │   ├── analyzer.py
│   │   ├── scorer.py
│   │   └── communicator.py
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── graph.py               ← LangGraph state machine
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── models.py              ← tous les Pydantic models
│   │   ├── generator.py           ← générateur de données synthétiques
│   │   └── profiles/
│   │       ├── emma.json          ← profil "normal"
│   │       ├── lucas.json         ← profil "grooming"
│   │       └── mia.json           ← profil "harassment"
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── fetch_data.py
│   │   ├── baseline.py
│   │   ├── drift.py
│   │   └── notify.py
│   │
│   ├── skills/                    ← skills = instructions en markdown (cours)
│   │   ├── grooming.md
│   │   ├── harassment.md
│   │   ├── addiction.md
│   │   └── normal_life_event.md
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   └── store.py               ← MemoryStore simple
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py              ← wrapper OpenAI responses.create + logging
│   │
│   └── config.py                  ← settings, modèles par agent, thresholds
│
├── app/
│   └── streamlit_demo.py          ← UI démo
│
├── tests/
│   ├── test_generator.py
│   ├── test_baseline.py
│   └── test_scorer.py
│
├── scripts/
│   └── run_cli_demo.py            ← fallback terminal si Streamlit plante
│
└── data/
    └── baselines/                 ← baselines générées (gitignored)
```

---

## 5. CONVENTIONS DE CODE

### Style
- **Type hints partout** (Python 3.11+, syntaxe moderne : `list[str]`, `dict[str, X]`, `X | None`)
- **Pydantic v2** pour tous les data models — pas de dict nu pour les objets métier
- **Docstrings** sur chaque agent et fonction publique : rôle + inputs + outputs + tools utilisés
- **Logger structuré** via `structlog` ou `logging` standard — JAMAIS `print()` dans le code métier
- **Ruff** pour lint + format (config dans pyproject.toml)

### Pattern obligatoire — chaque appel LLM passe par le wrapper

```python
# src/sentinel/llm/client.py
from openai import OpenAI

class LLMClient:
    """Wrapper unique pour tous les appels OpenAI. Logge tout."""
    
    def __init__(self, model: str):
        self.client = OpenAI()
        self.model = model
    
    def call(self, instructions: str, user_input: str, ...) -> Response:
        # 1. Log de l'input
        # 2. Appel client.responses.create(...)
        # 3. Log de la chain-of-thought + output
        # 4. Return structured response
```

**Aucun agent n'instancie OpenAI directement.** Tout passe par `LLMClient`.

### Pattern agent

```python
class BaseAgent:
    name: str
    model: str
    skills: list[Path]  # markdown files
    
    def run(self, state: AgentState) -> AgentState:
        """Lit state, appelle LLM, retourne new state."""
```

### Skills = fichiers markdown (alignement cours)
Pas de skill hardcodé dans le code Python. Toujours dans `src/sentinel/skills/*.md`.
Format strict :
```markdown
# Skill: <nom>
## Objective
## When to use
## Step-by-step instructions
1. ...
2. ...
## Output format
## Examples
```

---

## 6. HARD CONSTRAINTS (Guardrails projet)

### Privacy & sécurité — non-négociable
- ❌ **NEVER** lire ou logger le contenu de messages textuels (même synthétiques). Métadonnées only.
- ❌ **NEVER** exposer la clé API OpenAI dans les logs ou les artefacts de démo.
- ✅ Tous les outils sont **whitelistés** dans une liste explicite. Pas d'exécution arbitraire.
- ✅ Le `Communicator` ne s'active **que si score > 0.65** (HITL trigger).

### Cours — alignement explicite
- ✅ Architecture = LLM + Planner + Memory + Tools/Skills (formule du cours)
- ✅ Skills en markdown séparés (clarté métier > magie LLM)
- ✅ Observabilité totale : chaque chain-of-thought loggée et auditable
- ✅ Optimisation tokens : modèle différencié par agent (cf. tableau §3)
- ❌ Pas d'OpenClaw / accès OS / exécution shell par l'agent

### Démo — non-négociable
- ✅ Vrai appel LLM (chain-of-thought visible dans la démo, pas en arrière-plan)
- ✅ 3 profils visibles dans un menu déroulant Streamlit
- ✅ Total de runtime par profil < 90s
- ✅ Vidéo de backup enregistrée avant la soutenance

---

## 7. WHAT NOT TO DO

- ❌ **Ne pas surcomplexifier**. C'est une démo de 2 min, pas un produit.
- ❌ **Ne pas mocker le LLM** — le jury doit voir un vrai appel API.
- ❌ **Ne pas ajouter de DB** (SQLite, etc.). In-memory + JSON suffit.
- ❌ **Ne pas faire d'authentification**, de multi-utilisateurs, de gestion de session.
- ❌ **Ne pas utiliser `chat.completions`** — le cours enseigne `responses.create`, on suit.
- ❌ **Ne pas afficher la chain-of-thought comme un bloc** — STREAMER pour l'effet visuel.
- ❌ **Ne pas demander à un LLM d'écrire les skills** (cours explicite : c'est inutile). Écrits à la main, révisés par LLM OK.
- ❌ **Ne pas ajouter de features hors scope démo** (mobile app, vraie API iOS, dashboard parent complet…).

---

## 8. COMMANDES STANDARD

```bash
# Setup
make install              # installe les deps via uv ou pip
cp .env.example .env      # puis ajouter OPENAI_API_KEY

# Développement
make demo                 # lance Streamlit sur localhost:8501
make demo-cli profile=lucas   # fallback terminal
make test                 # pytest -v
make lint                 # ruff check + ruff format

# Génération de données (one-time)
make generate-profiles    # régénère les 3 profils JSON
make generate-baselines   # calcule baselines à partir des profils
```

---

## 9. SCÉNARIOS DE DÉMO — Source de vérité

### Profil 1 — Emma, 14 ans, "RAS"
- Pattern : usage stable, contacts connus, horaires réguliers
- Score attendu : **0.15–0.30 (WATCH)**
- Verdict agent : "Comportement aligné avec baseline. Variation normale liée aux examens."
- **Rôle dans la démo** : montrer que l'agent ne crie pas au loup à tort. Crédibilité.

### Profil 2 — Lucas, 15 ans, "GROOMING"
- Pattern : nouveau contact "Jake_M_15" sur Discord J-21, fréquence ↑, horaires de plus en plus tardifs (23h → 2h), switch vers Snapchat à J-14, baisse des interactions avec amis habituels
- Score attendu : **0.72–0.85 (ALERT/HIGH ALERT)**
- Verdict agent : explication détaillée avec les 5 signaux corrélés
- Notification parent : message non-anxiogène, factuel, suggère une conversation
- **Rôle dans la démo** : LE moment fort. Le climax.

### Profil 3 — Mia, 13 ans, "HARCÈLEMENT"
- Pattern : pic de messages d'un contact connu (camarade de classe), réponses tardives anormales, baisse de sommeil, baisse d'usage d'apps sociales habituelles (retrait)
- Score attendu : **0.55–0.70 (MONITOR/ALERT)**
- Verdict agent : pattern différent du grooming — explique la nuance
- **Rôle dans la démo** : démontrer l'adaptabilité de l'agent. Pas du pattern-matching naïf.

---

## 10. CHECKLIST AVANT LA SOUTENANCE

- [ ] Les 3 profils tournent end-to-end sans erreur
- [ ] Le score Lucas est systématiquement > 0.65 sur 10 runs consécutifs
- [ ] Le score Emma est systématiquement < 0.40 sur 10 runs consécutifs
- [ ] Le coût total des 3 démos cumulées < $0.50
- [ ] Logs Rich propres en terminal pour debug live si besoin
- [ ] Vidéo Loom enregistrée
- [ ] README court avec quickstart si on partage le repo au jury
- [ ] Slide architecture avec screenshot du LangGraph exact
- [ ] Mockup notification parent intégré dans Streamlit

---

## 11. QUESTIONS Q&A À ANTICIPER (à garder en tête pendant le dev)

1. **"Comment vous êtes sûrs que l'agent ne part pas en cacahuètes ?"**
   → Compte utilisateur de l'agent (droits limités), HITL >0.65, observabilité totale, scope tools whitelisté, pas d'accès au contenu donc impossible de manipuler par prompt injection.

2. **"Pourquoi un agent et pas du rule-based ?"**
   → Les signatures grooming/harcèlement/addiction se chevauchent contextuellement. Voir profils Emma vs Lucas : mêmes pics nocturnes en période d'examens vs grooming. Un if/then classerait Noël comme crise d'addiction.

3. **"Pourquoi multi-agent et pas un seul gros LLM ?"**
   → Séparation des responsabilités + optimisation coût (modèle par agent) + maintenabilité (test/release indépendant — slide du cours).

4. **"Et les hallucinations ?"**
   → Seuils étagés + HITL + chain-of-thought auditable + revue mensuelle automatique des FP/FN.

---

*Fichier vivant. À mettre à jour à chaque décision d'architecture.*