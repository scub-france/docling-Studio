# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 9 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 2 |

Ponderation : items conformes = 13 pts / 18 pts totaux → 72/100.
Items non conformes : 11.1.1 (poids 3), 11.2.1 (poids 2).

---

## Ecarts constates

### [CRIT] La section `[Unreleased]` n'a pas ete renommee en `[0.7.0] - 2026-08-24`

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : Le changelog porte encore l'en-tete `## [Unreleased]`. Aucune section `## [0.7.0] - 2026-08-24` n'existe. Le contenu de la release (Analyses workspace, Reasoning Trace v2 #303, backend trace projection #303, configuration runtime du reasoning #317, workflow simplifie, lean dev stack, retrait de la surface reasoning v1) est present et detaille sous `[Unreleased]`, mais la section n'a pas ete figee pour la release. Le changelog n'est donc pas finalise pour un tag `0.7.0`.
- **Regle violee** : Item 11.1.1 — « La section `[Unreleased]` a ete renommee en `[X.Y.Z] - YYYY-MM-DD` » (poids 3).
- **Remediation** : Renommer `## [Unreleased]` en `## [0.7.0] - 2026-08-24` (et, optionnellement, recreer une section `## [Unreleased]` vide au-dessus pour le cycle suivant).

### [MAJ] `frontend/package.json` reste en 0.6.2 au lieu de 0.7.0

- **Localisation** : `frontend/package.json:3`
- **Constat** : Le champ `"version"` vaut `"0.6.2"`. La release cible est `0.7.0` : la version front n'a pas ete bumpee. A noter que ce projet traite historiquement le bump de version front comme une entree de changelog explicite (cf. 0.6.1 : « Frontend package version bumped to 0.6.1 (#audit-11) »), renforcant le caractere volontaire et attendu de ce bump.
- **Regle violee** : Item 11.2.1 — « `frontend/package.json` contient la bonne version X.Y.Z » (poids 2).
- **Remediation** : Passer `"version": "0.6.2"` a `"version": "0.7.0"` dans `frontend/package.json` et ajouter l'entree de bump correspondante au changelog lors de la finalisation de la section 0.7.0.

### [INFO] Note de version obsolete dans le README

- **Localisation** : `README.md:309`
- **Constat** : La ligne indique « ... pagination ships in v0.6. » Cette note prospective est desormais perimee : la release courante est 0.7.0 et la note pointe vers une version deja depassee sans confirmer si la fonctionnalite (pagination du graphe > 200 pages) a effectivement ete livree.
- **Regle violee** : Hors checklist ponderee (README n'a pas d'item dedie) — observation de qualite documentaire.
- **Remediation** : Corriger la note (confirmer la version reelle de livraison de la pagination graphe, ou retirer la reference `v0.6`).

### [INFO] Section `BREAKING CHANGES` absente pour 0.7.0 — a arbitrer a la finalisation

- **Localisation** : `CHANGELOG.md:7-24`
- **Constat** : La section 0.7.0 ne comporte pas de sous-section `### BREAKING CHANGES`, contrairement a toutes les releases depuis 0.6.0. L'audit ne releve pas de rupture d'API/donnees dissimulee : le retrait de la surface reasoning v1 conserve `/reasoning` et `/reasoning/:docId` en redirects (documente sous « Removed »), la surface `/studio` reste presente et flag-gated (`STUDIO_MODE_ENABLED`, `frontend/src/app/router/routes.ts:24`), et `docling-agent==0.6.0` reste dans le groupe opt-in `reasoning` (`document-parser/pyproject.toml:44-51`). Deux points de vigilance meritent toutefois un arbitrage explicite avant tag : le changement de profil compose par defaut (« Lean development stack » — le stack par defaut ne demarre plus que frontend + parser, `ingestion`/`graph`/`remote` deviennent opt-in) et le comportement de detection au boot d'un agent inutilisable (mapping vers `502` sur resultat vide). Ces evolutions sont decrites sous « Changed » mais ne sont pas classees comme ruptures.
- **Regle violee** : Item 11.1.3 juge conforme (aucune rupture non identifiee) — note preventive.
- **Remediation** : Lors de la finalisation, statuer explicitement sur le changement de profil compose par defaut (impact workflow operateur) et ajouter une sous-section `### BREAKING CHANGES` si l'un de ces points est retenu comme rupture.

---

## Points positifs

- **Aucun TODO / FIXME / HACK / XXX** dans le code en perimetre (`document-parser/**/*.py` hors `.venv`/`tests`, `frontend/src/**/*.ts|*.vue`) — item 11.3.1 conforme.
- **Aucun `console.log` / `console.debug` de debug** dans le front : les seuls appels sont des `console.error` / `console.warn` en blocs `catch` (gestion d'erreur structuree), explicitement autorises par la convention (`frontend/CLAUDE.md` — « no-console en warn (warn/error autorises) ») — item 11.3.2 conforme.
- **Aucun `print()` de debug** cote backend : les 3 occurrences de `print(` (`document-parser/infra/settings.py:43`, `document-parser/infra/secrets/fernet_box.py:46` et `:133`) sont a l'interieur de docstrings / messages d'exception documentant la commande de generation de cle Fernet, pas des instructions executables (le grep `^\s*print(` de la checklist ne les capture pas) — item 11.3.3 conforme.
- **Contenu de release complet et detaille** : la section 0.7.0 liste toutes les modifications significatives (Added/Changed/Removed) avec references d'issues (#303, #317) et notes de comportement precises — item 11.1.2 conforme.
- **Format Keep a Changelog respecte** : en-tete referencant Keep a Changelog + SemVer, groupes standards (Added/Changed/Removed/Fixed/Security), dates `YYYY-MM-DD`, versionnage decroissant — item 11.1.4 conforme.
- **README a jour sur les nouveautes 0.7.0** : la section Reasoning documente explicitement le comportement runtime introduit en 0.7.0 (`README.md:331` — « Since 0.7.0 ... »).
- **Versionnage SemVer coherent** : le schema de version suit MAJOR.MINOR.PATCH ; 0.6.2 → 0.7.0 est un bump mineur correct (ajouts retro-compatibles) — item 11.2.2 conforme.

---

## Verdict partiel : NO-GO

Un ecart `[CRIT]` non resolu (item 11.1.1 — changelog non fige pour 0.7.0) declenche la regle absolue du master : **NO-GO** quel que soit le score. Le score de 72/100 (zone GO CONDITIONNEL) ne s'applique donc pas. Debloquants : renommer la section changelog en `## [0.7.0] - 2026-08-24` (CRIT) et bumper `frontend/package.json` a `0.7.0` (MAJ), puis re-auditer.
