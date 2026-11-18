# Plan de remédiation — Release 0.7.4

**Date** : 2026-11-18
**Point de départ** : re-audit sur `a6fb539`, global ≈ 80, 2 CRITICAL, 17 MAJOR ([summary.md](summary.md)).
**État** : passe à faible risque terminée et contrôlée, global ≈ 84, 2 CRITICAL, 14 MAJOR ([synthèse de contrôle](../release-0.7.4-control/summary.md)). Tout est en commits locaux sur `fix/0.7.4-editor-followups`, rien n'est poussé.
**Règle de tri** : a été traité ce qui ne change ni un contrat d'API, ni une dépendance, et que les tests unitaires suffisent à vérifier. L'application n'a pas été lancée. Le reste est reporté avec sa raison.

---

## 1. Fait dans cette passe

| Lot | Contenu | Items visés | Résultat au contrôle |
|-----|---------|-------------|----------------------|
| Architecture backend | Aperçus, tailles de page et comptages de pages derrière les ports `PageRasterizer` et `PdfInspector` ; `services/` n'importe plus aucune bibliothèque PDF ; ports complétés, `DocumentVersionRepository`, services typés sur des ports ; erreurs d'aperçu, d'export et d'import dans la famille `ServiceError` ; jointure des liens de store, état de l'historique d'édition et erreurs d'import sortis des routes ; verrou pdfium partagé | 01-1.2.4, 01-1.3.3, 06-6.1.4, 06-6.2.1 | 06 : 87 → 100. 01 : inchangé à 78, items réduits mais pas levés |
| Nommage | Plus de 200 fonctions renommées avec un verbe, en trois passes, backend et frontend. Routes, outils MCP, champs et clés inchangés | 03-3.1.1 | Conforme. 03 : 56 → 61 |
| Couleurs | Tokens manquants définis, replis littéraux retirés, blancs et hex en dur remplacés par les tokens, canvas compris. 7 tokens ajoutés | 05-5.3 | Conforme. 05 : 67 → 83 |
| Frontend | Un seul appel des résumés d'analyse ; un seul lecteur de `pagesJson` ; montage de `AnalysisDetailPage` en fonctions nommées ; aperçu de l'éditeur annulé à la fermeture | 03-3.2.1 (cas nouveau), 05 MIN | Cas nouveau de 3.2.1 résolu, 3 MIN de 05 résolus |
| Tests | Routes de versions, les 6 types de commande de l'éditeur, requêtes `Range` sur l'export PDF, rendu réel avec poppler, upload d'un vrai PDF, canvas PDF.js, câblage de l'inspecteur PDF | 09 MIN | 2 MIN sur 3 résolus. Backend 1501 → 1563 tests, frontend 586 → 605 |
| CI et build | CI sur les pushes de release, avec un jeton en lecture seule ; `pipefail` dans le gate ; images en Node 22 ; contextes Docker allégés ; cache et gzip des fichiers statiques dans nginx ; logo réduit | 10-10.2.4, 12-12.2.5, 12-12.3.1 | 10 : 70 → 75. 12 : 86 → 95 |
| Documentation | Chargement du PDF par plages derrière un proxy, mise à niveau depuis 0.7.3, routes et couches de 0.7.4, variables d'environnement, API et codes de retour de l'éditeur, CHANGELOG | 11 INFO | 4 INFO résolues. 11 inchangé à 72, il attend le freeze |

---

## 2. À faire par le mainteneur

| Action | Lève | Remarque |
|--------|------|----------|
| Lancer l'application et regarder : les écrans touchés par les couleurs, l'éditeur, la visionneuse PDF, un upload, une base 0.7.3 migrée | Les points « non vérifiés » | Les deux commits de couleurs (`1516a0c`, `2d5a80e`, plus `b5f8c7f`) sont isolés : un `git revert` les annule sans toucher au reste |
| Pousser la branche et ouvrir la PR vers `release/0.7.4` | 10-10.1.1 (CRIT) à la CI verte | La CI e2e construira pour la première fois les images en Node 22 et démarrera les nouveaux gabarits nginx |
| Trancher la PR #403 | — | Elle corrige #393 une seconde fois et entrera en conflit avec le commit local `eade7fa` |
| Commit de freeze : `## [0.7.4] - date`, `frontend/package.json` en 0.7.4 | 11-11.1.1 (CRIT), 11-11.2.1 (MAJ) | Audit 11 à 100. À cette occasion, décider si les correctifs de l'éditeur (#392 à #396), jamais publié, restent sous `Fixed` ou rejoignent son entrée `Added` |
| Release Gate sur la PR de release vers `main` | 08 (Trivy), 10 | Jamais lancé sur du contenu 0.7.4 |
| Protéger `release/**` avec les checks requis | Récidive de 10.1.1 | La PR #402 a été fusionnée sans qu'un job tourne |
| Fermer ou redater #378 (Pillow) avant le 2026-12-31 | 08-8.5.1 | Les 5 exceptions Trivy expirent ce jour-là |

---

## 3. Reporté, avec la raison

| Audit / item | Écart | Pourquoi pas maintenant | Cible proposée |
|--------------|-------|-------------------------|----------------|
| 01-1.2.4 | Accès directs au système de fichiers dans les services (`os.unlink`, `open`, `Path.stat`) | Un port de stockage de fichiers déplace l'écriture de l'upload et la suppression, avec sa garde contre la sortie du dossier d'upload. À faire application lancée. Gain : 01 à 84 | 0.8.0 |
| 01-1.3.3 | Deux reliquats : `json.loads` du modèle de l'éditeur dans la route, garde de l'export édité hors d'`ExportService` | Le premier est du mapping de réponse ; déplacer le second dans le service ferait répondre 404 avant 422 sur un format invalide. Gain avec le point précédent : 01 à 91 | 0.8.0 |
| 01-1.2.3 | Règles métier hors de `domain/` | Déplacement de logique dans l'éditeur et les chunks | 0.8.0 |
| 02-2.3.1 | MCP et Ask lisent l'analyse non éditée | Change ce que MCP répond : décision produit. La documentation dit maintenant ce que fait le code | 0.8.0 |
| 02-2.4.3 | Pas de racine d'agrégat pour l'état d'analyse active | Refonte de la persistance | 0.8.0 |
| 03-3.2.1, 03-3.3.2 | 9 fonctions et 5 fichiers trop gros (`chunk_service.py`, store et composant de l'éditeur, `PagePreviewWithOverlay.vue`) | Découpages de plusieurs centaines de lignes, dont de l'interface. Trois fonctions sont dans le code Neo4j, à retirer en 0.8.0. Gain : 03 à 83 | 0.8.0 |
| 04-4.2 | Abstraction de fournisseur LLM à un seul membre | Retirer `LLM_PROVIDER_TYPE` supprime une variable d'environnement documentée | 0.8.0, avec dépréciation |
| 05-5.1 | Pile de titres écrite 4 fois | Les quatre copies divergent : les unifier change le plan ou les chunks de certains documents. Gain : 05 à 100 | 0.8.0, avec des documents de référence |
| 07-7.4.2 | `dict` dans les schémas de l'éditeur | Typer la réponse peut filtrer des champs que le front lit | 0.8.0 |
| 08 MAJ | `Host` non validé sur `/api/*` (rebinding DNS) | Un `TrustedHostMiddleware` mal réglé coupe tout déploiement derrière un nom d'hôte non prévu : valeur par défaut à choisir et à tester application lancée | 0.7.4 si testé, sinon 0.8.0 |
| 09-9.1.3 | Specs Karate UI périmées, éditeur hors `@critical`, aucun test du rendu PDF.js | Les e2e demandent la pile lancée | Avec la PR de release |
| 09 MIN | 64 tests backend jamais lancés en CI faute de `docling` | Arbitrage de coût de CI | 0.8.0 |
| 10-10.2.3 | Image `local` jamais construite ni scannée par le gate | Modifie le Release Gate et sa durée | 0.8.0 |
| 12-12.3.2 | Réponse de l'éditeur de 13,8 Mo à 300 pages | Demande de revoir le contrat de l'éditeur | 0.8.0 |
| 12 INFO | Suppression d'un document : charge toutes les analyses pour les compter | Les résumés sont plafonnés à 200, il faut un compteur côté backend | 0.8.0 |

---

## 4. Notes mesurées

| Audit | 13/11 | Avant remédiation | Après | Après CI verte et freeze |
|-------|-------|-------------------|-------|--------------------------|
| 01 Hexagonal Architecture | 69 | 78 | 78 | 78 |
| 02 DDD | 75 | 83 | 83 | 83 |
| 03 Clean Code | 39 | 56 | 61 | 61 |
| 04 KISS | 75 | 75 | 75 | 75 |
| 05 DRY | 67 | 67 | 83 | 83 |
| 06 SOLID | 87 | 87 | 100 | 100 |
| 07 Decoupling | 91 | 94 | 94 | 94 |
| 08 Security | 97 | 97 | 97 | 97 |
| 09 Tests | 85 | 93 | 93 | 93 |
| 10 CI / Build | 85 | 70 | 75 | 90 |
| 11 Documentation | 61 | 72 | 72 | 100 |
| 12 Performance | 52 | 86 | 95 | 95 |
| **Global** | **74** | **80** | **84** | **87** |
| CRITICAL | 4 | 2 | 2 | 0 |
| MAJOR | 24 | 17 | 14 | 13 |

La dernière colonne est une projection : elle suppose une CI verte et le commit de freeze, rien d'autre.
