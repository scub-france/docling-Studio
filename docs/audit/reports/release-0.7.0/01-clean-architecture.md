# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 9 / 13 |
| Score | 78 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 2 |

Detail du calcul : poids conformes = 25 sur 32 (1.1.1=3, 1.1.2=3, 1.1.3=3,
1.1.4=2, 1.2.1=3, 1.2.2=3, 1.3.1=3, 1.4.1=3, 1.4.2=2). Items non conformes :
1.2.3 (2), 1.2.4 (2), 1.3.2 (1), 1.3.3 (2). `25 / 32 * 100 = 78,1` -> **78**.

---

## Ecarts constates

### [MAJ] Les regles metier de split/merge de chunks vivent dans le service, pas dans le domain

- **Localisation** : `services/chunk_service.py:335` (`split_chunk`) et `services/chunk_service.py:393` (`merge_chunks`) ; module domaine orphelin `domain/chunk_editing.py:169` (`split`) et `domain/chunk_editing.py:116` (`merge`).
- **Constat** : Le domaine expose deja un module pur `domain/chunk_editing.py` dont le docstring precise l'intention : « The `ChunkEditingService` (in `services/`) wraps each call with audit-record generation and atomic persistence. » Or **aucun** fichier de `services/`, `api/`, `bootstrap/` n'importe `domain.chunk_editing` (verifie par `grep -rn chunk_editing services/ api/ bootstrap/`). Le service `chunk_service.py` reimplemente inline toute la mecanique metier : validation d'offset (`cursor_offset <= 0 or cursor_offset >= len(source.text)`, ligne 337), decoupage du texte (`head_text = source.text[:cursor_offset]`, ligne 346), decalage des sequences (ligne 368), reconstruction des chunks. Les deux implementations **divergent** de surcroit : la version service propage `bboxes`/`doc_items`/`token_count` (lignes 354-355, 415-419), la version domaine ne les propage pas. Le module domaine est donc du code mort et la regle metier authoritative a migre dans la couche d'orchestration.
- **Regle violee** : item 1.2.3 — « Les regles metier vivent dans `domain/`, pas dans les services » (poids 2).
- **Remediation** : Faire appeler par `ChunkService.split_chunk` / `merge_chunks` les fonctions pures `domain.chunk_editing.split` / `merge`, en enrichissant ces dernieres pour couvrir `bboxes`/`doc_items`/`token_count` si necessaire. Le service ne conserve que l'orchestration (persistence + ecriture de l'audit). Supprimer la duplication et le risque de divergence.

### [MAJ] Les services importent directement des librairies d'infrastructure PDF (concretions non injectees)

- **Localisation** : `services/document_service.py:13` (`from pdf2image import convert_from_bytes, pdfinfo_from_bytes`) et `services/analysis_service.py:17` (`import pypdfium2 as pdfium`).
- **Constat** : Deux services dependent en import direct de librairies d'infrastructure I/O sans passer par un port de `domain/ports.py` ni par injection. `document_service.py` appelle `convert_from_bytes` pour rasteriser une page (ligne 145), `pdfinfo_from_bytes`/poppler pour compter les pages (ligne 171) et ecrit le fichier sur disque (`open(...)` ligne 164, `os.unlink` ligne 93). `analysis_service.py` ouvre le PDF via `pdfium.PdfDocument(file_path)` (ligne 61). Ironiquement le docstring d'`analysis_service.py:3-4` affirme « Uses injected ports (converter, chunker, repositories) so the service is decoupled from infrastructure implementations » — ce qui n'est pas vrai pour la rasterisation/pagination PDF. Aucun port (type `PdfRasterizer` / `PageCounter` / `FileStorage`) n'existe ; le service reache directement la concretion.
- **Regle violee** : item 1.2.4 — « Les services recoivent leurs dependances par injection, pas par import direct de concretions » (poids 2).
- **Remediation** : Definir un ou des ports dans `domain/ports.py` (p.ex. `PagePreviewRenderer`, `PageCounter`, `FileStorage`) et deplacer `pdf2image`/`pypdfium2`/l'ecriture disque dans un adaptateur `infra/`. Injecter l'adaptateur dans `DocumentService` / `AnalysisService` via `bootstrap/factories.py`, comme c'est deja fait proprement pour le converter, le chunker et les repos.

### [MAJ] L'endpoint GET /api/documents/{id} orchestre deux depots et une jointure dans la couche HTTP

- **Localisation** : `api/documents.py:41` (`_fetch_store_links`), appele par le handler `get` en `api/documents.py:113-122` ; ports injectes directement via `api/deps.py:89-105` (`StoreRepoDep`, `DocumentStoreLinkRepoDep`).
- **Constat** : Le handler HTTP recoit directement deux ports de depot (`link_repo: deps.DocumentStoreLinkRepoDep`, `store_repo: deps.StoreRepoDep`, lignes 115-116) puis delegue a `_fetch_store_links`, qui realise une **orchestration metier** dans la couche API : deux appels depot (`link_repo.find_for_document`, ligne 53 ; `store_repo.find_all`, ligne 58) et une jointure `store_id -> slug` (`slug_by_id = {s.id: s.slug for s in stores}`, ligne 59). Ce cas d'usage (enrichir un document de ses liens de stores resolus par slug) devrait vivre dans un service, pas dans le routeur. Note : l'item 1.3.1 reste conforme (aucun import de `persistence/`, ce sont des ports de `domain.ports`), mais la logique n'est pas deleguee.
- **Regle violee** : item 1.3.3 — « Les endpoints delegent toute la logique aux services » (poids 2).
- **Remediation** : Deplacer `_fetch_store_links` dans `DocumentService` (p.ex. `get_with_store_links(doc_id)`), qui recoit deja `document_repo`/`analysis_repo` par injection ; y injecter aussi les depots store/link. Le routeur se limite au mapping DTO. Retirer `StoreRepoDep`/`DocumentStoreLinkRepoDep` de la surface directe des handlers.

### [MIN] Les transformations snake_case -> camelCase fuient hors de api/schemas.py

- **Localisation** : `services/chunk_service.py:105-108` et `:858-861`, `services/analysis_service.py:47-50`, `services/version_service.py:53-62`.
- **Constat** : Le mecanisme canonique de conversion de casse est `api/schemas.py` via `alias_generator=_to_camel` (`api/schemas.py:34,43`). Pourtant plusieurs services construisent a la main des dicts en camelCase pour le contrat API : `analysis_service.py` (`"sourcePage"`, `"tokenCount"`, `"docItems"`/`"selfRef"`, lignes 47-50, docstring explicite « Serialize ChunkResult to a camelCase dict matching the frontend API contract »), `chunk_service.py` (`"sourcePage"`, `"tokenCount"`, `"chunkId"`, `"pushId"`, `"documentId"`, `"storeSlug"`, lignes 105-108, 555-569, 686, 731-738, 858-861) et `version_service.py` (`"documentId"`, `"sourcePage"`, `"docItems"`, `"createdAt"`, lignes 53-62). La responsabilite de mapping du contrat wire est ainsi eclatee entre la couche services et la couche api.
- **Regle violee** : item 1.3.2 — « Les transformations camelCase/snake_case restent dans `api/schemas.py` » (poids 1).
- **Remediation** : Faire retourner par les services des objets/DTO en snake_case (ou des value objects domaine) et laisser les modeles Pydantic de `api/schemas.py` operer la conversion via `alias_generator`. Reserver les dicts camelCase construits a la main aux seuls formats reellement persistes (audit log) si necessaire.

### [INFO] Couplage inter-adaptateurs : persistence importe infra

- **Localisation** : `persistence/store_repo.py:25` (`from infra.secrets import get_fernet_box`).
- **Constat** : La couche `persistence/` (adaptateur SQLite) importe directement `infra.secrets` pour chiffrer/dechiffrer le mot de passe de connexion des stores. Ce n'est couvert par aucun item de la checklist (le flux `api -> services -> domain` et l'absence d'import framework dans le domain restent respectes), mais c'est un couplage adaptateur->adaptateur qui, a terme, gagnerait a passer par un port de chiffrement.
- **Remediation** (facultatif) : Definir un port `SecretBox` cote domaine et injecter l'implementation Fernet, plutot qu'un import direct depuis `persistence/`.

### [INFO] Un composant Vue effectue un fetch HTTP direct (hors couche api de la feature)

- **Localisation** : `frontend/src/features/document/ui/DownloadDropdown.vue:131` (`const response = await fetch(url)`).
- **Constat** : La separation vues/services/stores du frontend est globalement saine (chaque store importe son `./api`, aucun import croise inter-features detecte). Seule exception reperee dans le perimetre : `DownloadDropdown.vue` appelle `fetch()` directement au lieu de passer par le module `api.ts` de sa feature. Aucun item de checklist de cet audit ne couvre le frontend ; observation informative.
- **Remediation** (facultatif) : Deplacer l'appel reseau dans `features/document/api.ts` et l'invoquer depuis le composant/store.

---

## Points positifs

- **Domain 100% pur** : aucun import de `fastapi`, `aiosqlite`, `pydantic` ni d'aucune lib infra dans `domain/` ; aucune I/O (fichier, HTTP, DB, subprocess) — items 1.1.1 et 1.1.2 pleinement conformes.
- **Ports bien concus** : `domain/ports.py` regroupe 16 `Protocol` typedes (converter, chunker, repos, vector store, graph reader/writer, reasoning runner, LLM provider/probe, tree reader...) exprimant les besoins du domaine sans fuite d'infra — item 1.1.3 conforme.
- **Dataclasses partout** : `domain/models.py`, `domain/value_objects.py`, `domain/app_config.py` utilisent `@dataclass` et `StrEnum`, jamais Pydantic — item 1.1.4 conforme.
- **Sens des dependances respecte** : le domain n'importe aucune couche externe ; `infra/` n'importe ni `api`, ni `services`, ni `persistence` (verifie) ; les imports `persistence`/`infra` cotes `services/` sont tous confines a des blocs `if TYPE_CHECKING`.
- **Composition root propre** : `bootstrap/builder.py` + `bootstrap/factories.py` centralisent le cablage (choix des adaptateurs, injection). `StoreBackendResolver` recoit meme une `graph_writer_factory` opaque pour ne jamais runtime-importer `infra` cote services — exemple de DI exemplaire (item 1.2.4 respecte ailleurs).
- **API sans acces persistence direct** : aucun routeur de `api/` n'importe `persistence/` (item 1.3.1 conforme) ; les services ne touchent jamais `fastapi` ni de SQL brut (items 1.2.1 et 1.2.2 conformes).
- **Adaptateurs alignes sur les ports** : `LocalConverter`/`ServeConverter` (dont la propriete `supports_page_batching`), `LocalChunker`, `EmbeddingClient`, `OpenSearchStore`, `DoclingTreeReader`, `Neo4jGraphReader`/`Neo4jGraphWriter`, `OllamaProvider`/`OllamaProbe`, `DoclingAgentReasoningRunner` implementent chacun un `Protocol` de `domain/ports.py` — item 1.4.1 conforme.
- **Config centralisee** : les valeurs de configuration proviennent de `infra/settings.py` et sont injectees ; les seules occurrences d'URL/hote dans `infra/` sont des exemples en docstring — item 1.4.2 conforme.
- **Frontend feature-based net** : chaque feature isole `api.ts` (services), `store.ts` (Pinia), `ui/*.vue` (vues) ; aucun import de store d'une autre feature detecte.

---

## Verdict partiel : GO CONDITIONNEL

Aucun ecart CRITICAL — les sept items de poids 3 (couches pures, ports, flux
de dependances, adaptateurs) sont tous conformes. Score 78/100 dans la plage
60-79. Trois ecarts MAJOR (exactement, donc non bloquants selon la regle
« > 3 MAJOR »), a couvrir par un plan de remediation avant le prochain cycle :

1. Reunifier les regles metier split/merge dans `domain/chunk_editing.py` (item 1.2.3).
2. Placer les librairies PDF derriere des ports injectes (item 1.2.4).
3. Deplacer la jointure store-links de `api/documents.py` vers un service (item 1.3.3).
