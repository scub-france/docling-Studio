# Audit 03 — Clean Code

**Objectif** : verifier la lisibilite, la clarte et la maintenabilite du code.

**Cible** : `document-parser/` (hors `.venv/`, `__pycache__/`), `frontend/src/`

---

## Checklist

### 3.1 Nommage

| # | Item | Poids |
|---|------|-------|
| 3.1.1 | Les fonctions sont nommees avec des verbes d'action (`create_analysis`, `upload_document`) | 1 |
| 3.1.2 | Les variables expriment l'intention (`remaining_pages` et non `rp`) | 1 |
| 3.1.3 | Tout le code est en anglais — les traductions i18n sont dans `shared/i18n.ts` | 2 |
| 3.1.4 | Pas d'abbreviations ambigues sauf conventions etablies (`dto`, `bbox`, `id`, `url`) | 1 |

### 3.2 Fonctions

| # | Item | Poids |
|---|------|-------|
| 3.2.1 | Chaque fonction fait une seule chose (Single Responsibility) | 2 |
| 3.2.2 | Aucune fonction ne depasse 30 lignes (hors boilerplate inevitable) | 1 |
| 3.2.3 | Aucune fonction n'a plus de 4 parametres (hors constructeurs d'injection et signatures imposees par un framework, voir la precision ci-dessous) | 1 |
| 3.2.4 | Pas de flag arguments (booleen qui change le comportement) | 1 |
| 3.2.5 | Une fonction `get_*` ne modifie pas d'etat (pas de side-effects caches) | 2 |

**Precision sur 3.2.3** (2026-11-20, decision du mainteneur). Deux familles de signatures ne sont pas comptees, comme le « boilerplate inevitable » du 3.2.2 :

- les constructeurs qui ne font que recevoir leurs collaborateurs par injection (`__init__` des services et des adaptateurs) : les regrouper dans un objet ne retire aucune dependance et ajoute une indirection que l'audit 04 releverait ;
- les signatures dont les parametres sont le contrat public impose par un framework : fonctions de route FastAPI (parametres de chemin, de requete, corps, dependances `Depends`) et outils MCP (chaque parametre est un argument de l'outil).

Toute autre fonction reste soumise au seuil. Un constructeur qui depasse 7 collaborateurs reste a signaler en `[INFO]` : c'est un indice de service trop large (audit 06). Les rapports anterieurs a cette date comptaient ces signatures : leurs mesures de 3.2.3 ne sont pas comparables.

### 3.3 Fichiers et structure

| # | Item | Poids |
|---|------|-------|
| 3.3.1 | Aucun fichier source ne depasse 300 lignes | 1 |
| 3.3.2 | Un seul concept par fichier — pas de fichier fourre-tout | 2 |
| 3.3.3 | Imports ordonnes : stdlib, deps externes, imports internes | 1 |

### 3.4 Commentaires

| # | Item | Poids |
|---|------|-------|
| 3.4.1 | Le code est auto-documentant — les commentaires expliquent le "pourquoi", pas le "quoi" | 1 |
| 3.4.2 | Pas de code commente laisse en place (dead code) | 1 |

---

## Commandes de verification

```bash
# 3.3.1 — Fichiers Python > 300 lignes
find document-parser -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" -not -path "*/tests/*" | xargs wc -l | sort -rn | head -20

# 3.3.1 — Fichiers Vue/TS > 300 lignes
find frontend/src -name "*.vue" -o -name "*.ts" | xargs wc -l | sort -rn | head -20

# 3.2.3 — Fonctions avec > 4 parametres (Python)
grep -rn "def .*,.*,.*,.*,.*," document-parser --include="*.py" --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=tests

# 3.4.2 — Code commente
grep -rn "^[[:space:]]*#.*=\|^[[:space:]]*#.*def \|^[[:space:]]*#.*return\|^[[:space:]]*//.*=\|^[[:space:]]*//.*function" document-parser --include="*.py" --exclude-dir=.venv frontend/src --include="*.ts" --include="*.vue"
```

---

## Regles de notation

- Tout item de poids 3 non conforme = ecart `[CRIT]`
- Tout item de poids 2 non conforme = ecart `[MAJ]`
- Tout item de poids 1 non conforme = ecart `[MIN]`
