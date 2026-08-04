# Ask demo — narration & actions, shot par shot

Vue lisible de ce que la caméra fait pendant que la voix parle. Trois sources, réunies ici :

| Colonne | Source | Autorité |
|---|---|---|
| Texte | `scripts/demo/narration.json` | **la source** — édite là, jamais ici |
| Action | `e2e/ui/src/test/resources/demo/ask-demo.feature` | **la source** |
| Durée | `e2e/ui/src/test/resources/demo/pace.json` (écrit par `render-narration.sh`) | mesuré sur l'audio rendu |

**Ce fichier est une lecture, pas un pilote.** Rien ne le lit à l'exécution. Modifier une phrase
ici ne change ni la voix ni le montage — il faut passer par `narration.json` puis
`render-narration.sh`. À re-générer si les deux sources divergent.

⚠️ **Les durées ci-dessous sont périmées.** Elles viennent du `pace.json` du 15/07, mesuré sur
l'ancien texte. La narration a été réécrite (registre parlé) et l'intro ajoutée : il faut relancer
`render-narration.sh` pour connaître les vraies. Le total va monter d'environ 25 s.

Total des holds (ancien texte) : **187,0 s ≈ 3:07**, constant quelle que soit la lenteur d'Ollama
(les deux attentes sont coupées à 6 s en post). Les timecodes ci-dessous sont indicatifs : le
placement réel est calculé par `assemble.py` à partir des epochs de `timing.json`.

---

## Shot 0a — Bienvenue + contexte · 0:00 · _à mesurer_

**Action** — **aucune**. Plan fixe sur la vue Parse déjà chargée.

> Hey everybody, and welcome to this quick introduction to Docling Studio. First, some context. Docling Studio is an open source product, and it's built on the Docling project, from IBM Research. Docling is the part that reads your PDF and gives you back a real structure. Studio doesn't rebuild any of that.

⚠️ **« from IBM Research »** = l'équipe DS4SD (cf. le lien `DS4SD/docling` du README). Le projet a
été **donné à la Linux Foundation AI & Data en 2025** : l'origine reste IBM, la gouvernance non.
À vérifier avant publication si tu veux la ligne exacte.

---

## Shot 0b — Ce que fait Studio · _à mesurer_

**Action** — **aucune**. Toujours le même plan fixe.

> So what does Studio do? Two things. The first one is the whole point: it shows you what Docling found, clearly, and in a way you can trust — and where it needs a fix, you can fix it, right there. So it's a tool for looking at your documents, and for cleaning them up. And the second thing, the newer one, is what we're going to look at today: the agentic side. That's Docling Agent, and that's where it gets interesting.

⚠️ **« you can fix it » ne vaut que pour les chunks.** Le seul texte éditable est celui des chunks :
`PATCH /{doc_id}/chunks/{chunk_id}` (`document_chunks.py:94`), la textarea de `ChunkPanel.vue` et
celle d'`ElementProperties.vue` quand un chunk est sélectionné. Les nœuds parsés (titres,
paragraphes, tables) sont **en lecture seule** — aucune route `PUT`/`PATCH` ne les touche. D'où la
formulation vague : dire « correct the extraction » promettrait un éditeur qui n'existe pas.

ℹ️ **Docling Serve n'est plus nommé** dans l'intro : cette prise tourne en `engine: local`
(`/api/health`), le mode remote existe (`docker-compose.yml`, image `docling-serve-cpu:v1.21.0`)
mais n'est pas à l'écran, et il n'apporte rien au propos. À rajouter seulement si tu filmes ce mode.

🔴 **Ouverture statique : ~40 s.** 0a + 0b + shot 1 = **trois** holds sur la même image immobile.
C'est le défaut exact qui a fait fusionner les shots 5 et 6 (« 43 s de picture morte »). Le remède
est déjà écrit dans l'ancien script : `303-ask-demo-script.md` shot 1 dit *« Slowly scroll the tree
once »* — et le feature ne l'a jamais fait. Faire scroller le tree sous l'intro réglerait les deux
problèmes d'un coup.

---

## Shot 1 — Le document parsé · _à mesurer_

**Action** — `driver` sur `/docs/<docId>`, attend `parse-tab`, `tree-rail`, `preview-with-overlay`. Rien d'autre : plan fixe.

> So here's a PDF we've already parsed. And what comes back isn't a wall of text. It's a tree. Every title, every paragraph, every table, every figure is a node. And each one knows where it sits on the page.

---

## Shot 2a — La structure est adressable · 13,3 s

**Action** — clic sur la **première** ligne du tree (`.tree-node-row`), attend que `element-properties-empty` disparaisse puis que `element-properties` soit là. Le bbox se surligne dans le PDF.

> Click a node, and the preview shows you exactly where it came from. And on the right, that's what Docling actually pulled out: the node's own reference, its type, the page, and its box.

---

## Shot 2b — La self-reference · 8,2 s

**Action** — **aucune**, sauf si `BBOX_POINT="x,y"` est passé : dans ce cas seulement, clic aux coordonnées sur le canvas → le tree s'ouvre sur le nœud. Par défaut le beat est sauté (log : `demoBboxPoint unset — canvas-click beat skipped`) et le plan est fixe.

> Keep an eye on that reference — the one starting with hash, slash, texts. It's about to do a lot of work.

⚠️ Les bboxes sont peintes sur un `<canvas>` (`BboxCanvas.vue`) : aucun nœud DOM, donc aucun sélecteur ne peut les cliquer. Voir « The canvas caveat » dans `scripts/demo/README.md`.

---

## Shot 3 — Le panneau Ask apparaît · 0:35 · 9,7 s

**Action** — clic sur `ask-tab`, attend `ask-panel` et `trace-panel`. C'est ce clic qui fait apparaître le dock de trace et rétrécir le preview : **le layout shift est le plan**.

> Now the Ask tab. Two things just showed up. A box to type in, on the right. And an empty timeline, under the page. That timeline is what this whole thing is about.

---

## Shot 4a — La question · 0:45 · 2,2 s

**Action** — saisie de `q1` dans `ask-composer-input`. Puis clic sur `ask-run-btn`.

> So let's ask it something.

**q1** = `-DdemoQ1` / `DEMO_Q1`, défaut : `What datasets were used to evaluate the model, and how large are they?`

---

## Shot 4b — Le chunkless RAG, par-dessus l'attente · 0:47 · 16,1 s

**Action** — `retry(60, 1000)` sur `ask-turn-card` **et** sur `trace-row`. Le clip parle pendant le run (20–40 s). On ne tient ensuite que le reste : `rem4 = pace['4b'] − min(elapsed, 6000)`.

> Now, Studio doesn't do retrieval. Not one line of it. We hand the parsed document to Docling Agent, and let it do the work. And it doesn't work the way you'd expect. There's no chunking here. No embeddings. No vector database.

---

## Shot 5a — La timeline · 1:03 · 8,0 s

**Action** — attend `trace-stats` et `trace-model-chip`, compte les lignes, logue `trace rows: N | per-step timing degraded: …`. Plan fixe sur la réponse + la timeline.

> There's your answer. But look underneath. That's every step it took, in order. That's the loop it just ran.

---

## Shot 5b — Un passage = une ligne · 1:11 · 14,0 s

**Action** — clic sur la **première** `trace-row` → `focusElement(citations[0])` : le PDF saute et se surligne, le tree s'ouvre.

> Each row is one pass. It never read the whole paper. It saw an outline — just the headings — and it picked one section. And that title you're reading? That's the model's own reason for picking it. Then it read that section. Only that one.

---

## Shot 5c — Les lignes atténuées · 1:25 · 15,9 s

**Action** — clic sur la **dernière** `trace-row` (celle où il a répondu). Indexée via `locateAll(...)[rowCount − 1]`.

> Then it asked itself: can I answer now? The dim rows are where it said no, and went back for another section. The bright one is where it said yes. Five passes, that's the limit. So it moves through the document, the way you would.

🔴 **Ce texte exige ≥ 2 lignes.** À 1 ligne, `lastIdx = 0` : on re-clique la première, il n'y a ni ligne atténuée ni ligne brillante, et la phrase ment.

---

## Shot 5d — Le lien est vivant · 1:41 · 20,4 s

**Action** — **re-clic sur la même ligne** : `focusTick` s'incrémente, donc ça re-scrolle même déjà focus (délibéré, cf. `document/store.ts`). C'est le beat qui prouve que le lien n'est pas one-shot.

> And here's the part I really care about. That chip is a reference into the same tree you're looking at. So the page jumps to what it read, and the tree opens right to it. Every claim in here points at a real spot, on a real page. That's the difference between a model telling you it read something, and showing you.

⚠️ **Pas de « Properties fills in » ici** : `ElementProperties` et `ConversationPanel` sont en `v-if` sur le même `rightTab`, dans la même colonne de 360 px (`DocParseTab.vue:107-140`). Ask ouvert ⇒ Properties **absent du DOM**. Les surfaces visibles sont le PDF et le tree — deux, pas trois.

---

## Shot 5e — Les stats et le caveat · 2:02 · 16,7 s

**Action** — aucune, plan fixe sur l'en-tête (`trace-stats`, `trace-model-chip`) et la footnote.

> Up top: how many steps, how long it took, and the model — Granite 4.1 3B, running locally, through Ollama. And one honest note. The per-step timings aren't in the released library yet. So those bars show order, not duration. The total is real.

---

## Shot 7a — Deuxième question · 2:18 · 4,7 s

**Action** — `clear` puis saisie de `q2` dans `ask-composer-input`, clic sur `ask-run-btn`.

> One more. Something harder — something that isn't sitting in the abstract.

**q2** = `-DdemoQ2` / `DEMO_Q2`, défaut : `What are the stated limitations of this approach?`

---

## Shot 7b — La chasse · 2:23 · 13,6 s

**Action** — `retry(60, 1000).waitForResultCount('[data-e2e=ask-turn-card]', 2)`, puis `rem7 = pace['7b'] − min(elapsed, 6000)`.

> Same loop. But this time, the answer isn't where it looks first. So it has to go hunting. And watch the reasons when it comes back: it guessed, it read, it admitted that wasn't enough, and it tried somewhere else.

🔴 **Cette attente ne tient pas.** `ask-turn-card` n°2 existe dès la soumission, avant la réponse : sur la prise du 16/07 elle a rendu la main en **6 ms** (marks 71 → 72). Le clip ne tient donc que par la longueur du voiceover, pas par l'état réel du run. À 40 s de latence, le clic du 7c tombe sur la trace **périmée de la Q1** (`activeTrace` reste celle du tour précédent). La Q1 attend correctement, elle — sur `trace-row`.

---

## Shot 7c — Les impasses · 2:37 · 8,8 s

**Action** — clic sur `trace-row` (la première).

> That's not it failing. That's the loop working — and it's all on the record. Every dead end it walked down is right there, and you can click into each one.

🔴 Même dépendance que 5c : « every dead end » n'existe qu'avec ≥ 2 lignes.

---

## Shot 8 — Clôture · 2:45 · 21,6 s

**Action** — clic sur `props-tab`, attend `element-properties`. Retour sur la vue Parse complète.

> So: Docling parses the document. Docling Agent reasons over it. And Studio makes that reasoning something you can see, and click. And that trace we've been reading — run with trace — is something we contributed back upstream. It shipped in Docling Agent 0.6.0. So if you're building on the library, it's already there for you.

---

## Ce que la prise du 16/07 a donné

`out/demo/timing.json` : `traceRowsQ1: 1`, `traceRowsQ2: 1`, `degradedTiming: true`.

Une seule ligne sur chaque question ⇒ **5c, 5d et 7c ne décrivent pas ce qui est à l'écran**, et
le shot 5 clique trois fois la même ligne. Karate l'a signalé pendant le run :

```
WARNING: converged in one pass — a single-row timeline makes for a poor demo.
```

Le `DEMO_Q1` passé (`What datasets were used to evaluate the model?`) était le défaut du feature
**amputé de `and how large are they?`** — justement la part qui force l'agent à sortir de
l'abstract. À reprendre avant tout montage.

## À faire avant la prochaine prise

- [ ] Choisir deux questions dont la réponse est enfouie loin de l'abstract (lire les en-têtes du PDF cible plutôt que deviner).
- [ ] Réparer l'attente du shot 7b — s'aligner sur la Q1, attendre un état qui prouve que le **nouveau** run est fini.
- [ ] Optionnel : trouver `BBOX_POINT` sur une capture à la géométrie fixe 1440×900 pour activer le beat canvas du 2b.
