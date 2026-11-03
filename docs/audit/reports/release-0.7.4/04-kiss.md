# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : release/0.7.4 @ 1de1929 (= tag `v0.7.3` + 2 commits README)

Perimetre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`) et `frontend/src/`.
Baseline : rapport 0.7.3 (`docs/audit/reports/release-0.7.3/04-kiss.md`, commit `02adc68`,
score 75). L'audit 04 n'a pas ete re-audite en 0.7.3-reaudit (score reconduit tel quel).

Delta de code depuis la baseline (`02adc68..1de1929`) : remediation PR #367 et #368, soit
13 fichiers sous `document-parser/` et `frontend/src/` dont `uv.lock`. Aucun ne touche une
structure evaluee par cet audit :
- `services/analysis_service.py:180` : l'import Docling passe par `asyncio.to_thread` ;
- `infra/settings.py:90-96` : commentaire seulement ;
- `mcp_adapter/citation_app.html:2` : `lang="fr"` ;
- `pyproject.toml` : `mcp>=2.2.0` ;
- `Dockerfile` : `uv` 0.13.6 ;
- frontend : `ConfigSource` deplace dans `shared/types.ts`, libelles i18n MCP.

`git diff v0.7.3..1de1929` ne touche que `README.md` et deux GIF : le code audite est celui
du tag `v0.7.3`.

Methode :
- Chaque ecart du rapport 0.7.3 est re-verifie ligne a ligne sur `1de1929`, sans recopie.
- Les nouveaux ecarts sont cherches par les greps de la fiche, un balayage AST des fonctions
  relais pures, un inventaire des enums par nombre de membres et le controle de lecture de
  chaque champ `Settings`.
- Executions ciblees uniquement :
  - les fonctions pures `validate_mcp_config` et `Settings.from_env` ;
  - `pytest --collect-only` sur deux fichiers de tests.
- Application non lancee, suites de tests non executees.

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

Poids total de la checklist : 12. Poids conformes : 9. Les items 4.2 (poids 2) et 4.5
(poids 1) sont non conformes. `score = 9 / 12 * 100 = 75`.

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Le grep de la fiche ne remonte que `AppStateBuilder` (`bootstrap/builder.py:70`), la composition root deja validee. Aucune factory, strategy ni observer superflu. Frontend : aucune `class`, aucun bus d'evenements. |
| 4.2 | Resout le probleme actuel, pas hypothetique futur | 2 | **Non** | MAJ abstraction LLM-provider (inchange) et MIN carte de citation (inchange), plus 5 INFO d'appoint |
| 4.3 | Pas de wrapper sans valeur ajoutee | 1 | Oui (cf. INFO) | 17 relais purs detectes par AST en production, tous justifies (adaptateur de port, facade de couche) sauf les aides mortes listees en INFO |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (cf. INFO) | Pont MCP Apps fait main (INFO) ; ailleurs `DoclingDocument.concatenate`, `OrderedDict`, `asyncio.to_thread`, `TransportSecuritySettings` |
| 4.5 | Configuration simple | 1 | **Non** | MIN config MCP en couches (inchange) |
| 4.6 | Pas d'indirection inutile | 2 | Oui | Chemins API → service → repo et outil MCP → `DocumentTools` → service inchanges. Relais `server_status` justifie (SDK hors de `services/`). |
| 4.7 | Pas de meta-programmation / magie | 2 | Oui | Grep de la fiche : 0 en production. Seul un faux positif : `tests/test_chunking.py:460`, un nom de test. Aucun decorateur maison (`functools.wraps`, `ParamSpec` : 0). |
| 4.8 | Structures de donnees les plus simples | 1 | Oui | Curseur `ref@offset` en chaine, LRU `OrderedDict`, value objects geles ; rien de nouveau |

### Metriques de perimetre

| Mesure | 0.7.3 (`02adc68`) | 0.7.4 (`1de1929`) |
|--------|-------------------|-------------------|
| Variables d'env distinctes lues par `infra/settings.py` (1) | 45 | **45** (inchange) |
| Valeurs MCP surchargeables a chaud (`app_settings`, namespace `mcp`) | 4 | 4 |
| Representations de la config MCP (`Settings.mcp_*` → `McpRuntimeConfig` → `NavigationConfig`) | 3 | 3 |
| Cartes MCP Apps (HTML/CSS/JS autonomes) | 2 365 lignes (1 177 + 1 188) | 2 365 lignes (inchange) |
| Enums a un seul membre (backend, AST) | — | 1 (`LLMProviderType`) |
| Relais purs detectes par AST (production) | — | 17 (detail en 4.3) |
| Champs `Settings` jamais lus hors `settings.py` | — | 0 |
| Greps de la fiche (4.1 / 4.7) | `AppStateBuilder` seul / 0 | `AppStateBuilder` seul / 0 (+1 faux positif dans `tests/`) |

(1) Compte des noms distincts passes a `os.environ.get("…")`, extraits par regex. La meme
methode donne 37 sur `v0.7.2`, soit +8, conforme au delta annonce en 0.7.3. Le rapport 0.7.3
donnait 34 → 42 avec un comptage different, non reproduit ; l'ecart absolu n'a pas
d'incidence.

---

## Ecarts constates

### [MAJ] Genericite prematuree de l'abstraction LLM-provider (un seul backend realisable) — reconduit de 0.7.0

**Statut vs 0.7.3 : toujours present, strictement inchange.** `git diff 02adc68..1de1929` ne
touche aucun des fichiers concernes. L'ecart a ete releve en 0.7.0, puis reporte au re-audit
0.7.0, en 0.7.3 et au re-audit 0.7.3. C'est sa 4e constatation.

- **Localisation** :
  - `document-parser/domain/value_objects.py:167-177`
  - `document-parser/domain/ports.py:344-374`
  - `document-parser/infra/docling_agent_reasoning.py:136-140`
  - `document-parser/bootstrap/factories.py:103-110`
  - `document-parser/infra/settings.py:51-55` et `:231`
- **Constat** :
  - **Enum a un seul membre.** `LLMProviderType` est une `StrEnum` reduite a `OLLAMA`
    (`value_objects.py:177`). La docstring l'assume : « Other variants are kept here to make
    the abstraction visible and prepare future backends » (`:171-172`). C'est la seule enum a
    un membre du backend (inventaire AST).
  - **Tag de dispatch sans dispatch.** Le port `LLMProvider` porte un tag `type`
    (`ports.py:361-362`). Son seul consommateur est un garde `NotImplementedError`
    (`docling_agent_reasoning.py:137-140`). Le runner ne lit sinon que `host` et
    `default_model_id` (`:163`, `:176`, `:186`).
  - **Knob a une seule valeur.** `LLM_PROVIDER_TYPE` (`settings.py:55`, lu `:231`) est commente
    « kept as a config knob to make the LLMProvider abstraction visible and prepare the ground
    for additional backends » (`settings.py:51-54`).
  - **Double garde.** Le cas « non Ollama » est verifie par comparaison de chaine dans la
    factory (`factories.py:103-110`), puis par l'enum dans le runner
    (`docling_agent_reasoning.py:137`).
  - **Champ d'affichage a valeur unique.** La valeur remonte jusqu'au panneau : `builder.py:217`
    → `AppConfigService` (`app_config_service.py:73`, `:81`, `:186`) → `ReasoningConfigView`
    (`domain/app_config.py:63`) → `ReasoningConfigResponse.provider_type`
    (`api/schemas.py:697`, `:712`) → `ReasoningConfigSection.vue:153`, qui affiche
    « Provider: ollama ».
  - **Methode morte sur le port.** `health_check()` est declaree sur le port (`ports.py:370`)
    et n'a aucun appelant de production (voir l'INFO dedie).
- **Regle violee** : item 4.2 — « Le code resout le probleme actuel, pas un probleme
  hypothetique futur (pas de genericite prematuree) » (poids 2).

#### Cout de la suppression (inventaire verifie sur `1de1929`)

| Surface | Elements touches | Detail |
|---------|------------------|--------|
| Domaine | `value_objects.py:167-177` (11 l.), `ports.py:34` (import) et `:344-374` (31 l.) | Supprimer l'enum. Le port est soit supprime, soit reduit a `host` + `default_model_id`. |
| Infra | `infra/llm/ollama_provider.py` (47 l.) : `type` `:29-31`, `health_check` `:41-47`, constantes `:18-21` | `OllamaProvider` peut rester un simple porteur host/modele. `infra/llm/ollama_probe.py`, la vraie sonde du panneau, n'est pas touche. |
| Runner | `docling_agent_reasoning.py:20-22` (imports), `:136-140` (garde) | 5 lignes |
| Bootstrap | `factories.py:88-91` (docstring), `:103-110` (garde) ; `builder.py:217` | — |
| Config | `settings.py:51-55`, `:231` | Une variable d'env de moins (45 → 44) |
| Service / DTO | `app_config_service.py:73`, `:81`, `:186` ; `domain/app_config.py:63` ; `api/schemas.py:697`, `:712` | Seulement si le champ `providerType` est retire du contrat |
| API exposee | Champ `providerType` des reponses GET/PUT/DELETE `/api/config/reasoning` | Seul consommateur : `ReasoningConfigSection.vue:153`. Aucun scenario `e2e/` ne lit `providerType` ni `config/reasoning` (grep : 0). Aucun snapshot OpenAPI versionne. |
| Frontend | `features/admin-config/types.ts:19`, `ReasoningConfigSection.vue:152-154`, `store.test.ts:29`, `shared/i18n.ts:400` et `:1123` (`settings.reasoning.provider`) | 4 fichiers |
| Tests | `tests/test_ollama_provider.py` : 6 tests, dont 5 ne testent que `type`, le protocole ou `health_check`. `test_docling_agent_reasoning.py:157-168` : `TestProviderRejection`, 1 test. `_make_runner` (`:26`, `:145`) est a adapter si `OllamaProvider` disparait. `test_app_config_service.py:72`, `:94` et `test_config_api.py:69`, `:109` : un argument et une assertion chacun. | `pytest --collect-only` : 7 tests directement lies. La garde de factory (`factories.py:103-110`) n'est couverte par aucun test (grep `llm_provider_type` dans `tests/` : 0). |
| Docs | `.env.example:87`, `docs/configuration.md:46`, `docs/troubleshooting.md:13`, entree CHANGELOG « Removed » | — |
| Comportement | Aujourd'hui, `LLM_PROVIDER_TYPE` ≠ `ollama` coupe le runner (`factories.py:103-110`, documente dans `troubleshooting.md:13`). Apres suppression, la variable est ignoree. | Seul changement observable. Le chemin Ollama est identique. |

- **Remediation** — deux options :
  - **Option A : assumer Ollama en dur.** Tout le tableau ci-dessus, y compris le retrait de
    `providerType` du contrat.
    - Ampleur : ≈ 22 fichiers, quasi exclusivement des suppressions (≈ 110-150 lignes de
      production, ≈ 70 de tests).
    - **Effort M** (mecanique).
    - **Risque de regression faible.** Le reasoning est coupe par defaut
      (`REASONING_ENABLED=false`, `settings.py:50`) et Ask est masque (`ASK_MODE=hidden`,
      `settings.py:67`). Le chemin Ollama est inchange.
    - Le seul contrat touche est un champ d'affichage d'une API admin sans autre consommateur
      que la SPA.
  - **Option B : reduire la couture sans toucher au contrat.**
    - A supprimer :
      - l'enum ;
      - `type` et `health_check` du port et de `OllamaProvider` ;
      - les deux gardes ;
      - le knob `LLM_PROVIDER_TYPE`.
    - A garder : le port `LLMProvider` (`host`, `default_model_id`).
    - `providerType` reste dans la reponse comme constante `"ollama"` ; le parametre
      `provider_type` d'`AppConfigService` disparait.
    - Ampleur : ≈ 9 fichiers de production, 3 de tests, 3 de docs.
    - **Effort S, risque tres faible.**
    - Le residuel est un champ d'affichage constant (INFO).

  L'une ou l'autre option leve aussi l'INFO `health_check()`. La 0.7.4 ne contient a ce jour
  aucun code fonctionnel nouveau : c'est le cycle le moins risque pour solder cette dette plutot
  que de la reporter une 5e fois.

---

### [MIN] Configuration MCP en couches : 8 variables d'env, 3 representations, un knob « live » qui ne l'est qu'a moitie

**Statut vs 0.7.3 : toujours present.** Seul le commentaire `settings.py:90-96` a change,
d'ou un decalage de +1 ligne apres `:95`. Une nuance : le sous-point stdio est deja documente
(voir plus bas).

- **Localisation** :
  - `document-parser/infra/settings.py:97-123` et `:254-275`
  - `document-parser/bootstrap/factories.py:241-252`
  - `document-parser/domain/mcp_config.py:41-50`
  - `document-parser/services/mcp_config_service.py:76-97`
  - `document-parser/services/navigation_config.py:25` et `:64-72`
  - `document-parser/bootstrap/mcp_mount.py:98-101`
  - `document-parser/mcp_stdio.py:63-76`
  - `document-parser/infra/settings.py:67`
- **Constat** :
  - **Surface.**
    - 7 variables `MCP_*` plus `ASK_MODE` (`settings.py:254-275`, `:236`).
    - Quatre valeurs MCP sont en plus surchargeables en base (`app_settings`, namespace `mcp`),
      avec precedence db > env, source par champ et reset (`mcp_config_service.py:76-97`).
  - **Trois representations pour quatre knobs** :
    1. `Settings.mcp_*` (`settings.py:97-123`) ;
    2. `env_mcp_config()`, qui construit un `McpRuntimeConfig` (`factories.py:241-252`,
       `mcp_config.py:41-50`) ;
    3. `resolve_mcp_config`, qui applique les lignes db (`mcp_config_service.py:76-97`), puis
       `NavigationConfig.from_runtime`, qui re-projette trois champs
       (`navigation_config.py:64-72`).

    Les defauts litteraux sont ecrits a plusieurs endroits :
    - `5` rounds : `settings.py:110` et `:274`, `navigation_config.py:25`,
      `features/mcp-config/store.ts:17`. `server.py:81`, `:102` et `prompts.py:52-53`
      reutilisent la constante `MAX_ROUNDS` et non le litteral : la liste 0.7.3 est corrigee
      sur ce point.
    - `4000` tokens : `settings.py:107` et `:273`, `navigation_config.py:32`, `store.ts:17`.
  - **`max_rounds` est « live » sans etre applique ni entierement live.**
    - Rien ne l'impose cote serveur (`settings.py:108-109`, `navigation_config.py:21-23`).
    - Sur HTTP, les instructions serveur sont figees au boot avec la valeur d'env
      (`mcp_mount.py:98-101`, `server.py:81-87`). Le prompt et la carte, eux, lisent la valeur
      effective.
    - La doc reconnait la limite : « restart the backend, then the client, to align them »
      (`docs/mcp-server.md:85-87`).
  - **Deux validations divergentes pour le meme knob** — **verifie par execution** des
    fonctions pures :
    - `Settings.from_env()` avec `MCP_MAX_READ_TOKENS=50` accepte la valeur
      (`settings.py:159-160` : `>= 1`) ;
    - `validate_mcp_config(McpRuntimeConfig(5, 50, "", enabled=False))` renvoie
      `['max_read_tokens must be between 100 and 32000 (got 50)']` (`mcp_config.py:34-35`,
      `:115-119`).

    Or l'interrupteur On/Off renvoie le formulaire complet (`store.ts:99-104`), et
    `update_config` valide tout avant d'ecrire (`mcp_config_service.py:147-155`). Avec une telle
    valeur d'env, couper le serveur depuis le panneau echoue donc en 400. Ce dernier
    enchainement HTTP est deduit statiquement et n'a pas ete execute.

    `Settings` importe deja les bornes des rounds depuis le domaine (`settings.py:10-11`,
    `:161`), mais pas celles des tokens.
  - **Semantique differente selon le transport.** L'entree stdio resout la config effective
    mais ignore `config.enabled` et `MCP_ENABLED` (`mcp_stdio.py:63-76`). Elle annonce le plafond
    effectif (`:73-75`), alors que HTTP annonce celui d'env.
    - Nuance vs 0.7.3 : l'exemption stdio est **documentee et assumee** depuis `02adc68` :
      « Both gate the HTTP transport only. The stdio process is spawned by the client itself,
      and that spawn is the authorisation » (`docs/mcp-server.md:33-34`). La remediation 0.7.3
      « ou documenter que stdio l'ignore » est donc deja satisfaite.
    - Il reste la divergence du plafond annonce.
  - **`ASK_MODE`** est une chaine a deux valeurs (`settings.py:67`, validee `:179-180`), alors
    que toutes les autres bascules sont des booleens `*_ENABLED`.
- **Regle violee** : item 4.5 — « Configuration simple — pas de systeme de config complexe la
  ou une variable d'env suffit » (poids 1).
- **Remediation** :
  1. Valider `mcp_max_read_tokens` dans `Settings.__post_init__` avec `READ_TOKENS_MIN` et
     `READ_TOKENS_MAX` du domaine, comme pour les rounds (3 lignes, **S**).
     - Risque : un operateur dont la valeur est hors [100, 32000] verra le boot refuse.
     - A signaler au CHANGELOG, ou bien borner (clamp) la valeur plutot que la refuser.
  2. Ne faire vivre le plafond de rounds qu'a un seul endroit (**S**) :
     - soit le retirer du texte des instructions (`server.py:81-87`) ;
     - soit retirer `max_rounds` des valeurs a chaud et le laisser en env seul.

     Risque faible, mais le premier choix change un texte lu par le modele.
  3. `ASK_MODE` → booleen `ASK_ENABLED`. Changement d'env cassant, a ne faire qu'avec un
     alias : **M**, non prioritaire.

  Les points 1 et 2 suffiraient a reclasser le residuel (3 representations, `ASK_MODE`) en
  INFO.

### [MIN] Carte de citation conservee mais desactivee par defaut (`MCP_CITATION_CARD=false`)

**Statut vs 0.7.3 : toujours present, inchange.** Le seul changement depuis la baseline est
`lang="en"` → `lang="fr"` (`citation_app.html:2`, commit `6711444`).

- **Localisation** :
  - `document-parser/infra/settings.py:116-119` et `:271-272`
  - `document-parser/mcp_adapter/apps.py:141-142` et `:146-228`
  - `document-parser/mcp_adapter/citation_app.html` (1 177 lignes)
  - `document-parser/services/citation_service.py:57`
- **Constat** :
  - **Livre mais eteint par defaut.** Sont concernes :
    - `show_citation` et son outil app-only `get_citation_image` ;
    - le template `citation_app.html` ;
    - le DTO `CitationView` (`apps.py:74`) ;
    - le cas d'usage `CitationService.get_citation` (`citation_service.py:57`), dont
      `apps.py:168` est l'unique appelant de production (le reste est dans les tests,
      `test_navigation_service.py:512-528`).
  - **Motif ecrit dans le code** : « a model offered it called it on its own before every
    sources card, which already shows each cited passage boxed on its page »
    (`settings.py:116-118`, `apps.py:5-8`).
  - **Decision sans besoin nomme.** Le design #363 constate la redondance, puis tranche « The
    tool stays, described for a passage the reader asks to see »
    (`docs/design/363-mcp-chunkless-rag-simplification.md:481-485`). Une decision est donc
    ecrite, mais aucun hote ni besoin courant n'y est nomme.
  - **Empreinte.** Le flag est present dans :
    - 11 fichiers de production : 10 Python, plus le template ;
    - 6 fichiers de tests backend, dont 19 occurrences dans `test_mcp_apps.py` ;
    - 3 fichiers frontend, dont `McpConfigSection.vue` ;
    - `.env.example` et la doc.

    S'y ajoute une seconde copie du pont postMessage (INFO 4.4).
  - **Classement.** Instance supplementaire de l'item 4.2, deja non conforme. Classee MIN parce
    qu'elle est opt-in, documentee (`docs/mcp-server.md:50`, `:158`) et hors du chemin par
    defaut.
- **Regle violee** : item 4.2 (poids 2, deja compte non conforme).
- **Remediation** : retirer la carte. Cela comprend le template, les deux outils,
  `get_citation`, `CitationView`, `MCP_CITATION_CARD`, `McpServerStatus.citation_card` et la
  ligne du panneau. Elle se ressortira de l'historique git le jour ou un hote en aura besoin.
  - **Effort M** : nombreux fichiers, mais des suppressions.
  - **Risque faible** : desactivee par defaut. `CitationImageService.render_page` reste utilise
    par `show_sources` (`sources_view.py:204`) et ne doit pas partir avec la carte.

  Tant que la carte reste, l'item 4.2 reste non conforme, meme si le MAJ est solde : la meme
  lecture a ete appliquee en 0.7.3 a l'item 3.1.3 pour le choix produit du francais.

---

### [INFO] Pont MCP Apps (JSON-RPC sur postMessage) ecrit a la main et present en deux copies

**Statut vs 0.7.3 : toujours present, inchange.**

- **Localisation** :
  - `document-parser/mcp_adapter/citation_app.html:690-770` (`post`, `call`, `settle`,
    `handshake`) et `:1065` (`reportSize`)
  - `document-parser/mcp_adapter/sources_app.html:984-1060` et `:1089`
  - `document-parser/mcp_adapter/citation_app.html:460` (`renderMarkdown`)
- **Constat** :
  - **Protocole recopie.** Chaque carte embarque sa propre implementation du protocole MCP
    Apps : requetes en attente avec timeout, poignee de main `ui/initialize` puis
    `ui/notifications/initialized`, `reportSize`.
  - **Mesure 0.7.4** (difflib, lignes normalisees) : ≈ 155 lignes strictement identiques par
    blocs de 3 lignes ou plus, dont 153 dans les `<script>`. Le rapport 0.7.3 annoncait
    « ≈ 230 lignes communes », ce qui incluait le quasi-identique ; ce chiffre n'est pas
    reproduit a l'identique.
  - **SDK officiel non utilise.** `@modelcontextprotocol/ext-apps` couvre ce besoin. Le choix
    « pas de SDK, pas de build » n'est toujours documente nulle part : `apps.py:1-22` justifie un
    template statique par vue, pas l'absence de SDK.
- **Regle violee** : item 4.4 (conforme dans l'ensemble) — observation.
- **Remediation** : inchangee.
  - Documenter le choix dans `apps.py`.
  - Factoriser le pont si les deux cartes restent.
  - La suppression de la carte de citation fait disparaitre la seconde copie.

### [INFO] Aides mortes et relais sans valeur ajoutee

**Statut vs 0.7.3 : toujours present, inchange.** Un constat preexistant non releve en 0.7.3
est ajoute.

- **Localisation** :
  - `document-parser/mcp_adapter/wire.py:72`, `document-parser/mcp_adapter/wire_mapping.py:42`
  - `document-parser/mcp_adapter/server.py:90`
  - `document-parser/mcp_adapter/prompts.py:52-53`
  - `document-parser/services/mcp_config_service.py:100-106` et `:186-188`
  - `document-parser/services/app_config_service.py:144-145`
  - `document-parser/infra/serve_converter.py:95-98`
- **Constat** :
  - **Code mort.**
    - `_neutralise_all` est defini deux fois a l'identique (`wire.py:72`, `wire_mapping.py:42`)
      et n'est appele nulle part.
    - La constante `INSTRUCTIONS = instructions(apps=False)` (`server.py:90`) n'a aucun
      lecteur, tests et docs compris.

    Les deux ont ete verifies par grep sur tout le depot.
  - **Relais triviaux.**
    - `_default_rounds()` renvoie une constante (`prompts.py:52-53`).
    - `load_effective_mcp_config` jette la moitie du tuple (`mcp_config_service.py:100-106`).
    - `server_status` relaie le callable injecte (`:186-188`). Ce relais est justifie : il
      garde le SDK hors de `services/`.
    - `_require_writable` enveloppe `require_writable` (`app_config_service.py:144-145`).
  - **Nouveau constat (preexistant a `02adc68`, issu de #344)** : `ServeConverter.merge_batches`
    (`serve_converter.py:95-98`) est inatteignable par construction. Sa docstring le dit :
    « Not reached while `supports_page_batching` is False ». Il n'existe que pour satisfaire le
    port `DocumentConverter` (`ports.py:79`). C'est tolerable : 3 lignes, et une alternative
    serait plus complexe.
  - **Le reste du balayage AST** (17 relais purs en production) est justifie :
    - `DoclingTreeReader` (`infra/docling_tree.py:286-307`) adapte des fonctions libres au port
      `DocumentTreeReader` (#audit-01) ;
    - `AnalysisService.find_*` (`analysis_service.py:194-206`) et `DocumentService.find_*`
      (`document_service.py:111-115`) sont des facades de couche API → service.
- **Regle violee** : item 4.3 (conforme dans l'ensemble) — observation.
- **Remediation** : supprimer `_neutralise_all` (×2) et `INSTRUCTIONS`, sans risque (0
  appelant). Remplacer `_default_rounds` par `lambda: MAX_ROUNDS`.

### [INFO] `PageRasterizer.crop(box, fmt)` : generalite residuelle apres le retrait du mode crop

**Statut vs 0.7.3 : toujours present, inchange.**

- **Localisation** :
  - `document-parser/domain/ports.py:436-445`
  - `document-parser/infra/page_raster.py:35-64`
  - `document-parser/services/citation_image_service.py:91`
  - `document-parser/domain/navigation.py:207` et `:220`
- **Constat** :
  - **Le crop sert de transcodeur.** L'unique appel de production recadre la page entiere avec
    une boite sentinelle `(0, 0, 10_000, 10_000)` pour la reencoder en WEBP
    (`citation_image_service.py:91`).
  - **Parametre inutilise.** Le defaut `fmt="PNG"` (`ports.py:441`) n'est jamais utilise en
    production.
  - **Double encodage.** La page est encodee en PNG par `render_page` (`page_raster.py:32-33`),
    puis decodee et reencodee.
  - **Nommage trompeur.** `RasterCrop.png` et `CitationImage.png` (`navigation.py:207`, `:220`)
    portent des octets WEBP.
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : inchangee. Remplacer `crop` par `render_page(..., fmt="WEBP")` ou
  `encode_webp(png)`, et supprimer la boite sentinelle.

### [INFO] Repli d'environnement de developpement dans le chemin de production

**Statut vs 0.7.3 : toujours present, inchange.**

- **Localisation** :
  - `document-parser/services/document_service.py:119-131`
  - `document-parser/api/documents.py:186` et `:214`
  - `document-parser/infra/page_raster.py:27`
- **Constat** :
  - **Repli silencieux.** `resolve_storage_path` retente un fichier introuvable sous
    `UPLOAD_DIR/<basename>`, pour le cas « base creee sous Docker, worktree lance sur l'hote »
    (docstring `:120-125`).
  - **Couverture partielle.** Le repli ne s'applique qu'aux deux routes citees.
    `PdfPageRasterizer.render_page` lit `storage_path` tel quel (`page_raster.py:27`) : les
    vignettes MCP n'en beneficient pas.
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : inchangee. Traiter ce cas par la configuration ou par un script de migration
  des chemins.

### [INFO] Taxonomie `ReasoningStepKind` a 7 valeurs alors qu'une seule est emise — reconduit de 0.7.0

**Statut vs 0.7.3 : toujours present, inchange.**

- **Localisation** :
  - `document-parser/domain/value_objects.py:207-222`
  - `document-parser/domain/trace_builder.py:60`
  - `frontend/src/features/reasoning/types.ts:6`
  - `frontend/src/features/reasoning/kindColors.ts:14-22`
- **Constat** : seul `ReasoningStepKind.READ` est produit (`trace_builder.py:60`, unique
  emission en production). Les six autres valeurs sont « reserved »
  (`value_objects.py:211-213`) et ont chacune une couleur cote frontend.
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : inchangee. Reduire a `read`, ou documenter le contrat d'alignement amont.

### [INFO] `StepId` (`RootModel[str]`) — enveloppe cosmetique — reconduit de 0.7.0

**Statut vs 0.7.3 : toujours present, inchange.**

- **Localisation** : `document-parser/api/schemas.py:566-575`, wrap `:619`
- **Constat** : `StepId(step.id)` n'existe que pour donner un nom de type OpenAPI a une chaine
  (docstring `:569-571`).
- **Regle violee** : items 4.2 / 4.8 (deja couverts) — observation.
- **Remediation** : inchangee. `id: str` avec `Field(description=...)`.

### [INFO] `LLMProvider.health_check()` non utilise en production — reconduit de 0.7.0

**Statut vs 0.7.3 : toujours present, inchange.**

- **Localisation** :
  - `document-parser/domain/ports.py:370-374`
  - `document-parser/infra/llm/ollama_provider.py:41-47`
- **Constat** :
  - **Aucun appelant de production.** Hors tests, `grep health_check` ne remonte que les
    definitions. Les seuls appelants sont 3 tests de `test_ollama_provider.py:39-82`.
  - **Sonde reelle distincte.** Le panneau sonde Ollama avec `OllamaProbe`
    (`builder.py:219`), dont le commentaire renvoie a `OllamaProvider.health_check`
    (`ollama_probe.py:23`).
  - **Meme constat cote conversion.** `ServeConverter.health_check()` (`serve_converter.py:189`)
    est lui aussi sans appelant de production. Il est suivi par l'audit 06 (INFO 3) et n'est pas
    recompte ici.
- **Regle violee** : item 4.2 (deja compte) — observation.
- **Remediation** : retirer `health_check` du port et de `OllamaProvider`. C'est inclus dans les
  options A et B du MAJ.

---

## Delta vs 0.7.3

Score : **75 → 75 (=)**. Items conformes : 6/8 → 6/8. Aucun changement de code depuis
`02adc68` ne touche le perimetre KISS. La remediation #367/#368 visait les audits 07, 08, 10,
11 et 12.

| Ecart 0.7.3 | Statut 0.7.4 | Detail |
|-------------|--------------|--------|
| [MAJ] Abstraction LLM-provider prematuree (`value_objects.py:167`) | **Toujours present, inchange** | 4e constatation (0.7.0, re-audit 0.7.0, 0.7.3, 0.7.4). Le cout de suppression est desormais chiffre. |
| [MIN] Configuration MCP en couches | **Toujours present** | Lignes `settings.py` decalees de +1. Divergence de validation **confirmee par execution**. Sous-point stdio deja documente (`docs/mcp-server.md:33-34`). Liste des defauts dupliques corrigee. |
| [MIN] Carte de citation desactivee conservee | **Toujours present** | Seul `lang="fr"` a change (`6711444`) |
| [INFO] Pont MCP Apps fait main en double | Toujours present | Mesure de duplication refaite : ≈ 155 lignes identiques |
| [INFO] Aides mortes et relais | Toujours present | Ajout de `ServeConverter.merge_batches`, inatteignable |
| [INFO] `crop` residuel | Toujours present | — |
| [INFO] Repli de chemin de dev | Toujours present | — |
| [INFO] `ReasoningStepKind` a 7 valeurs | Toujours present | — |
| [INFO] `StepId` `RootModel[str]` | Toujours present | — |
| [INFO] `health_check()` mort sur le port | Toujours present | Renvoi vers l'audit 06 pour `ServeConverter.health_check` |

Aucun nouvel ecart classe (CRIT, MAJ ou MIN) : le code n'a pas change.

---

## Points positifs

- **Remediation 0.7.3 simple et standard.**
  - L'import Docling bloquant est corrige par une seule ligne `asyncio.to_thread`
    (`analysis_service.py:180`), sans file de taches ni executor maison.
  - `ConfigSource` est deplace dans `shared/types.ts:6`, ce qui supprime un import croise entre
    features au lieu d'ajouter une couche.
- **Simplification active du serveur MCP (#363)** : surface publiee limitee a 4 outils de
  lecture, une carte par defaut et un prompt. Toujours vrai sur `1de1929`.
- **Trace des sources sans etat** (`domain/source_map.py:8-11`) et transport
  `stateless_http=True` (`mcp_mount.py:115`), assumes et documentes.
- **Modules de domaine purs et courts** : `source_bar.py` (62 lignes), `outline_locate.py`
  (71), `spans.py` (85), `page_regions.py` (121).
- **Interrupteur On/Off minimal** : `_ServingGate` (`mcp_mount.py:151-169`) lit un booleen de
  l'`AppState` immuable. Ni remontage ni middleware global.
- **Precedence factorisee** : `services/config_overrides.py` (`pick`, `parse_*`,
  `require_writable`) est partage par `app_config_service.py:29` et `mcp_config_service.py:36`.
- **Outils standard reutilises** (item 4.4) :
  - `DoclingDocument.concatenate` pour les lots (`local_converter.py:174`) ;
  - `TransportSecuritySettings` du SDK MCP ;
  - `OrderedDict` pour le LRU ;
  - Starlette `Route`/`JSONResponse`.
- **Config sans champ mort** : les 45 variables lues alimentent toutes un champ `Settings`
  effectivement consomme hors de `settings.py`.
- **`ToolErrors` en context manager plutot qu'en decorateur** (`tool_errors.py:29`), ce qui
  preserve les signatures dont le SDK derive les schemas.
- **Zero meta-programmation** (item 4.7) et frontend sans classe ni bus d'evenements.

---

## Verdict partiel : GO CONDITIONNEL

- Aucun ecart CRITICAL.
- Un seul ecart MAJOR (abstraction LLM-provider), sous le seuil bloquant (> 3).
- Score 75 / 100, dans la tranche 60-79.

Conditions :

1. **Solder le MAJ dans ce cycle**, option B au minimum (S, risque tres faible). Il en est a sa
   4e constatation, et la 0.7.4 n'apporte aucun code fonctionnel : c'est le moment le moins
   risque. A defaut, l'inscrire comme condition bloquante de 0.8.0.
2. **Corriger la double validation de `MCP_MAX_READ_TOKENS`** : 3 lignes. Elle peut empecher de
   couper le serveur MCP depuis le panneau.
3. **Statuer sur la carte de citation** (suppression recommandee). Tant qu'elle reste, l'item
   4.2 ne peut pas redevenir conforme.

Trajectoire de score (poids conformes / 12) :

| Etape | Score |
|-------|-------|
| Actuel | 75 |
| Item 4.5 conforme (remediations 1 et 2 du MIN config) | 83 |
| Item 4.2 conforme (MAJ et carte de citation) | 92 |
| Les deux | 100 |
