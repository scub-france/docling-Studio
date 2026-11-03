# Rapport de re-audit : KISS (Keep It Simple, Stupid)

> **Re-audit de `claude/nifty-turing-fmn3wo` @ `a4d9679` — score 75 → 83**

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Type** : re-audit après remédiation
**Référence** : rapport initial `release-0.7.4/04-kiss.md` (code `1de1929`, rapport `e6047c2` ; 75/100, GO CONDITIONNEL, 0 CRIT, 1 MAJ, 2 MIN, 7 INFO)
**Remédiation examinée** : `git log e6047c2..a4d9679` (100 commits ; aucun changement de code entre `1de1929` et `e6047c2`).

Commits pertinents pour cet audit :

| Commit | Objet | Écart visé |
|--------|-------|------------|
| `2ce5cf1` | Suppression de l'enum `LLMProviderType`, du tag `type`, de `health_check`, des deux gardes et de `LLM_PROVIDER_TYPE` | MAJ 4.2 (option B) |
| `fd4c7e1` | `providerType` devient une constante du service | MAJ 4.2 |
| `b181c22` | Commentaire de `OllamaProbe` sans renvoi à `health_check` | INFO 4.2 |
| `04866fa`, `8ea22af` | `MCP_MAX_READ_TOKENS` ramené dans [100, 32000] au démarrage, documenté | MIN 4.5 (point 1) |
| `0277562` | Le plafond de rounds n'est plus énoncé que par le prompt | MIN 4.5 (point 2) |

Commits examinés pour l'abstraction qu'ils introduisent : `cb1e3b9` (`ServiceError`), `7a1f4d5` (`ProvidedKeysModel`), `c59b076` (`_BoundedBodyRoute`), `39dcda5` (ports `VectorStorePool` / `GraphDriverPool`), `2892b8c` (`EditJournal`), `44d0e2f` (coercitions `__post_init__`), `e331670` (`FileStorage`).

Méthode :
- Chaque écart du rapport 0.7.4 est re-vérifié dans le code de `a4d9679`.
- Nouveaux écarts cherchés par les greps de la fiche, l'inventaire AST des enums par nombre de membres, le balayage AST des relais purs (même script appliqué à `e6047c2` et à `a4d9679`), le contrôle de lecture des champs `Settings`.
- Exécution ciblée des seules fonctions pures `Settings.from_env` et `validate_mcp_config`.
- Application non lancée, suites non relancées. Résultats du coordinateur sur HEAD : backend `ruff check` / `ruff format --check` OK, pytest **1673 passed, 19 skipped** ; frontend eslint, prettier, vue-tsc OK, vitest **522 passed** (53 fichiers).

---

## Score de compliance

| Métrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 6 / 8 | **7 / 8** |
| Score | 75 / 100 | **83 / 100** |
| Écarts CRITICAL | 0 | 0 |
| Écarts MAJOR | 1 | 1 (la carte de citation, reclassée : voir ci-dessous) |
| Écarts MINOR | 2 | 0 |
| Écarts INFO | 7 | 10 |

Poids total : 12. Poids conformes : 10. Seul l'item 4.2 (poids 2) reste non conforme. `score = 10 / 12 * 100 = 83,3` → **83**.

**Même lecture qu'en 0.7.4.** Le rapport initial posait : « Tant que la carte reste, l'item 4.2 reste non conforme, même si le MAJ est soldé » et « Les points 1 et 2 [du MIN config] suffiraient à reclasser le résiduel en INFO ». Les deux sont appliqués tels quels. La trajectoire annoncée (« Item 4.5 conforme → 83 ») est atteinte.

**Reclassement de la carte de citation (MIN → MAJ).** Le constat est identique à 0.7.4. Elle était classée MIN parce qu'elle s'ajoutait à un item déjà porté non conforme par le MAJ LLM-provider. Ce MAJ étant corrigé, elle est désormais la seule cause de non-conformité de 4.2 (poids 2), et la fiche impose « Tout item de poids 2 non conforme = écart [MAJ] ». Ce n'est pas une aggravation. Son retrait est une décision laissée au mainteneur.

| # | Item | Poids | 0.7.4 | Re-audit | Justification |
|---|------|-------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Oui | Grep de la fiche : `AppStateBuilder` seul (`bootstrap/builder.py:74`), composition root déjà validée. Les abstractions ajoutées par la remédiation sont proportionnées (INFO dédié). |
| 4.2 | Résout le problème actuel | 2 | **Non** | **Non** | MAJ LLM-provider **corrigé** (option B). Reste la carte de citation désactivée par défaut, décision mainteneur. |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | Oui (INFO) | Oui (INFO) | Relais purs (même script AST) : 22 → 23, le seul ajout étant `ChunkService._journal`, qui lie l'acteur (`chunk_service.py:291-293`). Aides mortes inchangées (INFO). |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (INFO) | Oui (INFO) | Pont MCP Apps toujours fait main (INFO). La remédiation reprend le verrou pdfium de Docling (`infra/pdfium_lock.py:16-19`) et le garde SSRF existant plutôt que d'en écrire de nouveaux. |
| 4.5 | Configuration simple | 1 | **Non** | **Oui** | Points 1 et 2 de la remédiation 0.7.4 faits : borne de `MCP_MAX_READ_TOKENS` alignée sur le panneau, plafond de rounds énoncé à un seul endroit. Résidu en INFO. |
| 4.6 | Pas d'indirection inutile | 2 | Oui | Oui | Chemins inchangés en profondeur. `ServiceError` retire des `try/except` des routeurs ; `FileStorage` et `PdfInspector` remplacent des appels disque / pdfium faits dans le service (exigence des audits 01 / 06), sans couche de plus sur le chemin d'une requête. |
| 4.7 | Pas de méta-programmation | 2 | Oui | Oui | Grep de la fiche : 0 en production (faux positif `tests/test_chunking.py:460`). Un `@model_serializer(mode="wrap")` (`api/schemas.py:76`), point d'extension documenté de Pydantic, et quatre `object.__setattr__` en `__post_init__` de dataclasses gelées : idiomes standard, pas de métaclasse ni de décorateur maison. |
| 4.8 | Structures les plus simples | 1 | Oui | Oui | Rien de nouveau ; `BudgetedRead` et `EditJournal` sont des dataclasses gelées. |

### Métriques de périmètre

| Mesure | 0.7.4 (`1de1929`) | Re-audit (`a4d9679`) |
|--------|-------------------|----------------------|
| Variables d'env distinctes lues par `infra/settings.py` (1) | 45 | **45** (−`LLM_PROVIDER_TYPE`, +`MAX_IMPORT_TABLE_CELLS`) |
| Valeurs MCP surchargeables à chaud | 4 | 4 |
| Représentations de la config MCP | 3 | 3 |
| Endroits qui **énoncent** le plafond de rounds au modèle | 2 (instructions figées au boot + prompt) | **1** (le prompt, valeur effective) |
| Validations de `MCP_MAX_READ_TOKENS` divergentes | 2 (`>= 1` vs [100, 32000]) | **0** (ramené dans [100, 32000], `< 1` refusé) |
| Enums à un seul membre (backend, AST) | 1 (`LLMProviderType`) | **0** |
| Relais purs, même script AST (production) | 22 (2) | 23 |
| Cartes MCP Apps (lignes) | 2 365 | 2 389 (1 194 + 1 195) |
| Lignes identiques entre les deux cartes (difflib, blocs ≥ 3, même script) | 160 | 160 |
| Champs `Settings` jamais lus hors `settings.py` | 0 | 0 (mais 3 lus sans effet : voir INFO nouveau) |

(1) Noms distincts passés à `os.environ.get("…")`, extraits par regex tolérant le retour à la ligne, sur les deux commits.
(2) Le rapport 0.7.4 annonçait 17 avec un autre script ; le script de ce re-audit, appliqué à `e6047c2`, en trouve 22. La comparaison vaut à méthode égale.

---

## Écarts constatés

### [MAJ] Carte de citation conservée mais désactivée par défaut (`MCP_CITATION_CARD=false`) — décision mainteneur

**Statut vs 0.7.4 : inchangé sur le fond, reclassé MIN → MAJ** (voir l'encadré « Reclassement » ci-dessus). Seul changement : ses quatre messages d'erreur anglais sont passés en français (`1b9b59f`, audit 03).

- **Localisation** :
  - `document-parser/infra/settings.py:127-130` et `:311`
  - `document-parser/mcp_adapter/apps.py:74` (`CitationView`), `:141-142`, `:146-228`
  - `document-parser/mcp_adapter/citation_app.html` (1 194 lignes)
  - `document-parser/services/citation_service.py:55` (`get_citation`, unique appelant de production `apps.py:168`)
  - `docs/mcp-server.md:50`, `:158`
- **Constat** :
  - `show_citation`, `get_citation_image`, le template, `CitationView` et `CitationService.get_citation` sont livrés et éteints par défaut. Le motif écrit est inchangé : « offered to a model, it was called on its own before every sources card, which already shows each cited passage boxed on its page » (`settings.py:127-129`, `docs/mcp-server.md:50`).
  - Aucun hôte ni besoin courant n'est nommé, ni dans le code, ni dans `docs/mcp-server.md`, ni dans le design #363.
  - Le flag apparaît dans 7 fichiers Python de production (`grep citation_card`) et 3 fichiers frontend.
- **Règle violée** : item 4.2 — « Le code résout le problème actuel, pas un problème hypothétique futur » (poids 2).
- **Remédiation** : inchangée. Retirer la carte (template, deux outils, `get_citation`, `CitationView`, `MCP_CITATION_CARD`, `McpServerStatus.citation_card`, ligne du panneau) en gardant `CitationImageService.render_page`, utilisé par `show_sources`. **Effort M** (suppressions), risque faible (désactivée par défaut). Cela supprime aussi la seconde copie du pont MCP Apps (INFO 4.4).
  - Si le mainteneur garde la carte, nommer dans `docs/mcp-server.md` l'hôte ou le cas d'usage qui la justifie lèverait l'objection de 0.7.4 (« aucun hôte ni besoin courant n'y est nommé »). Ce serait un changement de lecture : 4.2 conforme, **83 → 100**.

### [INFO] Résidu de l'abstraction LLM-provider : un port à deux propriétés et un champ d'affichage constant

**Nouveau, résidu attendu de l'option B** (le MAJ 0.7.4 est **corrigé**).

- **Vérification du MAJ 0.7.4** (code actuel) :
  - **Enum** : `LLMProviderType` n'existe plus (inventaire AST des enums : aucune à un membre ; `grep LLMProviderType` hors `tests/` : 0).
  - **Port** : `LLMProvider` réduit à `host` et `default_model_id`, sans tag ni `health_check` (`domain/ports.py:488-502`). La docstring dit pourquoi un second backend n'est pas préparé : docling-agent ne pilote qu'Ollama (`:491-495`).
  - **Adaptateur** : `OllamaProvider` ramené à 22 lignes, deux propriétés (`infra/llm/ollama_provider.py:11-22`).
  - **Gardes** : celles de la factory et du runner ont disparu (`grep NotImplementedError\|LLM_PROVIDER` sur `infra/docling_agent_reasoning.py` et `bootstrap/` : 0).
  - **Knob** : `LLM_PROVIDER_TYPE` n'est plus lu (`settings.py:63-64`, absent de `from_env`). Des tests épinglent qu'il est ignoré (`tests/test_settings.py:190`, `tests/test_reasoning_factory.py:23`). Le changement est annoncé en BREAKING au CHANGELOG.
  - **Constante** : `providerType` est désormais `_PROVIDER_TYPE = "ollama"` (`services/app_config_service.py:56-58`, `:188`). Le paramètre `provider_type` du constructeur a disparu.
- **Résidu** :
  - le champ `providerType` reste dans le contrat (`domain/app_config.py:63`, `api/schemas.py:740`, `:755`) et le panneau affiche « Provider: ollama » (`frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:153`), comme prévu par l'option B ;
  - le design #317, marqué Implemented, décrit encore `LLM_PROVIDER_TYPE` comme un réglage en lecture seule (`docs/design/317-admin-panel-runtime-reasoning-config.md:44`, `:90`, `:493`). Relève de l'audit 11.
- **Règle violée** : item 4.2 — observation.
- **Remédiation** : aucune requise. Option A (retrait de `providerType` du contrat) si le panneau est revu.

### [INFO] Configuration MCP : trois représentations et des défauts répétés (résidu du MIN 4.5)

**Statut vs 0.7.4 : MIN corrigé, reclassé en INFO** comme le prévoyait le rapport initial.

- **Corrigé** :
  1. **Validation unique de `MCP_MAX_READ_TOKENS`** : `Settings.__post_init__` appelle `_clamp_mcp_max_read_tokens` (`settings.py:136-137`, `:212-234`). Il utilise les bornes du domaine (`READ_TOKENS_MIN` / `MAX`, `:13-14`) et journalise un avertissement ; une valeur `< 1` reste une erreur de démarrage (`:175-176`). Ramener la valeur dans les bornes plutôt que la refuser était l'une des deux options du rapport 0.7.4 ; les déploiements existants démarrent donc toujours.
     - **Vérifié par exécution** des fonctions pures : `MCP_MAX_READ_TOKENS=50` donne 100, avec le warning « MCP_MAX_READ_TOKENS=50 is outside 100-32000; using 100 », et `validate_mcp_config(McpRuntimeConfig(5, 100, "", enabled=False))` renvoie `[]` ; `99999` donne 32000 ; `0` lève `ValueError: mcp_max_read_tokens must be >= 1`.
     - L'interrupteur On/Off du panneau ne peut donc plus échouer en 400 à cause de la valeur d'env (enchaînement HTTP non exécuté).
     - Documenté : `docs/mcp-server.md:47`.
  2. **Plafond de rounds énoncé à un seul endroit** : les instructions serveur n'en donnent plus (« stop at the round cap the chunkless_rag prompt states », `mcp_adapter/server.py:62`), avec la raison écrite dans la docstring (`:81-90`). Le prompt lit la valeur effective à chaque rendu (`server.py:125`, `:206-217` ; `prompts.py:74`, `:83`, `:91`), comme la carte des sources (`sources_mapping.py:34-36`). La divergence HTTP / stdio du plafond annoncé disparaît du même coup.
- **Reste** (sans complexité nouvelle) :
  - **Trois représentations** : `Settings.mcp_*` (`settings.py:115-121`) → `env_mcp_config()` (`bootstrap/factories.py:249-260`) → `resolve_mcp_config` (`services/mcp_config_service.py:76`) puis `NavigationConfig.from_runtime` (`services/navigation_config.py:65-72`).
  - **Défauts répétés** :
    - `5` rounds : `settings.py:121`, `:314`, `navigation_config.py:25`, `frontend/src/features/mcp-config/store.ts:17` ;
    - `4000` tokens : `settings.py:118`, `:313`, `navigation_config.py:32`, `store.ts:17`.
  - **`ASK_MODE`** reste une chaîne à deux valeurs (`settings.py:77`, `:195-196`, `:276`).
  - **Deux régimes** pour la même variable : `< 1` est refusé, `1-99` est relevé à 100. Documenté.
- **Règle violée** : item 4.5 — observation.
- **Remédiation** : facultative. Lire les défauts de `navigation_config` depuis `Settings`, ou l'inverse (S) ; `ASK_ENABLED` avec alias (M, non prioritaire).

### [INFO] Abstractions introduites par la remédiation : proportionnées, un paramètre de compatibilité superflu

**Nouveau.** Réponse à la question « la remédiation a-t-elle ajouté de l'abstraction superflue ? » : **non, à un détail près**.

| Abstraction | Localisation | Ce qu'elle remplace | Verdict |
|-------------|--------------|---------------------|---------|
| `ServiceError` + un handler | `services/errors.py:14-26`, `api/errors.py:24-30` | Un `try/except` par famille d'erreurs dans chaque routeur (`cb1e3b9` : `api/stores.py` −54/+30, `api/document_chunks.py` −53/+13) | **Simplifie.** Une classe de base à un attribut, un handler de 2 lignes. Coexiste encore avec des mappings locaux (`api/analyses.py` : 13 `except`/`HTTPException`, `api/documents.py` : 25), sans couche de plus. |
| `ProvidedKeysModel` | `api/schemas.py:64-79` ; sous-classes `:361`, `api/graph.py:28`, `:42` | Des `dict` libres dans la réponse (audit 07) | **Justifié.** 16 lignes pour garder le JSON identique en émettant les seules clés fournies. `response_model_exclude_unset=True` sur la route, l'outil standard, s'appliquerait aussi aux modèles parents (`GraphEdge.order`, champs par défaut de `StoreResponse`) et changerait le JSON. `always_emitted` ne sert qu'une fois (`api/graph.py:50`). |
| `_BoundedBodyRoute` / `_BoundedBodyRequest` | `api/analyses.py:31-82` | Rien : nouvelle borne de corps (audit 08) | **Justifié.** C'est l'extension « custom APIRoute / Request » documentée par FastAPI. La docstring explique pourquoi une dépendance arriverait trop tard (`:62-68`). Limité à un routeur. Petit couplage à l'attribut interne `_body` de Starlette (`:51-58`), comme dans l'exemple officiel. |
| Ports `VectorStorePool`, `GraphDriverPool` | `domain/ports.py:420-450` ; `services/store_backend_resolver.py:40-44`, `:84-85` | Annotations `TYPE_CHECKING` sur des classes `infra/` | **Proportionné.** Un `Protocol` à une méthode chacun, uniquement pour les annotations, sans indirection à l'exécution. Ils servent la règle « aucun import infra dans `services/` », gardée par un test. Contexte d'ingestion déprécié : ils partiront avec lui en 0.8.0. |
| `EditJournal` | `domain/chunk_editing.py:154-219` | Une fabrique `journal_entry` à 10 paramètres | **Simplifie** : chaque appel tient sur une ligne (6 dans `chunk_service.py`, 2 dans `version_service.py:158-168`). **Détail superflu** : le champ `new_id: Callable[[], str]` n'existe que pour que le restore garde des ids hex (`version_service.py:41-42`, `:158`) quand les autres lignes prennent des uuid4 avec tirets (`chunk_editing.py:154-155`). Deux formats d'id coexistent dans `chunk_edits` sans lecteur qui en dépende (non vérifié en base). |
| Coercitions `__post_init__` des VO navigation | `domain/navigation.py:227-229`, `:292-294`, `:313-315` ; `domain/source_map.py:79-82` | — | **Évitable.** Quatre coercitions laissent des producteurs internes, dont un du domaine (`outline_builder.py:57`, `:68`, `:113`), passer des chaînes au lieu des membres d'enum. Suivi dans l'audit 02 (INFO). |

- **Règle violée** : items 4.1 / 4.2 — observation.
- **Remédiation** (S, facultative) : retirer `new_id` d'`EditJournal` et laisser le restore prendre des uuid4 comme les autres lignes, après vérification qu'aucun lecteur ne dépend du format ; passer les membres d'enum dans `outline_builder.py`.

### [INFO] Trois variables d'environnement lues sans effet (nouveau constat, préexistant)

**Nouveau.** Le code est antérieur à 0.7.4 ; il apparaît maintenant que la remédiation documente chaque variable (`d5e26d0`).

- **Localisation** :
  - `docs/configuration.md:62-70` (section « Read but unused »)
  - `document-parser/infra/settings.py:82-85`, `:99`, `:159-164`, `:281-282`, `:292`
  - `document-parser/main.py:154-157`, `:169`
  - `document-parser/api/schemas.py:90-91`, `:107`
  - `frontend/src/features/feature-flags/store.ts:104-107`, `:125`, `:174`
- **Constat** :
  - `MAX_PASTE_IMAGE_SIZE_MB` et `PASTE_ALLOWED_IMAGE_TYPES` sont lues, validées (une valeur invalide empêche le démarrage), puis renvoyées par `/api/health`, sans aucun lecteur dans `frontend/src` (grep hors tests : 0).
  - `LINKED_MODE_ENABLED` alimente un flag `linkedMode` que rien ne consulte : aucun `isEnabled('linkedMode')`, et `modeFlags()` ne renvoie que `parse`.
  - La doc le dit elle-même : « changing them changes nothing in the app ».
  - Ceci nuance le point positif 0.7.4 « Config sans champ mort », exact au sens « champ lu hors de `settings.py` » (`main.py` les lit), mais pas au sens « champ qui a un effet ».
- **Règle violée** : item 4.2 (déjà non conforme) — observation.
- **Remédiation** (S) : retirer les trois variables, leurs champs `HealthResponse` et le flag `linkedMode`, avec une entrée « Removed » ; ou les rattacher à la fonction qu'elles devaient régler.

### [INFO] Pont MCP Apps (JSON-RPC sur postMessage) écrit à la main et présent en deux copies

**Statut vs 0.7.4 : inchangé.**

- **Localisation** :
  - `document-parser/mcp_adapter/citation_app.html:690-770` (`post`, `call`, `settle`, `handshake`) et `:1082` (`reportSize`) ;
  - `document-parser/mcp_adapter/sources_app.html:991-1065` et `:1096`.
- **Constat** :
  - 160 lignes identiques par blocs de 3 lignes ou plus, même chiffre à `e6047c2` et à `a4d9679` avec le même script.
  - Le choix « pas de SDK `@modelcontextprotocol/ext-apps`, pas de build » n'est toujours pas écrit (`apps.py:1-22` justifie un template par vue).
- **Remédiation** : inchangée (documenter le choix ; la suppression de la carte de citation retire la seconde copie).

### [INFO] Aides mortes et relais sans valeur ajoutée

**Statut vs 0.7.4 : inchangé.**

- **Localisation** :
  - `document-parser/mcp_adapter/wire.py:72` et `document-parser/mcp_adapter/wire_mapping.py:42` (`_neutralise_all`, défini deux fois, 0 appelant) ;
  - `document-parser/mcp_adapter/server.py:93` (`INSTRUCTIONS = instructions(apps=False)`, 0 lecteur) ;
  - `document-parser/mcp_adapter/prompts.py:52-53` (`_default_rounds`) ;
  - `document-parser/services/mcp_config_service.py:100-106` (`load_effective_mcp_config`) et `:186-188` (`server_status`, justifié) ;
  - `document-parser/services/app_config_service.py:146-147` (`_require_writable`) ;
  - `document-parser/infra/serve_converter.py:95-98` (`merge_batches`, inatteignable).
- **Constat** : les mêmes qu'en 0.7.4, vérifiés par grep. Le commit `0277562` a réécrit `instructions()` sans retirer la constante `INSTRUCTIONS`. Les autres relais purs (`DoclingTreeReader`, façades `find_*`) restent justifiés.
- **Remédiation** : inchangée (supprimer `_neutralise_all` ×2 et `INSTRUCTIONS`, sans risque).

### [INFO] `PageRasterizer.crop(box, fmt)` : généralité résiduelle après le retrait du mode crop

**Statut vs 0.7.4 : inchangé.**

- **Localisation** : `document-parser/domain/ports.py:564-572` ; `document-parser/infra/page_raster.py:42` ; `document-parser/services/citation_image_service.py:91` ; `document-parser/domain/navigation.py:245`, `:258`
- **Constat** : toujours un recadrage de la page entière avec la boîte sentinelle `(0, 0, 10_000, 10_000)` pour réencoder en WEBP ; `RasterCrop.png` / `CitationImage.png` portent des octets WEBP. La réécriture de `render_page` (rendu depuis le chemin, `78af645`) n'a pas touché ce point.
- **Remédiation** : inchangée.

### [INFO] Repli d'environnement de développement dans le chemin de production — désormais dans un port

**Statut vs 0.7.4 : inchangé sur le fond, formalisé.**

- **Localisation** : `document-parser/domain/ports.py:714-718` ; `document-parser/infra/file_storage.py:39-49` ; `document-parser/services/document_service.py:262`, `:266` ; `document-parser/services/citation_image_service.py:74`, `:90` ; `document-parser/services/source_service.py:142-155`
- **Constat** :
  - Le repli « base créée sous Docker, worktree lancé sur l'hôte » fait désormais partie du contrat du port `FileStorage.resolve`.
  - Il reste partiel : les rendus MCP (`citation_image_service`, `source_service`) lisent `storage_path` tel quel.
  - Comportement identique à l'ancien `DocumentService.resolve_storage_path` : seul le nom de fichier est cherché dans le répertoire de stockage (`file_storage.py:40-49`).
- **Remédiation** : inchangée (configuration ou migration des chemins), ou appliquer `resolve` partout si le repli est assumé.

### [INFO] Taxonomie `ReasoningStepKind` à 7 valeurs alors qu'une seule est émise — reconduit de 0.7.0

**Statut vs 0.7.4 : inchangé.** `domain/value_objects.py:194-209` ; seule émission `domain/trace_builder.py:60`.

### [INFO] `StepId` (`RootModel[str]`) — enveloppe cosmétique — reconduit de 0.7.0

**Statut vs 0.7.4 : inchangé.** `document-parser/api/schemas.py:609-616`, wrap `:662`.

---

## Delta vs 0.7.4

Score : **75 → 83 (+8)**. Items conformes : 6/8 → 7/8. Écarts : 0 CRIT / 1 MAJ / 2 MIN / 7 INFO → 0 CRIT / 1 MAJ / 0 MIN / 10 INFO.

| Écart 0.7.4 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] Abstraction LLM-provider prématurée | **Corrigé** (option B) | Enum absente (AST) ; `ports.py:488-502` ; `ollama_provider.py:11-22` ; `settings.py:63-64` ; `app_config_service.py:56-58`. Résidu INFO (`providerType` constant). |
| [MIN] Configuration MCP en couches | **Corrigé**, résidu en INFO | Borne : `settings.py:212-234`, vérifiée par exécution. Plafond : `server.py:62`, `:81-90`. |
| [MIN] Carte de citation désactivée conservée | **Inchangé**, reclassé **MAJ** (seule cause de 4.2) | `settings.py:127-130`, `apps.py:141-228`. Décision mainteneur. |
| [INFO] Pont MCP Apps en double | Inchangé | 160 / 160 lignes identiques |
| [INFO] Aides mortes et relais | Inchangé | `server.py:93`, `wire.py:72`, `wire_mapping.py:42` |
| [INFO] `crop` résiduel | Inchangé | `citation_image_service.py:91` |
| [INFO] Repli de chemin de dev | Inchangé, formalisé dans `FileStorage.resolve` | `ports.py:714-718` |
| [INFO] `ReasoningStepKind` à 7 valeurs | Inchangé | `value_objects.py:194-209` |
| [INFO] `StepId` | Inchangé | `schemas.py:609` |
| [INFO] `LLMProvider.health_check()` mort | **Corrigé** | Absent du port et d'`OllamaProvider` ; `ServeConverter.health_check` (`serve_converter.py:189`) reste suivi par l'audit 06. |

**Nouveaux constats** : 3 INFO, aucun CRIT, MAJ ou MIN.
- Résidu LLM-provider (attendu).
- Évaluation des abstractions ajoutées, avec le paramètre `new_id` d'`EditJournal` superflu.
- Trois variables d'env lues sans effet (code préexistant).

**Régression** : aucune. La remédiation n'introduit ni pattern superflu, ni couche de plus sur le chemin d'une requête, ni méta-programmation. Elle retire une enum, un knob, deux gardes, une méthode morte et une validation en double.

---

## Points positifs

- **Dette la plus ancienne de l'audit soldée.** Le MAJ LLM-provider, constaté depuis 0.7.0 (4 rapports), est fermé selon l'option B recommandée :
  - le port garde ce que le runner lit, et sa docstring dit pourquoi un second backend n'est pas préparé ;
  - des tests épinglent que la variable est ignorée ;
  - le changement est annoncé en BREAKING.
- **Une source de vérité pour le plafond de rounds** : le texte figé au boot n'énonce plus de nombre et renvoie au prompt, qui lit la valeur effective. Le correctif est petit, documenté (`server.py:81-90`) et sans nouveau mécanisme.
- **Borne de lecture alignée par les constantes du domaine** (`settings.py:13-14`), pas par une copie des nombres. La valeur est ramenée dans les bornes plutôt que refusée, pour ne casser aucun démarrage. Le tout est vérifié par exécution et par un test (`tests/test_settings.py:278-298`).
- **Abstractions de la remédiation proportionnées** : chacune remplace plus de code qu'elle n'en ajoute (`ServiceError`, `EditJournal`) ou ne s'utilise qu'en annotation (ports pools). Les points d'extension choisis sont les points documentés de FastAPI et de Pydantic.
- **Outils standard réutilisés** : verrou pdfium de Docling (`infra/pdfium_lock.py:16-19`), garde SSRF commun à la sonde Ollama et aux stores, `asyncio.to_thread` pour le comptage de pages.
- **Moins de code** : `chunk_service.py` passe de 1 019 à 311 lignes, dont les règles vont dans de petits modules purs du domaine ; quatre composants Vue morts et leurs traductions sont supprimés (`frontend/src` : 1 927 lignes retirées, 344 ajoutées).
- **Zéro méta-programmation** (item 4.7) et toujours aucune classe ni bus d'événements côté frontend.

---

## Verdict partiel : GO

- Aucun écart CRITICAL.
- Un seul écart MAJOR (la carte de citation, décision laissée au mainteneur), sous le seuil bloquant (> 3).
- Score 83 / 100 ≥ 80.

Les deux conditions techniques du rapport 0.7.4 sont remplies : MAJ LLM-provider soldé, double validation de `MCP_MAX_READ_TOKENS` corrigée. La troisième (« statuer sur la carte de citation ») reste au mainteneur.

Pour atteindre 100, une seule action :
- **retirer la carte de citation** (effort M, suppressions, risque faible) ;
- ou, si elle reste, **nommer dans la doc le besoin qui la justifie** : ce serait un changement de lecture de 4.2, à acter explicitement.

Hygiène sans effet sur le score (S) :
- supprimer `INSTRUCTIONS` et `_neutralise_all` ×2 ;
- retirer les trois variables lues sans effet ;
- retirer `new_id` d'`EditJournal`.
