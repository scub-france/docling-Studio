# Rapport d'audit : DRY (Don't Repeat Yourself)

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 7 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 2 |
| Ecarts INFO | 2 |

Poids total de la checklist : 12. Poids conformes : 8 (les items 5.1 et 5.3,
poids 2 chacun, sont non conformes). `score = 8 / 12 * 100 = 67`.

| # | Item | Poids | Conforme |
|---|------|-------|----------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois sans factorisation | 2 | **Non** |
| 5.2 | Types partages centralises (`shared/types.ts` / `domain/models.py`) | 2 | Oui |
| 5.3 | Pas de magic numbers/strings eparpilles — constantes nommees et centralisees | 2 | **Non** |
| 5.4 | Logique reactive partagee dans `shared/composables/` | 1 | Oui |
| 5.5 | Appels API sans duplication de config HTTP — centralises dans `shared/api/http.ts` | 2 | Oui |
| 5.6 | Schemas Pydantic transforment le domain, ne le redefinissent pas | 2 | Oui |
| 5.7 | Regles de validation definies a un seul endroit (pas de desaccord front/back) | 1 | Oui |

---

## Ecarts constates

### [MAJ] Palette de couleurs par type d'element redefinie dans 4 fichiers

- **Localisation** : `frontend/src/features/document/elementColors.ts:14`, `frontend/src/features/analysis/ui/BboxOverlay.vue:42`, `frontend/src/features/analysis/ui/StructureViewer.vue:68`, `frontend/src/features/analysis/ui/ResultTabs.vue:199`
- **Constat** : la table `type d'element → hex` existe comme source unique de verite dans `elementColors.ts` (`ELEMENT_COLORS`, ligne 14 — `title:'#EF4444'`, `section_header:'#F97316'`, `text:'#3B82F6'`, `table:'#8B5CF6'`, `picture:'#22C55E'`, `list:'#06B6D4'`, `formula:'#EC4899'`, `code:'#14B8A6'`, `caption:'#EAB308'`), et sa docstring annonce explicitement etre le « Single source of truth ». Pourtant trois composants de la feature `analysis` **redeclarent** un objet `ELEMENT_COLORS` local au lieu d'importer la constante partagee : `BboxOverlay.vue:42-52` (copie exacte des 9 entrees), `ResultTabs.vue:199-209` (copie exacte), `StructureViewer.vue:68-76` (variante partielle — `title` et `code` manquants). Le meme bloc de constantes apparait donc 4 fois. La feature `reasoning` (`kindColors.ts:10`) fait, elle, la bonne chose en important `ELEMENT_COLORS` — preuve que la centralisation etait disponible et volontairement contournee ici.
- **Regle violee** : item 5.1 — « Aucun bloc de code identique ou quasi-identique n'apparait 3+ fois sans etre factorise » (poids 2). Recoupe aussi 5.3 (constantes couleur non centralisees).
- **Remediation** : dans `BboxOverlay.vue`, `ResultTabs.vue`, `StructureViewer.vue`, supprimer la constante locale et importer `ELEMENT_COLORS` / `colorFor` depuis `features/document/elementColors.ts` (ou promouvoir la palette vers `shared/` si le couplage inter-feature `analysis → document` est juge indesirable). Divergence a corriger au passage : `StructureViewer` n'expose pas `title`/`code`, ce qui produit deja un rendu incoherent entre surfaces.

### [MAJ] Helper de parsing ISO-datetime copie-colle dans 6 repositories

- **Localisation** : `document-parser/persistence/document_repo.py:11`, `document-parser/persistence/chunk_repo.py:13`, `document-parser/persistence/chunk_edit_repo.py:12`, `document-parser/persistence/document_store_link_repo.py:11`, `document-parser/persistence/document_version_repo.py:12`, `document-parser/persistence/store_repo.py:29`, `document-parser/persistence/analysis_repo.py:11`
- **Constat** : la meme fonction utilitaire `_parse_iso(value) -> datetime` (parse `datetime.fromisoformat` + coercition `tzinfo` a UTC si naive, avec garde `None`/`""`) est reimplementee a l'identique dans 4 repos (`document_repo`, `chunk_repo`, `chunk_edit_repo`, `document_store_link_repo`), plus une variante `_parse_iso` non-optionnelle dans `document_version_repo:12` et une variante `_parse_dt(value: str | datetime)` dans `store_repo:29`. Sept copies au total d'une meme logique de conversion. Pire, `analysis_repo._parse_dt` (ligne 11) **diverge** : il n'applique PAS la coercition tzinfo→UTC que font les six autres, donc `AnalysisJob.started_at/completed_at` peut ressortir naive la ou tous les autres agregats ressortent aware — exactement le type de derive silencieuse que la factorisation previent.
- **Regle violee** : item 5.1 — bloc quasi-identique present bien plus de 3 fois sans factorisation (poids 2).
- **Remediation** : extraire un unique `parse_iso(value: str | datetime | None, *, default_utc: bool) -> datetime | None` dans `persistence/database.py` (ou un `persistence/_datetime.py` dedie) et le faire consommer par tous les `_row_to_*`. Aligner au passage `analysis_repo` sur la coercition UTC pour supprimer la divergence de comportement.

### [MAJ] Couleurs UI en dur et tokens `--color-*` non definis, eparpilles

- **Localisation** : `frontend/src/features/store/ui/StoreForm.vue:389` `:394` `:405` `:487`, `frontend/src/features/store/ui/Neo4jConfigForm.vue:94` `:99` `:103` `:107`, `frontend/src/features/store/ui/OpenSearchConfigForm.vue:77` `:81` `:84`, plus `frontend/src/app/App.vue`, `frontend/src/features/analysis/ui/GraphView.vue`, `frontend/src/pages/IngestLaunchDialog.vue`
- **Constat** : le systeme de design definit ses tokens dans `App.vue :root` (`--border`, `--text-muted`, `--accent`, `--bg-surface`, …). Les formulaires de store ignorent ce vocabulaire et referencent un namespace **inexistant** (`--color-border`, `--color-text-muted`) qui n'est defini nulle part, forcant le repli sur des hex codes en dur repetes : `#d1d5db` (7 occurrences), `#6b7280` (12 occurrences), `#dc2626` — rouge d'erreur — (11 occurrences reparties sur 6 fichiers). La meme valeur d'erreur `#dc2626` est ainsi recopiee dans `App.vue`, `GraphView.vue`, `IngestLaunchDialog.vue` et les trois formulaires de store, sans constante nommee ni token. Un changement de charte impose une chasse au hex sur tout le front.
- **Regle violee** : item 5.3 — « Pas de magic numbers ou magic strings eparpilles — les constantes sont nommees et centralisees » (poids 2).
- **Remediation** : remplacer `var(--color-border, #d1d5db)` / `var(--color-text-muted, #6b7280)` par les tokens reels du systeme (`var(--border)` / `var(--text-muted)`), et introduire un token d'erreur (`--danger: #dc2626`) dans `:root` (clair + sombre) consomme partout au lieu du hex litteral. Aucun fallback en dur ne doit subsister une fois le token defini.

### [MIN] Bloc de style `.field-*` et pont reactif v-model dupliques dans les formulaires de store

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue:77-108`, `frontend/src/features/store/ui/OpenSearchConfigForm.vue:60-91`, `frontend/src/features/store/ui/StoreForm.vue:375-406`
- **Constat** : le bloc scoped `.config-form` / `.field` / `.field-label` / `.field-input` / `.field-input[aria-invalid]` / `.field-help` / `.field-error` est recopie a l'identique dans `Neo4jConfigForm` et `OpenSearchConfigForm`, et repris quasi tel quel dans `StoreForm`. En parallele, le pont reactif `const indexName = ref(String(props.modelValue.indexName ?? props.modelValue.index_name ?? ''))` + le `watch(() => props.modelValue, ...)` + `emitChange`/`emit('valid', ...)` est duplique verbatim entre `Neo4jConfigForm.vue:53-74` et `OpenSearchConfigForm.vue:40-57`.
- **Regle violee** : item 5.1 (duplication, ampleur limitee — CSS scoped + petit pattern reactif), non bloquant.
- **Remediation** : extraire les regles `.field-*` communes dans une feuille partagee (ou un composant `FormField` reutilisable), et factoriser le pont v-model en composable `useStringConfigField(modelValue, key, emit)`.

### [MIN] Bornes de chunking et defauts d'options dupliques entre DTO Pydantic et value objects du domain

- **Localisation** : `document-parser/api/schemas.py:133-163` (`PipelineOptionsRequest`) et `:185-208` (`ChunkingOptionsRequest`) ; `document-parser/domain/value_objects.py:100-137` (`ConversionOptions`, `ChunkingOptions`) ; `frontend/src/features/chunks/ui/StrategyPopover.vue:52-53`
- **Constat** : les DTO de requete redeclarent champ par champ, **avec les memes valeurs par defaut**, les value objects du domain (`do_ocr=True`, `do_table_structure=True`, `table_mode="accurate"`, `images_scale=1.0`, `max_tokens=512`, `merge_peers=True`, …). Le flux est `Request.model_dump()` → `ConversionOptions(**dict)` (`services/analysis_service.py:398`), donc un defaut modifie d'un cote diverge silencieusement de l'autre. Par ailleurs les bornes `max_tokens` `64`/`8192` sont ecrites en litteral a la fois dans le validateur Pydantic (`schemas.py:206-207`) et dans le template (`StrategyPopover.vue :min="64" :max="8192"`), sans constante partagee — contrairement a `maxIterations` qui, lui, est correctement centralise en `MAX_ITERATIONS_MIN/MAX` des deux cotes.
- **Regle violee** : item 5.3 (defauts/bornes non nommes et dupliques) ; recoupe l'esprit de 5.6. Non bloquant.
- **Remediation** : deriver les defauts des DTO depuis les value objects du domain (ou centraliser les defauts dans le domain et ne laisser au DTO que l'aliasing camel/snake + la validation), et extraire `CHUNK_MAX_TOKENS_MIN/MAX` en constante backend exposee au front, sur le modele deja applique a `maxIterations`.

### [INFO] `fetch()` brut dans DownloadDropdown hors du client HTTP centralise

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:131`
- **Constat** : c'est le seul `fetch()` du front hors de `shared/api/http.ts`. Il est justifie fonctionnellement (`apiFetch` fait toujours `response.json()`, or ce cas a besoin du `Response` brut pour lire un `blob()` + parser le `content-disposition`), donc ce n'est pas une duplication de la config HTTP (pas de base URL ni de headers recopies). Reserve mineure : la gestion d'erreur (`response.ok`, statut 404) est reimplementee localement au lieu d'etre partagee.
- **Regle violee** : item 5.5 — observation, l'item reste conforme (aucune config HTTP dupliquee).
- **Remediation** : optionnel — exposer un helper `downloadBlob(url)` dans `shared/api/` pour mutualiser le pattern blob + parsing de nom de fichier si un second appelant apparait.

### [INFO] Petites constantes de troncature repetees dans l'infra

- **Localisation** : `document-parser/infra/neo4j/queries.py:104` et `:128` (`[:200]`), `document-parser/infra/docling_agent_reasoning.py:188` `:204` `:218` (`query[:120]`)
- **Constat** : la limite de troncature de texte `200` est ecrite deux fois dans `queries.py` (aperçu de noeud) et la troncature de log `query[:120]` trois fois dans `docling_agent_reasoning.py`. Ampleur negligeable, chaque repetition est locale a son fichier.
- **Regle violee** : item 5.3 — observation d'appoint, non bloquante.
- **Remediation** : promouvoir en constante module-level (`_PREVIEW_CHARS = 200`, `_LOG_QUERY_CHARS = 120`) si ces valeurs doivent rester coherentes.

---

## Points positifs

- **Client HTTP integralement centralise (item 5.5)** : les 11 modules `features/*/api.ts` passent tous par `apiFetch` (`shared/api/http.ts`) ; en-tetes `Content-Type`, gestion `response.ok`, extraction du `detail` d'erreur FastAPI (y compris le format `loc/msg` des 422) et court-circuit `204` sont ecrits une seule fois. Aucune recopie de base URL ni de headers.
- **Types partages reellement centralises (item 5.2)** : `shared/types.ts` porte les contrats transverses (`Document`, `Analysis`, `Chunk`, `DocChunk`, `DocTreeNode`, lifecycle…) ; les types restants (`reasoning/types.ts`, `admin-config/types.ts`, `store/api.ts`) sont authentiquement feature-scoped, pas des doublons d'un type partage. Cote back, `domain/models.py` et `domain/value_objects.py` sont l'unique source des entites et VO.
- **Schemas Pydantic transformateurs, pas redefinisseurs (item 5.6)** : les DTO de reponse projettent le domain via des constructeurs explicites `from_trace` / `from_step` / `from_payload` / `from_view` / `from_result` (`schemas.py:557-707`) et `asdict`, la serialisation camelCase est mutualisee par `_CamelModel` (un seul `_to_camel`), et le mot de passe de store n'est jamais serialise. La logique de mapping vit avec le modele qu'elle produit, pas eparpillee dans les routeurs.
- **Regles de validation sans desaccord front/back (item 5.7)** : la borne `maxIterations` est definie une fois par cote et alignee (`domain/app_config.py:22-23` = `1..20` ; `admin-config/types.ts:41-42` = `MAX_ITERATIONS_MIN/MAX`, consomme par `ReasoningConfigSection.vue:114-115`). Les enums metier (`table_mode`, `chunker_type`) ne sont valides qu'au niveau Pydantic ; le front n'introduit pas de regle concurrente contradictoire.
- **Reutilisation exemplaire de la palette par la feature reasoning** : `kindColors.ts:10` importe `ELEMENT_COLORS` et derive les teintes de badge par `color-mix`, plutot que de recoder des hex — le contre-exemple positif des ecarts couleur ci-dessus.
- **Helpers de formatage mutualises** : `shared/format.ts` (`formatSize`, `formatRelativeTime`, `formatAbsolute`) et `reasoning/timeline.logic.ts` (`fmtDur`, `fmtTick`, `computeBars`, `axisTicks`) concentrent le formatage duree/taille/temps a un seul endroit, consommes par les composants sans recopie.
- **Constantes de dimension et de statut nommees cote domain** : `DEFAULT_PAGE_WIDTH/HEIGHT` (`value_objects.py:14-15`) et `DOCUMENT_STATUS_UPLOADED` (`schemas.py:31`) sont des exemples corrects de magic values extraites et documentees.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL (la checklist DRY ne comporte aucun item poids 3, la severite
maximale atteignable est MAJ). Trois ecarts MAJOR — palette couleur redeclaree 4x
(5.1), helper datetime copie-colle 7x avec divergence UTC (5.1), couleurs UI en dur
non tokenisees (5.3) — restent sous le seuil bloquant (> 3 MAJ). Score 67 / 100
(tranche 60–79). Les trois MAJ sont des factorisations mecaniques a faible risque de
regression (constantes + helper pur + tokens CSS) : plan de remediation a executer
avant le prochain release, sans reprise fonctionnelle.
