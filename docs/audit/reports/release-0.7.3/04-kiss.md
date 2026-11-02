# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`,
avec un examen approfondi du delta depuis 0.7.2 (`caddf30..02adc68`) : serveur MCP
(`mcp_adapter/`, `mcp_stdio.py`, `bootstrap/mcp_mount.py`), nouveaux modules de domaine
(`source_map`, `outline_locate`, `source_bar`, `quote_marks`, …), services de navigation,
panneau d'administration MCP (`/api/config/mcp`, `/api/mcp/server`, `features/mcp-config/`),
`ASK_MODE`, analyse par lot, import d'analyses Docling, fusion des lots (#344).
Methode : analyse statique uniquement (application non lancee, suites de tests non executees).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 8 |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 7 |

Poids total de la checklist : 12. Poids conformes : 9 (items 4.2, poids 2, et 4.5, poids 1,
non conformes). `score = 9 / 12 * 100 = 75`.

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui |
| 4.2 | Resout le probleme actuel, pas hypothetique futur | 2 | **Non** |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | Oui (cf. INFO) |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (cf. INFO) |
| 4.5 | Configuration simple | 1 | **Non** |
| 4.6 | Pas d'indirection inutile | 2 | Oui |
| 4.7 | Pas de meta-programmation / magie | 2 | Oui |
| 4.8 | Structures de donnees les plus simples | 1 | Oui |

### Metriques de perimetre

| Mesure | 0.7.2 | 0.7.3 |
|--------|-------|-------|
| Variables d'environnement lues par `infra/settings.py` | 34 | **42** (+8 : 7 `MCP_*` + `ASK_MODE`) |
| Valeurs MCP surchargeables a chaud (table `app_settings`, namespace `mcp`) | — | 4 (`enabled`, `max_rounds`, `max_read_tokens`, `studio_base_url`) |
| Representations de la config MCP | — | 3 (`Settings.mcp_*` → `McpRuntimeConfig` → `NavigationConfig`) |
| Code Python MCP (adapter + stdio + mount) | — | 1 820 lignes |
| Services de navigation / config MCP | — | 1 639 lignes |
| Nouveaux modules de domaine (navigation, sources, ancres…) | — | 2 127 lignes |
| Cartes MCP Apps (HTML/CSS/JS autonomes) | — | 2 365 lignes (1 177 + 1 188) |
| Feature frontend `mcp-config` (hors tests) | — | 1 423 lignes |
| Resultats des greps de la fiche (4.1 / 4.7) | `AppStateBuilder` seul / 0 | `AppStateBuilder` seul / 1 `setattr` trivial (`main.py:52`) |

---

## Ecarts constates

### [MAJ] Genericite prematuree de l'abstraction LLM-provider (un seul backend realisable) — reconduit de 0.7.0

- **Localisation** : `document-parser/domain/value_objects.py:167`, `document-parser/domain/ports.py:345`, `document-parser/infra/docling_agent_reasoning.py:137`, `document-parser/bootstrap/factories.py:103`, `document-parser/infra/settings.py:51`
- **Constat** : strictement inchange depuis 0.7.0 (aucun diff `v0.7.0..HEAD` sur `value_objects.py`, `docling_agent_reasoning.py`, `infra/llm/`). La pile complete est toujours en place pour choisir un backend LLM alors qu'un seul est realisable :
  - `LLMProviderType` est une `StrEnum` a **un seul membre** (`OLLAMA`, `value_objects.py:177`), la docstring l'assume : « Other variants are kept here to make the abstraction visible and prepare future backends » ;
  - le port `LLMProvider` (`ports.py:345`) porte un tag `type` (`ports.py:362`) dont le seul consommateur est un garde `NotImplementedError` (`docling_agent_reasoning.py:137-140`) ;
  - le knob `LLM_PROVIDER_TYPE` (`settings.py:55`, lu `settings.py:230`) est commente « kept as a config knob to make the LLMProvider abstraction visible and prepare the ground for additional backends » (`settings.py:51-54`) ;
  - le cas « provider non Ollama » est garde **deux fois** : par comparaison de chaine dans la factory (`factories.py:103-110`) puis par l'enum dans le runner (`docling_agent_reasoning.py:137`) ;
  - la valeur remonte jusqu'au panneau d'admin (`builder.py:217` → `ReasoningConfigResponse.provider_type`, `api/schemas.py:697` → `ReasoningConfigSection.vue:153`, « Provider: ollama »), un champ d'affichage qui ne peut prendre qu'une valeur.
- **Regle violee** : item 4.2 — « Le code resout le probleme actuel, pas un probleme hypothetique futur (pas de genericite prematuree) » (poids 2).
- **Remediation** : inchangee depuis 0.7.0 — soit assumer Ollama en dur (supprimer l'enum a un membre, le tag `type`, le knob `LLM_PROVIDER_TYPE`, le double garde et le champ `providerType` du panneau), soit reduire la couture au seul port `LLMProvider` sans enum de dispatch ni selecteur d'env et documenter la dette. Hors chemin chaud, risque release faible, mais c'est la deuxieme release consecutive ou la dette est reportee : a planifier explicitement (0.8.0).

---

### [MIN] Configuration MCP en couches : 8 variables d'env, 3 representations, un knob « live » qui ne l'est qu'a moitie

- **Localisation** : `document-parser/infra/settings.py:90-122` et `:253-274`, `document-parser/bootstrap/factories.py:240`, `document-parser/domain/mcp_config.py:41`, `document-parser/services/mcp_config_service.py:76`, `document-parser/services/navigation_config.py:25` et `:64`, `document-parser/bootstrap/mcp_mount.py:98-101`, `document-parser/mcp_stdio.py:63-78`, `document-parser/infra/settings.py:67`
- **Constat** :
  - **Surface** : la release ajoute 8 variables d'env (34 → 42) : `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, `MCP_APPS_ENABLED`, `MCP_CITATION_CARD`, `MCP_MAX_READ_TOKENS`, `MCP_MAX_ROUNDS`, `MCP_STUDIO_BASE_URL`, `ASK_MODE`. Quatre valeurs MCP sont en plus surchargeables en base (`app_settings`, namespace `mcp`) via le panneau, avec precedence db > env, source par champ et reset.
  - **Trois representations pour quatre knobs** : `Settings.mcp_*` (`settings.py:96-122`) → `env_mcp_config()` construit un `McpRuntimeConfig` (`factories.py:240-251`, `mcp_config.py:41-50`) → `resolve_mcp_config` applique les lignes db (`mcp_config_service.py:76-97`) → `NavigationConfig.from_runtime` re-projette trois champs (`navigation_config.py:64-72`). Les valeurs par defaut sont repetees a chaque etage : `5` rounds (`settings.py:109`, `navigation_config.py:25`, defaut de `build_mcp_server` `server.py:102`, `prompts.py:52-53`, formulaire `features/mcp-config/store.ts:17`), `4000` tokens (`settings.py:106`, `navigation_config.py:32`, `store.ts:17`).
  - **`max_rounds` rendu « live » alors qu'il n'est ni applique ni entierement live** : rien ne l'impose cote serveur (`settings.py:107-108` : « Nothing enforces it server-side », idem `navigation_config.py:21-23`) ; c'est un nombre ecrit dans un texte. Sur HTTP, les *instructions* serveur sont figees au boot avec la valeur d'env (`mcp_mount.py:98-101`, `server.py:81-87`) tandis que le prompt et la carte lisent la valeur effective : apres une surcharge, le client voit deux plafonds differents. La doc le reconnait comme limite (« restart the backend, then the client, to align them », `docs/mcp-server.md:80-82`) — un knob a chaud qui exige un redemarrage pour etre coherent.
  - **Deux validations divergentes pour le meme knob** : `Settings` accepte `MCP_MAX_READ_TOKENS >= 1` (`settings.py:158-159`) alors que l'ecriture exige `[100, 32000]` (`mcp_config.py:34-35`, `mcp_config_service.py:148`). Le panneau renvoie le formulaire complet, y compris pour l'interrupteur On/Off (`store.ts:99-104`) : avec `MCP_MAX_READ_TOKENS=50` en env, tout PUT — y compris couper le serveur — serait refuse en 400 (PLAUSIBLE, deduit statiquement, non execute).
  - **Semantique differente selon le transport** : l'entree stdio resout la config effective mais ignore `config.enabled` et `MCP_ENABLED` (`mcp_stdio.py:63-78`) ; un serveur « Off » dans Settings continue de servir en stdio, et y annonce le plafond effectif alors que HTTP annonce celui d'env (`mcp_stdio.py:73-75`).
  - **`ASK_MODE`** est une chaine a deux valeurs (`"hidden"`/`"visible"`, `settings.py:67`, validee `:178-179`) la ou toutes les autres bascules sont des booleens `*_ENABLED` ; elle s'ajoute comme troisieme axe a `REASONING_ENABLED` et a la surcharge db `reasoning.enabled`, et masque la section Settings qui permettrait de couper le raisonnement que les routes continuent de servir (`settings.py:62-66`).
- **Regle violee** : item 4.5 — « Configuration simple — pas de systeme de config complexe la ou une variable d'env suffit » (poids 1).
- **Remediation** : (1) ne garder a chaud que ce qui est reellement applique au prochain appel (`max_read_tokens`, `studio_base_url`, l'interrupteur) et laisser `MCP_MAX_ROUNDS` en env seul — ou retirer le plafond des instructions pour qu'il ne vive qu'a un endroit ; (2) une seule source des bornes et des defauts (`domain/mcp_config.py`) reutilisee par `Settings.__post_init__` ; (3) faire respecter `enabled` par `mcp_stdio.py` (ou documenter que stdio l'ignore) ; (4) `ASK_MODE` → booleen `ASK_ENABLED` aligne sur les autres flags.

### [MIN] Carte de citation conservee mais desactivee par defaut (`MCP_CITATION_CARD=false`)

- **Localisation** : `document-parser/infra/settings.py:115-118`, `document-parser/mcp_adapter/apps.py:141-142` et `:146-228`, `document-parser/mcp_adapter/citation_app.html` (1 177 lignes), `document-parser/services/citation_service.py:57`
- **Constat** : `show_citation`, son outil app-only `get_citation_image`, le template `citation_app.html`, le DTO `CitationView` et le cas d'usage `CitationService.get_citation` (dont `apps.py:168` est l'unique appelant de production) sont livres mais **eteints par defaut**. Le motif est ecrit dans le code : « a model offered it called it on its own before every sources card, which already shows each cited passage boxed on its page » (`settings.py:115-117`, `apps.py:5-8`). La fonctionnalite est donc couverte par `show_sources` et gardee « au cas ou » : ~1 450 lignes (HTML + ~150 lignes Python + tests), un flag d'env, une ligne dans le panneau admin (`McpConfigSection.vue`, `restartOnly`) et une seconde copie du pont postMessage a maintenir (cf. INFO 4.4). Instance supplementaire de l'item 4.2 (deja non conforme) ; classee MIN et non MAJ parce qu'elle est opt-in, documentee (`docs/mcp-server.md:46`) et hors du chemin par defaut.
- **Regle violee** : item 4.2 — code qui resout un besoin hypothetique (« when the reader asks to see it ») deja couvert par l'existant (poids 2, item deja compte non conforme).
- **Remediation** : retirer la carte de citation (template, deux outils, `get_citation`, `MCP_CITATION_CARD`, ligne du panneau) et la ressortir de l'historique git le jour ou un hote en a besoin ; a defaut, statuer explicitement dans le design #363 sur sa conservation.

---

### [INFO] Pont MCP Apps (JSON-RPC sur postMessage) ecrit a la main et present en deux copies

- **Localisation** : `document-parser/mcp_adapter/citation_app.html:690-770` (`post`/`call`/`settle`/`handshake`), `document-parser/mcp_adapter/sources_app.html:984-1060`, `document-parser/mcp_adapter/citation_app.html:460` (`renderMarkdown`)
- **Constat** : chaque carte embarque sa propre implementation du protocole MCP Apps — table des requetes en attente avec timeout, poignee de main `ui/initialize` puis `ui/notifications/initialized`, contexte d'hote, dimensions, `reportSize` — en grande partie identique d'un fichier a l'autre (≈ 230 lignes communes). Le SDK client officiel des vues MCP Apps (`@modelcontextprotocol/ext-apps`) couvre exactement ce besoin ; les commentaires montrent le cout du fait-main (« This view used to send only the notification … That is why the page thumbnail never arrived », `citation_app.html:725-728`). La carte de citation ajoute un rendu Markdown/tableaux maison alors que la convention frontend est `marked`. Le choix a une justification reelle (templates statiques mono-fichier, pas de bundler cote backend, CSP par defaut sans script externe) mais il n'est documente nulle part.
- **Regle violee** : item 4.4 (conforme dans l'ensemble) — observation, non bloquante ; la duplication releve aussi de l'audit 05.
- **Remediation** : documenter le choix « pas de SDK, pas de build » dans `apps.py` ; si les deux cartes restent, factoriser le pont (fragment unique injecte a la lecture du template) ; la suppression de la carte de citation (MIN ci-dessus) supprime la seconde copie et le rendu Markdown maison.

### [INFO] Aides mortes et relais sans valeur ajoutee dans le nouveau code

- **Localisation** : `document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`, `document-parser/mcp_adapter/server.py:90`, `document-parser/mcp_adapter/prompts.py:52`, `document-parser/services/mcp_config_service.py:100` et `:186`, `document-parser/services/app_config_service.py:144`
- **Constat** : `_neutralise_all` est defini **deux fois** a l'identique (`wire.py:72`, `wire_mapping.py:42`) et appele nulle part ; la constante `INSTRUCTIONS = instructions(apps=False)` (`server.py:90`) n'a aucun lecteur, tests compris. Relais triviaux : `_default_rounds()` qui renvoie une constante (`prompts.py:52-53`), `load_effective_mcp_config` qui jette la moitie du tuple de `resolve_mcp_config` (`mcp_config_service.py:100-106`), `McpConfigService.server_status` qui ne fait qu'appeler le callable injecte (`:186-188`), `_require_writable` qui enveloppe `require_writable` (`app_config_service.py:144-145`). Aucun n'est sur un chemin chaud et le relais `server_status` sert a garder le SDK hors de `services/` ; l'item 4.3 reste conforme, mais les deux copies mortes de `_neutralise_all` et `INSTRUCTIONS` sont a supprimer (recoupe l'audit 03).
- **Regle violee** : item 4.3 (conforme dans l'ensemble) — observation.
- **Remediation** : supprimer `_neutralise_all` (×2) et `INSTRUCTIONS` ; remplacer `_default_rounds` par `lambda: MAX_ROUNDS` ou un defaut `None`.

### [INFO] `PageRasterizer.crop(box, fmt)` : generalite residuelle apres le retrait du mode crop

- **Localisation** : `document-parser/domain/ports.py:436`, `document-parser/infra/page_raster.py:35-64`, `document-parser/services/citation_image_service.py:91`
- **Constat** : le commit `dc54211` a retire le mode crop de `get_citation_image`, mais le port garde `crop(png, box, *, fmt="PNG")`. Son unique appel de production recadre la page entiere avec une boite sentinelle `(0, 0, 10_000, 10_000)` pour la reencoder en WEBP (`citation_image_service.py:91`) : le « crop » sert de transcodeur, le format par defaut `PNG` n'est jamais utilise en production, et la page est encodee en PNG par `render_page` puis decodee et reencodee. Le champ `CitationImage.png` porte en realite des octets WEBP.
- **Regle violee** : item 4.2 (deja compte) — observation d'appoint.
- **Remediation** : remplacer `crop` par un `render_page(..., fmt="WEBP")` (ou `encode_webp(png)`), supprimer la boite sentinelle et le parametre inutilise.

### [INFO] Repli d'environnement de developpement dans le chemin de production

- **Localisation** : `document-parser/services/document_service.py:119`, `document-parser/api/documents.py:186` et `:214`
- **Constat** : `resolve_storage_path` retente un fichier introuvable sous `UPLOAD_DIR/<basename>` pour le cas « base creee sous Docker (`/app/uploads/...`), worktree lance sur l'hote » (docstring `document_service.py:120-125`). C'est un probleme de poste de developpement resolu dans le code servi en production, et applique seulement a deux routes : `PdfPageRasterizer.render_page` (`infra/page_raster.py:27`) lit `storage_path` tel quel, donc les vignettes MCP ne beneficient pas du repli.
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : traiter ce cas par la configuration (`UPLOAD_DIR`/montage) ou un script de migration des chemins, plutot que par un repli silencieux partiel.

### [INFO] Taxonomie `ReasoningStepKind` a 7 valeurs alors qu'une seule est emise — reconduit de 0.7.0

- **Localisation** : `document-parser/domain/value_objects.py:207`, `frontend/src/features/reasoning/types.ts:6`, `frontend/src/features/reasoning/kindColors.ts:14`
- **Constat** : inchange ; seul `READ` est produit, les six autres sont « reserved ».
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : inchangee (reduire a `read` ou documenter le contrat d'alignement amont).

### [INFO] `StepId` (`RootModel[str]`) — enveloppe cosmetique — reconduit de 0.7.0

- **Localisation** : `document-parser/api/schemas.py:566` (etait `:527`)
- **Constat** : inchange ; wrap `StepId(step.id)` (`schemas.py:619`) pour un nom de type OpenAPI.
- **Regle violee** : items 4.2 / 4.8 (deja couverts) — observation.
- **Remediation** : inchangee (`id: str` + `Field(description=...)`).

### [INFO] `LLMProvider.health_check()` non utilise en production — reconduit de 0.7.0

- **Localisation** : `document-parser/domain/ports.py:370`, `document-parser/infra/llm/ollama_provider.py:41`
- **Constat** : inchange ; aucun appelant de production (`grep "\.health_check()"` hors tests : 0 resultat pour ce port), la sonde reelle reste `OllamaProbe`.
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : inchangee (retirer du port ou cabler).

---

## Delta vs 0.7.0

Score : **83 → 75 (−8)**. Items conformes : 7/8 → 6/8. La baisse vient entierement de
l'item 4.5 (configuration), rendu non conforme par la couche de config MCP ajoutee en
0.7.3 ; l'item 4.2 etait deja non conforme.

| Ecart 0.7.0 | Statut 0.7.3 | Detail |
|-------------|--------------|--------|
| [MAJ] Abstraction LLM-provider prematuree (`value_objects.py:167`) | **Toujours present, inchange** | Aucun diff depuis `v0.7.0` ; c'est l'un des 9 MAJ portes en dette par le re-audit 0.7.0, non traite en 0.7.x |
| [INFO] `ReasoningStepKind` a 7 valeurs | Toujours present | `value_objects.py:207` |
| [INFO] `StepId` `RootModel[str]` | Toujours present | deplace `schemas.py:527` → `:566` |
| [INFO] `health_check()` mort sur le port | Toujours present | `ports.py:370` (etait `:337`) |

Nouveaux ecarts 0.7.3 : [MIN] configuration MCP en couches (4.5), [MIN] carte de citation
desactivee conservee (4.2), et 4 INFO (pont MCP Apps fait main en double, aides mortes,
`crop` residuel, repli de chemin de dev).

---

## Points positifs

- **Simplification active du serveur MCP (#363, `dc54211`)** : le journal d'investigation de #329 (6 outils, 3 tables SQLite, adjudicateur, budgets de retry) a ete retire avant release, ainsi que `how_to_use`, le compteur d'usage, la porte « unshown », la seconde facon de lire par `uri`, `MCP_INLINE_CITATION_IMAGE` et le mode crop. La surface publiee est revenue a 4 outils de lecture, une carte, un prompt — le probleme actuel, pas davantage. C'est exactement le reflexe KISS attendu.
- **Trace des sources sans etat** (`domain/source_map.py:8-11`) : la carte est projetee a partir des ancres que l'agent renvoie, « no journal to keep, no state to go stale » ; transport HTTP `stateless_http=True` (`mcp_mount.py:115`) assume et documente.
- **Modules de domaine purs et courts** : `source_bar.py` (62 lignes), `outline_locate.py` (71), `spans.py` (85), `page_regions.py` (121) — fonctions pures sur value objects, sans I/O ; curseur de lecture en simple chaine `ref@offset` (`navigation_service.py:221`).
- **Interrupteur On/Off simple** (item 4.1/4.6) : un seul wrapper ASGI de ~20 lignes (`_ServingGate`, `mcp_mount.py:151-169`) lit un booleen de l'`AppState` immuable, reconstruit en un `_update` atomique avec les services (`builder.py:243-246`) ; pas de remontage, pas de redemarrage, pas de middleware global.
- **Regles de precedence factorisees** : `services/config_overrides.py` (`pick`, `parse_*`, `require_writable`) est partage par la config reasoning (#317) et MCP (#364) au lieu d'etre recopie.
- **Polling d'analyse par lot minimal** : un seul `GET /api/analyses/summaries` par tick quelle que soit la taille du lot (`features/analysis/store.ts:170`), arret des qu'aucune analyse n'est active, regles pures dans `batch.ts` (33 lignes) testables sans timers.
- **Outils standard reutilises** (item 4.4) : `DoclingDocument.concatenate` pour recoller les lots (#344, `local_converter.py:174`) au lieu d'une fusion maison, `TransportSecuritySettings` du SDK MCP pour la protection DNS-rebinding, `OrderedDict` pour le LRU des index, `unicodedata`/`hashlib` pour la normalisation et le versionnage des templates, Starlette `Route`/`JSONResponse` pour la porte 503.
- **`ToolErrors` en context manager plutot qu'en decorateur** (`tool_errors.py:29-35`) : choix justifie (le SDK derive le schema d'entree de la signature) et plus simple qu'un decorateur preservant les signatures.
- **Helpers frontend purs** (`DocsLibraryPage.logic.ts`, `DocWorkspacePage.logic.ts`, `layerVisibility.ts`, `progress.ts`) : petites fonctions sans Vue ni routeur ; l'accordeon `provide/inject` est justifie par la contribution d'une feature a la page d'une autre (`McpConfigSection` dans `SettingsPanel`).
- **Zero meta-programmation** (item 4.7) : greps de la fiche negatifs (hors `AppStateBuilder`, composition root deja valide en 0.7.0, et un `setattr(app.state, ...)` trivial).

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL. Un seul ecart MAJOR (abstraction LLM-provider, reconduit sans
changement depuis 0.7.0), sous le seuil bloquant (> 3). Score 75 / 100 (60-79).
Conditions : planifier la remediation du MAJ reconduit (deuxieme report consecutif) et
des deux MIN — simplifier la config MCP (surtout `max_rounds` a chaud et la double
validation de `max_read_tokens`) et statuer sur la carte de citation desactivee — dans
le cycle 0.8.0.
