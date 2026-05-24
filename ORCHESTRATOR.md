# ORCHESTRATOR.md — Règles multi-agents (Sentinel Demo)

Règles d'orchestration pour ce projet. Les règles générales du projet sont dans `CLAUDE.md`.

---

## §1 — Orchestrator-Worker Pattern

Toute tâche multi-étapes suit ce schéma :

```
Orchestrateur (ce contexte principal)
  ├── Analyse la tâche → définit la stratégie → décompose en sous-tâches
  ├── Lance les sous-agents EN PARALLÈLE (jamais en série quand c'est possible)
  ├── Synthétise les résultats
  └── Décide si un tour supplémentaire est nécessaire

Sous-agents (workers)
  ├── Opèrent de façon indépendante dans leur périmètre
  ├── Exécutent 3+ tool calls en parallèle quand possible
  ├── Retournent des résultats filtrés et structurés (jamais de dump brut)
  └── Chacun a son propre contexte isolé
```

### Sélection du modèle par rôle

| Rôle | Modèle | Pourquoi |
|------|--------|----------|
| Orchestrateur | Opus | Planification stratégique, synthèse multi-sources |
| Worker spécialisé | Sonnet | Exécution focalisée sur un domaine précis |
| Extraction simple | Haiku | Pattern matching, formatage, lookups rapides |

⚠️ Distinct des modèles LLM **runtime** de l'agent Sentinel (cf. `CLAUDE.md` §3) — ici on parle des sous-agents Claude Code utilisés en développement.

---

## §2 — Effort Scaling

Calibrer le nombre d'agents à la complexité réelle. Ne pas sur-agenter les tâches simples.

| Complexité | Agents | Tool calls / agent | Quand l'utiliser |
|------------|--------|--------------------|-----------------|
| **Simple** | 1 | 3-10 | Lookup, fix d'un seul fichier, recherche rapide |
| **Modérée** | 2-4 | 10-15 chacun | Comparaison, changement multi-fichiers, investigation |
| **Complexe** | 5-10+ | Responsabilités divisées | Pipeline complet, refacto multi-agents, debug end-to-end |

**Règle** : Si un agent avec 3 tool calls peut résoudre le problème, ne pas en lancer cinq.

### Exemples pour ce projet

| Tâche | Complexité | Agents recommandés |
|-------|------------|-------------------|
| Corriger un bug dans `scorer.py` | Simple | 1 |
| Ajouter un nouveau profil de démo (data + tests) | Modérée | 2 (générateur + tests) |
| Implémenter un nouvel agent LangGraph end-to-end | Complexe | 4-5 (model + agent + graph wiring + UI + tests) |
| Audit complet avant soutenance (3 profils × stabilité) | Complexe | 3 workers parallèles (un par profil) + 1 synthèse |

---

## §3 — Enveloppe de tâche pour les sous-agents

Chaque sous-agent DOIT recevoir une enveloppe complète. Pas de délégations vagues.

| Champ | Requis | Description |
|-------|--------|-------------|
| **Objectif** | Oui | Ce qu'il faut trouver ou faire — précis et borné |
| **Format de sortie** | Oui | Comment structurer la réponse (tableau, liste, code, diff) |
| **Outils / sources** | Oui | Quels outils utiliser, quels fichiers prioriser |
| **Périmètre** | Oui | Ce qu'il ne faut PAS faire — évite les chevauchements |

**Mauvais** : "Améliore le scorer"
**Bon** : "Dans `src/sentinel/agents/scorer.py`, ajoute la pondération par signal listée dans `src/sentinel/skills/grooming.md`. Retourne un diff. Ne modifie ni l'Analyzer ni les tests — un autre agent gère la couverture test."

---

## §4 — Parallélisation

Grouper toutes les opérations indépendantes dans un seul message :

- Greps, lectures, éditions indépendants → parallèle
- Lancements d'agents indépendants → parallèle
- Opérations dépendantes (ex: lire un fichier avant de l'éditer) → séquentiel

**Ne jamais sérialiser ce qui peut tourner en parallèle.**

---

## §5 — Protocole de communication

### Sous-agent → Orchestrateur
- Retourner des **résultats filtrés** avec compression intelligente
- Ne jamais dumper l'output brut des outils — résumer et structurer
- Signaler l'incertitude : "Trouvé X mais impossible de confirmer Y"

### Orchestrateur → Utilisateur
- Aller droit au but : la réponse d'abord, pas le processus
- Partager les découvertes, pas la mécanique
- Calibrer la narration à la complexité : fix simple = "Fait." / investigation complexe = partager les étapes clés

---

## §6 — Spécifique Sentinel

- **Aucun sous-agent ne contourne les Hard Constraints** de `CLAUDE.md` §6 (privacy, métadonnées only, pas de `chat.completions`, etc.)
- Un sous-agent qui touche au code LLM doit utiliser le wrapper `LLMClient` — jamais d'instanciation directe d'`OpenAI()`
- Pour tout changement sur les agents LangGraph (`collector/analyzer/scorer/communicator`), vérifier que la chain-of-thought reste streamée et loggée
- Avant d'élargir le scope, relire `tasks/todo.md` — pas de feature creep hors démo
