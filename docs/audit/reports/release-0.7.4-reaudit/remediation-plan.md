# Plan de remédiation — Release 0.7.4

**Date** : 2026-11-18
**Point de départ** : re-audit sur `a6fb539`, global ≈ 80, 2 CRITICAL, 17 MAJOR ([summary.md](summary.md)).
**Règle de tri** : est traité tout de suite ce qui ne change ni un contrat d'API, ni un comportement visible, ni une dépendance, et que les tests unitaires suffisent à vérifier. L'application n'est pas lancée pendant cette remédiation. Le reste est reporté avec sa raison.

---

## 1. Traité dans cette passe (risque faible)

| Lot | Contenu | Audits / items visés | Vérification |
|-----|---------|----------------------|--------------|
| A — Architecture backend | `PreviewService` passe par le port `PageRasterizer` au lieu de `DocumentService.generate_preview` ; lecture des tailles de page derrière un port ; erreurs d'aperçu et d'export dans la famille `ServiceError` ; méthodes manquantes ajoutées aux `Protocol`, port `DocumentVersionRepository`, constructeurs de services typés sur des ports ; hash de source des chunks calculé à un seul endroit ; verrou pdfium | 01-1.2.4, 01-1.3.3, 06-6.1.4, 06-6.2.1, 02 MIN, 05 MIN, 12 MIN | pytest, ruff, `tests/test_architecture.py` |
| B — Nommage | Fonctions nommées d'après leur résultat renommées avec un verbe, surtout dans `mcp_adapter/`. Les noms d'outils MCP, de prompts et de champs ne changent pas | 03-3.1.1 | pytest, vitest, script de mesure de l'audit 03 |
| C — Couleurs | Tokens CSS manquants définis une fois, replis hexadécimaux retirés des composants, `BboxCanvas` lit les mêmes tokens | 05-5.3 | eslint, vue-tsc, vitest ; **aucune vérification visuelle** |
| D — Frontend | Un seul appel `/api/analyses/summaries` ; `parseAnalysisPages` réutilisé ; montage de `AnalysisDetailPage` découpé en fonctions nommées ; suppression d'un document comptée sur les résumés ; constante nommée pour la taille des plages PDF.js ; minuteur d'aperçu annulé au démontage ; tests de `PdfPageCanvas` | 03-3.2.1 (cas nouveau), 05 MIN, 09, 12 INFO | vitest, vue-tsc |
| E — Tests backend | Tests HTTP des routes de versions ; un test HTTP par type de commande de l'éditeur ; test `Range` sur l'export PDF que charge PDF.js ; un test de rendu réel avec poppler ; commentaires périmés ; avertissements `never awaited` | 09 MIN, 07/10/12 « non vérifié » | pytest |
| F — CI et build | CI déclenchée sur les pushes vers `release/**` ; `pipefail` dans le job de tests du gate ; images construites en Node 22 comme la CI (`pdfjs-dist` demande Node ≥ 22.13) ; `out/` et `__pycache__` dans `.dockerignore`, nouveau `frontend/.dockerignore` ; cache d'un an et gzip pour `/assets/` dans les deux gabarits nginx ; logo réduit de 878 Ko à 61 Ko | 10-10.1.1 (prévention), 10-10.2.4, 12-12.2.5, 12-12.3.1 | relecture ; **nginx et Docker non exécutés**, la CI e2e les validera |
| G — Documentation | Chargement du PDF par plages derrière un proxy, cache d'aperçus, `format=webp` ; note de montée de version depuis 0.7.3 ; `docs/architecture.md` et `docs/configuration.md` alignés sur le code ; éditeur mentionné dans le README | 11 INFO | liens vérifiés par script |
| H — CHANGELOG | Section `[Unreleased]` restructurée : les correctifs d'une fonctionnalité jamais publiée rejoignent son entrée, numéros de PR ajoutés, une seule entrée pour l'affichage des PDF | 11-11.1.4 | relecture contre le code |

---

## 2. À faire par le mainteneur (décisions de release)

| Action | Lève | Remarque |
|--------|------|----------|
| Pousser `fix/0.7.4-editor-followups` et ouvrir la PR vers `release/0.7.4` | 10-10.1.1 (CRIT) dès que la CI est verte | Rien n'est poussé sans accord |
| Trancher la PR #403 (second correctif de #393) | — | Elle double le commit local `eade7fa` et entrera en conflit. La fermer en la créditant, ou la fusionner d'abord puis résoudre |
| Commit de freeze : `## [0.7.4] - date`, `frontend/package.json` en 0.7.4 | 11-11.1.1 (CRIT), 11-11.2.1 (MAJ) | Audit 11 à 100 |
| Lancer l'application une fois : éditeur, visionneuse PDF.js, couleurs du lot C, base 0.7.3 migrée | Points « non vérifiés » | Aucun test avec application démarrée n'a été fait |
| Release Gate sur la PR de release vers `main` | 08 (Trivy), 10 | Jamais lancé sur du contenu 0.7.4 |
| Fermer ou redater #378 (Pillow) avant le 2026-12-31 | 08-8.5.1 | Les 5 exceptions Trivy expirent ce jour-là |

---

## 3. Reporté, avec la raison

| Audit / item | Écart | Pourquoi pas maintenant | Cible proposée |
|--------------|-------|-------------------------|----------------|
| 08 MAJ | `Host` non validé sur `/api/*` (rebinding DNS) | Un `TrustedHostMiddleware` mal réglé coupe tout déploiement derrière un nom d'hôte non prévu (Space Hugging Face, proxy). Il faut choisir la valeur par défaut et la tester application lancée | 0.7.4 si testé, sinon 0.8.0 |
| 02-2.3.1 | MCP et Ask lisent l'analyse non éditée | Change ce que MCP répond : décision produit | 0.8.0 |
| 02-2.4.3 | Pas de racine d'agrégat pour l'état d'analyse active | Refonte de la persistance | 0.8.0 |
| 01-1.2.3 | Règles métier hors de `domain/` | Déplacement de logique dans l'éditeur et les chunks, à faire avec des tests de non-régression fonctionnels | 0.8.0 |
| 03-3.2.1, 03-3.3.2 | Fonctions et fichiers trop gros (`chunk_service.py`, store et composant de l'éditeur, `PagePreviewWithOverlay.vue`) | Découpages de plusieurs centaines de lignes, dont de l'interface non vérifiable sans lancer l'application. Trois des fonctions sont dans le code Neo4j, dont le retrait est prévu en 0.8.0 | 0.8.0 |
| 04-4.2 | Abstraction de fournisseur LLM à un seul membre | Retirer `LLM_PROVIDER_TYPE` supprime une variable d'environnement documentée | 0.8.0, avec dépréciation |
| 05-5.1 | Pile de titres écrite 4 fois | Les quatre copies divergent (racine, niveau d'un `title`, définition d'un titre) : les unifier change le plan ou les chunks de certains documents | 0.8.0, avec un jeu de documents de référence |
| 07-7.4.2 | `dict` dans les schémas de l'éditeur | Typer la réponse peut filtrer des champs que le front lit | 0.8.0 |
| 09-9.1.3 | Specs Karate UI périmées, éditeur hors `@critical` | Les e2e demandent la pile lancée | Avec la PR de release |
| 09 MIN | 64 tests backend jamais lancés en CI faute de `docling` | Installer `docling` en CI alourdit chaque run : arbitrage coût | 0.8.0 |
| 10-10.2.3 | Image `local` jamais construite ni scannée par le gate | Modifie le Release Gate et sa durée | 0.8.0 |
| 12-12.3.2 | Réponse de l'éditeur de 13,8 Mo à 300 pages | Demande de revoir le contrat de l'éditeur | 0.8.0 |
| 08 MIN | Pas de `max_length` sur les schémas de l'éditeur, import sans plafond de taille | Une limite trop basse casse des documents réels : à calibrer | 0.8.0 |

---

## 4. Effet attendu sur les notes

Estimation avant l'audit de contrôle, item par item. Les valeurs mesurées sont dans [control-audit.md](control-audit.md).

| Audit | Avant | Attendu | Hypothèse |
|-------|-------|---------|-----------|
| 01 | 78 | 78 à 84 | 1.2.4 ne passe que si tous les typages concrets sont levés |
| 03 | 56 | 61 | 3.1.1 conforme |
| 05 | 67 | 83 | 5.3 conforme |
| 06 | 87 | 94 à 100 | 6.2.1 conforme, 6.1.4 si le rendu PDF sort de `DocumentService` |
| 10 | 70 | 70 à 75 | 10.2.4 conforme ; 10.1.1 attend la CI |
| 12 | 86 | 95 | 12.2.5 et 12.3.1 conformes |
| Global | ≈ 80 | ≈ 83 | ≈ 87 après CI verte et freeze |
