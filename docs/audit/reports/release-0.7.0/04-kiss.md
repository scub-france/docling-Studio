# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 8 |
| Score | 83 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 3 |

Poids total de la checklist : 12. Poids conformes : 10 (seul l'item 4.2, poids 2,
est non conforme). `score = 10 / 12 * 100 = 83`.

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui |
| 4.2 | Resout le probleme actuel, pas hypothetique futur | 2 | **Non** |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | Oui |
| 4.4 | Outils standard avant solutions maison | 1 | Oui |
| 4.5 | Configuration simple | 1 | Oui |
| 4.6 | Pas d'indirection inutile | 2 | Oui |
| 4.7 | Pas de meta-programmation / magie | 2 | Oui |
| 4.8 | Structures de donnees les plus simples | 1 | Oui |

---

## Ecarts constates

### [MAJ] Genericite prematuree de l'abstraction LLM-provider (un seul backend realisable)

- **Localisation** : `document-parser/domain/value_objects.py:167`, `document-parser/domain/ports.py:311`, `document-parser/infra/docling_agent_reasoning.py:137`, `document-parser/infra/settings.py:49`
- **Constat** : une pile d'abstraction complete est en place pour selectionner un backend LLM alors qu'un seul est realisable aujourd'hui :
  - `LLMProviderType` (`value_objects.py:167`) est une `StrEnum` a **un seul membre** (`OLLAMA = "ollama"`, ligne 177) ;
  - le port `LLMProvider` (`ports.py:311`) expose un tag `type` (ligne 329) dont l'unique consommateur est un garde de dispatch `if provider.type is not LLMProviderType.OLLAMA: raise NotImplementedError` (`docling_agent_reasoning.py:137-140`) ;
  - un knob d'environnement `LLM_PROVIDER_TYPE` (`settings.py:53`, defaut `"ollama"`) selectionne ce provider unique, avec un commentaire qui l'assume explicitement : *« kept as a config knob to make the LLMProvider abstraction visible and prepare the ground for additional backends »* (`settings.py:49-52`).
  Les docstrings confirment que le second backend exige un support amont docling-agent inexistant (`ports.py:320-325`, `value_objects.py:170-175`). L'abstraction, l'enum, le garde runtime et la variable d'env resolvent donc un probleme futur hypothetique, pas le besoin actuel (Ollama uniquement).
- **Regle violee** : item 4.2 — « Le code resout le probleme actuel, pas un probleme hypothetique futur (pas de genericite prematuree) » (poids 2).
- **Remediation** : soit assumer Ollama en dur tant qu'aucun autre backend n'est realisable (supprimer l'enum a un membre, le tag `type` et le knob `LLM_PROVIDER_TYPE`, garder `OllamaProvider` concret) ; soit, si la couture doit rester visible pour l'architecture hexagonale, la reduire au strict port `LLMProvider` sans enum de dispatch ni selecteur d'environnement, et documenter la decision comme dette assumee. Risque de release faible (code bien documente, hors chemin chaud), a traiter dans le cycle suivant.

---

### [INFO] Taxonomie `ReasoningStepKind` a 7 valeurs alors qu'une seule est emise

- **Localisation** : `document-parser/domain/value_objects.py:207` (backend), `frontend/src/features/reasoning/types.ts:6`, `frontend/src/features/reasoning/kindColors.ts:14`
- **Constat** : `ReasoningStepKind` declare 7 kinds (PLAN/RETRIEVE/RERANK/READ/VERIFY/ANSWER/MAP) et la table `KIND_TO_ELEMENT` (`kindColors.ts:14-22`) mappe une couleur pour chacun, alors que la docstring reconnait que « docling-agent's chunkless RAG loop only emits READ steps today; the other kinds are reserved » (`value_objects.py:211-213`) et que `trace_builder._read_step` code en dur `kind=ReasoningStepKind.READ`. Meme theme que l'ecart 4.2 : taxonomie construite pour des phases d'agent qui n'existent pas encore.
- **Regle violee** : item 4.2 (deja comptabilise non conforme) — observation d'appoint, non bloquante.
- **Remediation** : conserver si l'alignement wire avec l'amont (docling-lens) est un contrat voulu ; sinon reduire l'union a `read` et l'etendre quand une phase reelle apparait. A minima documenter que 6 des 7 kinds sont morts a ce jour.

### [INFO] `StepId` (`RootModel[str]`) — enveloppe cosmetique autour d'une simple chaine

- **Localisation** : `document-parser/api/schemas.py:527`
- **Constat** : `class StepId(RootModel[str])` enveloppe l'identifiant de step (`"s1"`, `"s2"`, …) uniquement pour lui donner un nom dans le schema OpenAPI (docstring lignes 528-532). Le domaine type ce champ en `str` nu (`value_objects.py:252`) et le front en `string` (`types.ts:32`) ; l'enveloppe impose un `StepId(step.id)` au wrap (`schemas.py:580`) sans valeur runtime. Structure plus complexe que necessaire pour un besoin purement cosmetique de documentation.
- **Regle violee** : items 4.2 / 4.8 (deja couverts) — observation d'appoint, non bloquante.
- **Remediation** : remplacer `id: StepId` par `id: str` avec un `Field(description=...)` si l'on souhaite documenter le format, ce qui supprime le type wrapper et le wrap/unwrap.

### [INFO] `LLMProvider.health_check()` non utilise en production

- **Localisation** : `document-parser/domain/ports.py:337`, `document-parser/infra/llm/ollama_provider.py:41`
- **Constat** : `health_check()` est declare sur le port `LLMProvider` et implemente par `OllamaProvider`, mais aucun appelant de production ne l'invoque (le runner de reasoning ne lit que `type`, `host`, `default_model_id` ; seuls des tests appellent `health_check`). La verification de disponibilite reelle du daemon Ollama passe par un adaptateur distinct, `OllamaProbe.probe()` (`infra/llm/ollama_probe.py`), utilise par le panneau admin. `health_check` est donc une surface morte sur le port.
- **Regle violee** : item 4.2 — surface prevue pour un usage futur non concretise (non bloquant ; recoupe l'audit Clean Code pour le code mort).
- **Remediation** : retirer `health_check` du port et de `OllamaProvider` tant qu'aucun consommateur ne l'appelle, ou le cabler la ou une sonde de disponibilite du provider est reellement requise.

---

## Points positifs

- **Chemin d'execution du reasoning minimal et lisible** (item 4.6) : `api/reasoning.py` → `ReasoningService.run` (validation + timing + projection) → `ReasoningRunner.run` (adaptateur infra) → `domain.trace_builder.build_trace` (fonction pure). Chaque couche porte une responsabilite distincte, aucune traversee superflue.
- **`trace_builder` est une pure fonction sur value objects** (`domain/trace_builder.py`) — aucune dependance HTTP/DB/docling-agent, testable en isolation ; exactement le niveau de simplicite attendu.
- **Zero meta-programmation / magie** (item 4.7) : aucune metaclasse, aucun `__init_subclass__`, aucun `exec`/`eval`, aucun `type(...)` dynamique dans le perimetre. Les seuls decorateurs sont standards (`@runtime_checkable`, `@dataclass`, `@property`, routeurs FastAPI).
- **Outils standard privilegies** (item 4.4) : `urllib.parse` pour la validation d'URL, `importlib.metadata` pour la provenance, `asyncio.to_thread` pour deporter l'appel synchrone LLM, `httpx` pour les sondes, `color-mix` CSS natif pour les teintes de badge, `computed`/`ref`/`reactive` Pinia natifs cote front. Aucune reimplementation maison.
- **Config runtime #317 justifiee par le besoin** (item 4.5) : la table `app_settings` + `AppConfigService` + precedence (db sur env) + hot-rebuild existent parce que l'exigence est une reconfiguration a chaud via le panneau admin sans redemarrage — une simple variable d'env ne couvre pas ce besoin. Lectures tolerantes (fallback env sur ligne illisible), ecritures strictes : precedence claire, pas de sur-ingenierie.
- **`AppStateBuilder` est un vrai composition root, pas un Builder superflu** (item 4.1) : il possede la sequence de boot et sert le hot-rebuild #317 via un unique `dataclasses.replace` + rebind atomique, ce qui remplace ~150 lignes de `app.state.x = y` non typees.
- **`AppState` frozen + `deps.require(...)`** : conteneur immuable type, chaque slot optionnel etroitise en un service non-optionnel a un seul endroit ; indirection utile, pas gratuite.
- **`_import_deps()` source unique du contrat de dependances** : `run()` et `deps_present()` passent par la meme fonction, ce qui empeche la derive entre le check de boot et ce qui s'execute reellement — simplicite au service de la robustesse.

---

## Verdict partiel : GO

Aucun ecart CRITICAL. Un seul ecart MAJOR (genericite prematuree de l'abstraction
LLM-provider, item 4.2), non bloquant (seuil MAJ bloquant = > 3). Score 83 / 100
(>= 80). Les 3 observations INFO recoupent le meme theme de scaffolding anticipe
et sont a nettoyer dans un cycle ulterieur, sans impact release.
