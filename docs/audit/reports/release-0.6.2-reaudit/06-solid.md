# Rapport d'audit : SOLID (re-audit)

**Release** : 0.6.2 (branche `fix/0.6.2-audit-blockers`)
**Date** : 2026-06-08
**Auditeur** : claude-code
**HEAD** : `f6b4e23` (build: cut implicit HuggingFace Hub deps across all images and pipelines)
**Baseline** : `release-0.6.2/06-solid.md` — 100/100, GO (0 CRIT / 0 MAJ / 0 MIN / 1 INFO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 15 / 15 (31 / 31 ponderes) |
| Score | **100 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 1 |

**Delta vs baseline `release-0.6.2/06-solid.md`** : **0 point** (100 → 100). 1 INFO maintenu.

### Detail par item (fiche `docs/audit/audits/06-solid.md`)

| # | Item | Poids | Statut | Delta vs baseline |
|---|------|-------|--------|-------------------|
| 6.1.1 | Service = responsabilite unique | 2 | OK | = |
| 6.1.2 | Store Pinia mono-feature | 2 | OK | = |
| 6.1.3 | Routers REST groupes par ressource | 1 | OK | = |
| 6.1.4 | Pas de service cumulant responsabilites | 2 | OK | = |
| 6.2.1 | Ports permettent ajout d'adaptateurs sans modif | 2 | OK | = |
| 6.2.2 | Local/remote extensible via `_build_converter()` | 2 | OK (renforce — voir contexte) | = |
| 6.2.3 | Ajout format export sans toucher endpoints | 1 | OK | = |
| 6.3.1 | `LocalConverter` / `ServeConverter` interchangeables | 3 | OK | = |
| 6.3.2 | Implementations de ports ne levent pas d'exceptions hors contrat | 2 | OK | = |
| 6.3.3 | Aucun `isinstance` / `type()` discriminant un adaptateur | 2 | OK | = |
| 6.4.1 | `DocumentConverter` et `DocumentChunker` ports separes | 2 | OK | = |
| 6.4.2 | Aucun port ne force des methodes inutilisees | 2 | OK | = |
| 6.5.1 | Services dependent de protocoles abstraits | 3 | OK | = |
| 6.5.2 | Injection dans `main.py` (composition root) | 2 | OK | = |
| 6.5.3 | Pas d'instanciation directe d'adaptateurs en services | 3 | OK (renforce cote tests) | = |

**Calcul** (formule master.md §3) : poids conformes = 31 / 31 × 100 = **100 / 100**.

---

## Contexte du re-audit

La fenetre `fix/0.6.2-audit-blockers` (8 commits depuis `release/0.6.2 @ 051ac4a`) cible les blockers tour 1 (CI / Securite / Docs / HF). **Le diff sur la surface SOLID applicative est zero ligne** :

```bash
$ git diff release/0.6.2..HEAD -- document-parser/services/ \
    document-parser/domain/ports.py document-parser/infra/ \
    document-parser/api/ document-parser/persistence/
# 0 ligne — surface byte-identique
```

Les seules surfaces touchees par la fenetre :

| Element | Type | Impact SOLID |
|---------|------|--------------|
| `dd1962e` — service `docling-serve` ajoute aux deux compose | Compose (runtime infra hors process) | Aucun — pas de code Python, le chemin de consommation existait deja via `ServeConverter` |
| `f6b4e23` — `BAKE_MODELS=false` par defaut sur les 3 Dockerfiles | Build | Aucun — gating de build, surface SOLID non touchee |
| `bc9b4f8` — CI E2E pilote par `docling-serve` distant | CI | Aucun — choix de runtime du test, pas du code |
| `29ab575` — `tests/test_chunking.py` mock le port `DocumentChunker` au lieu d'instancier `LocalChunker` | Tests | **Positif DIP cote tests** — voir Points positifs #14 |
| Audits docs + CHANGELOG + `.trivyignore.yaml` | Docs / Securite | Hors perimetre SOLID |

La conformite 100/100 du baseline est **transposee mecaniquement**. Le re-audit confirme l'absence de regression silencieuse via re-execution des commandes de la fiche.

---

## Verification des principes

### SRP (6.1)

- **6.1.1 / 6.1.4 conforme** : Les 8 services applicatifs (`AnalysisService`, `ChunkService`, `DocumentService`, `GraphService`, `IngestionService`, `StoreBackendResolver`, `StoreService`, `VersionService`) restent mono-responsabilite. Aucun fichier touche par la fenetre.
- **6.1.2 conforme** : 10 stores Pinia, un feature = un store. Frontend non touche par la fenetre.
- **6.1.3 conforme** : 8 routers REST groupes par ressource — identique au baseline.

### OCP (6.2)

- **6.2.1 conforme** : 17 Protocols declares dans `document-parser/domain/ports.py`. Aucune ligne modifiee.
- **6.2.2 conforme — RENFORCE par le contexte de la fenetre** : `main.py:49-64` `_build_converter()` choisit toujours `LocalConverter` ou `ServeConverter` via `settings.conversion_engine`. La switch CI E2E du commit `bc9b4f8` consomme exactement ce point d'extension via la variable d'environnement existante (`DOCUMENT_PARSER_CONVERSION_ENGINE=serve`). Aucune modification du service, du port, ni de la factory — c'est la **demonstration empirique** que l'OCP fonctionne : une nouvelle topologie de runtime (CI sur container distant) a pu etre branchee sans toucher au code applicatif.
- **6.2.3 conforme** : `domain/value_objects.py` non modifie.

### LSP (6.3)

- **6.3.1 conforme** : `LocalConverter` et `ServeConverter` toujours interchangeables, contrat `ConversionResult` identique. Le carry de `self_ref` introduit par `#3936166` (baseline) reste en place — `serve_converter.py:250,270` aligne sur `local_converter.py:202`. La fenetre n'a pas touche `infra/`.
- **6.3.2 conforme** : Exceptions typees au domaine (`ReasoningParseError`, `GraphServiceError`/hierarchie, `StoreBackendNotConfiguredError`) inchangees.
- **6.3.3 conforme** : `grep -rn "isinstance\|type(" document-parser/services/` retourne 3 occurrences (`store_service.py:135,139` ; `chunk_service.py:218`), toutes sur des types primitifs (`str`, `list`). Zero discrimination d'adaptateur. Identique au baseline.

### ISP (6.4)

- **6.4.1 conforme** : `DocumentConverter` et `DocumentChunker` toujours ports separes (`ports.py:52-87`).
- **6.4.2 conforme** : 17 ports, ~3.7 methodes/port. Documentation anti-no-op de `GraphWriter` toujours presente. Aucune ligne touchee.

### DIP (6.5)

- **6.5.1 conforme** : Re-execution des grep de la fiche :

  ```
  $ grep -rn "^from infra\|^import infra" document-parser/services/
  (zero match)

  $ grep -rn "from infra\.\|import infra\." document-parser/services/ --include="*.py"
  document-parser/services/store_backend_resolver.py:40:    from infra.neo4j.driver_pool import Neo4jDriverPool
  document-parser/services/store_backend_resolver.py:41:    from infra.opensearch_pool import OpenSearchClientPool
  document-parser/services/store_backend_resolver.py:42:    from infra.opensearch_store import OpenSearchStore
  document-parser/services/chunk_service.py:170:        # `from infra.docling_tree import ...` smell hiding inside two
  ```

  Resultat **strictement identique** au baseline : 3 imports sous `if TYPE_CHECKING:` (annotation mypy uniquement) + 1 occurrence dans un commentaire docstring. Aucun import runtime. DIP intacte.

- **6.5.2 conforme** : Composition root `document-parser/main.py:255-348` non modifie. `_build_converter()` (lignes 49-64) et `_build_chunker()` (74) instancient les adaptateurs concrets ; tous les ports sont injectes aux services. La nouvelle topologie docling-serve passe par ce meme point — pas un contournement.

- **6.5.3 conforme — RENFORCE cote tests** : Re-execution :

  ```
  $ grep -rn "LocalConverter\|ServeConverter\|LocalChunker\|OpenSearchStore" \
      document-parser/services/ --include="*.py"
  document-parser/services/store_backend_resolver.py:11:  # docstring
  document-parser/services/store_backend_resolver.py:42: # TYPE_CHECKING
  document-parser/services/store_backend_resolver.py:61: # annotation
  ```

  Aucune instanciation directe en `services/`. Par ailleurs, le commit `29ab575` ameliore la discipline DIP cote tests : `test_rechunk_with_serve_document_json` n'instancie plus `LocalChunker()` mais mocke le port `DocumentChunker` (`AsyncMock`). Le test prouve maintenant que le service depend bien du port, pas d'une implementation. C'est un signal **positif** sur 6.5.1/6.5.3.

---

## Verification specifique de la nouveaute 0.6.2 — switch docling-serve en CI

Le brief mentionne la consommation docling-serve en CI. Verification SOLID dediee :

| Aspect | Constat |
|--------|---------|
| Le service `docling-serve` ajoute dans `docker-compose.yml` est-il consomme via un adaptateur respectant `DocumentConverter` ? | OUI — `infra/serve_converter.py::ServeConverter` (baseline 0.6.2, non touche). |
| Le switch CI a-t-il introduit un nouveau chemin d'import depuis `services/` vers `infra/` ? | NON — `grep` ci-dessus zero match runtime. La selection est faite en haut de `main.py:_build_converter()` via variable d'environnement. |
| La factory `_build_converter()` a-t-elle ete modifiee pour le switch ? | NON — `git diff release/0.6.2..HEAD -- document-parser/main.py` = 0 ligne. La factory existante (0.6.2) supportait deja `conversion_engine=serve`. |
| OCP demontre ? | OUI — la **topologie de runtime** a change (container distant vs local in-process) sans **aucune** modification du code applicatif. C'est le cas d'usage canonique d'OCP : extension par point d'extension existant, fermeture sur le code modifie. |

---

## Ecarts constates

### [INFO] LSP — declaration `@property` vs attribut de classe pour `supports_page_batching`

- **Localisation** :
  - `document-parser/domain/ports.py:67-74` — declare `@property def supports_page_batching(self) -> bool`
  - `document-parser/infra/local_converter.py:286` — `supports_page_batching: bool = True`
  - `document-parser/infra/serve_converter.py:64` — `supports_page_batching: bool = False`
- **Constat** : INFO herite du baseline 0.6.2 (lui-meme herite de 0.6.1 reaudit). Aucune ligne touchee par la fenetre. Le contrat fonctionne au runtime ; la divergence de forme est purement cosmetique (`mypy --strict` pourrait raler).
- **Regle violee** : Aucune (forme stricte de 6.3.1 — meme contrat de retour respecte).
- **Remediation** : Harmoniser sur l'attribut simple OU rendre les deux adaptateurs `@property`. **Non-bloquant** pour le release 0.6.2.

---

## Points positifs

1. **Surface SOLID byte-identique au baseline 0.6.2** : `git diff release/0.6.2..HEAD -- document-parser/services/ document-parser/domain/ports.py document-parser/infra/ document-parser/api/ document-parser/persistence/` retourne **zero ligne**. La conformite 100/100 est mecaniquement preservee.
2. **DIP totale — services purement ports** : Aucun `from infra.*` runtime dans `document-parser/services/`. La couche service ne connait que des ports.
3. **OCP demontre empiriquement par la fenetre** : Le commit `bc9b4f8` (switch CI E2E vers docling-serve distant) consomme le point d'extension `_build_converter()` **sans modifier une seule ligne** de service, port ou factory. C'est la preuve par l'usage que l'architecture est ouverte a l'extension, fermee a la modification.
4. **Composition root scellee** : `main.py:255-348` (non touche) reste l'unique lieu d'instanciation des adaptateurs concrets (`LocalConverter`, `ServeConverter`, `LocalChunker`, `OpenSearchStore` via pool, `Neo4jGraphReader`, `Neo4jGraphWriter`, `DoclingTreeReader`, `DoclingGraphProjector`).
5. **Factory pattern preserve** : `StoreBackendResolver` recoit toujours un `graph_writer_factory: Callable[[Any], GraphWriter]` injecte avec `Neo4jGraphWriter` par `main.py:298`.
6. **LSP confirme — `LocalConverter` / `ServeConverter` interchangeables** : Contrat de retour `ConversionResult` identique, carry `self_ref` aligne par #3936166. La switch CI E2E vers le container distant est une **validation runtime** de cette substitution.
7. **LSP — Adaptateurs port-only sans logique** : `DoclingTreeReader`, `DoclingGraphProjector`, `Neo4jGraphReader`, `Neo4jGraphWriter` toujours shims stateless.
8. **ISP — Ports finement segreges** : 17 ports, ~3.7 methodes/port, documentation anti-no-op sur `GraphWriter`.
9. **DIP — Aucune fuite infra dans `api/`** : `grep -rn "from infra" document-parser/api/` retourne 0 match.
10. **DIP — Encapsulation infra des secrets** : `FernetBox` n'est importe que par `persistence/store_repo.py`. Inchange.
11. **DIP — Pools infra confines** : `Neo4jDriverPool` et `OpenSearchClientPool` toujours TYPE_CHECKING-only dans `StoreBackendResolver`.
12. **Validation automatisee** : `tests/test_architecture.py` declare toujours les regles de couches (`services -> no import from api, infra, persistence`).
13. **SRP — Routes API et stores Pinia** : 8 routers REST, 10 stores Pinia, un router = une ressource, un store = un feature.
14. **DIP renforce cote tests (commit `29ab575`)** : `test_rechunk_with_serve_document_json` mocke desormais le port `DocumentChunker` (`AsyncMock`) au lieu d'instancier `LocalChunker()`. Le test prouve maintenant que `AnalysisService.rechunk` consomme bien un port, pas une implementation. Effet de bord positif du correctif HF — la dependance test -> infra est elle aussi rompue.

---

## Verdict partiel : GO

**Score** : **100 / 100** (delta **0** vs baseline `release-0.6.2/06-solid.md`).
**Ecarts CRITICAL** : 0 — release autorisee.
**Ecarts MAJOR** : 0.
**Ecarts MINOR** : 0.
**Ecarts INFO** : 1 (LSP `@property` vs attribut — reporte au prochain cycle, non-bloquant).

SOLID reste exemplaire. La fenetre `fix/0.6.2-audit-blockers` **n'a touche aucune ligne** de la surface applicative SOLID, et le switch docling-serve en CI a au contraire **demontre** l'OCP en consommant le point d'extension `_build_converter()` sans modifier le code. Effet de bord positif : le commit `29ab575` ameliore la discipline DIP cote tests en mockant le port `DocumentChunker` au lieu d'instancier `LocalChunker`. Aucune regression silencieuse detectee par les commandes de la fiche.
