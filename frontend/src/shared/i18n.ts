import type { Locale } from './types'
import { appLocale } from './appConfig'

type MessageMap = Record<string, string>
type Messages = Record<Locale, MessageMap>

const messages: Messages = {
  fr: {
    // Sidebar — 0.6.0 doc-centric nav (#209)
    'nav.home': 'Accueil',
    'nav.docs': 'Documents',
    'nav.stores': 'Stores',
    'nav.runs': 'Runs',
    'nav.settings': 'Paramètres',
    'nav.collapse': 'Réduire la barre latérale',
    'nav.expand': 'Développer la barre latérale',
    // Legacy nav labels — kept because the legacy pages (/studio, /documents,
    // /history, /search, /reasoning) still render headings using them. They
    // are no longer surfaced in the sidebar.
    'nav.studio': 'Studio',
    'nav.documents': 'Documents',
    'nav.history': 'Historique',
    'nav.reasoning': 'Raisonnement',
    'nav.search': 'Recherche',

    // Top bar
    'topbar.newAnalysis': 'Nouvelle analyse',

    // Breadcrumb (0.6.0 doc workspace — #208)
    'breadcrumb.aria': "Fil d'Ariane",
    'breadcrumb.studio': 'Studio',
    'breadcrumb.mode.ask': 'Ask',
    'breadcrumb.mode.inspect': 'Inspect',
    'breadcrumb.mode.chunks': 'Chunks',

    // Feature flags (0.6.0 — #210)
    'flags.allModesDisabled':
      "Aucun mode (Ask / Inspect / Chunks) n'est activé pour ce déploiement. Contactez votre administrateur.",

    // Lifecycle status badges (#215)
    'status.Uploaded': 'Uploadé',
    'status.Parsed': 'Parsé',
    'status.Chunked': 'Chunké',
    'status.Ingested': 'Ingéré',
    'status.Stale': 'Obsolète',
    'status.Failed': 'Échoué',
    'status.tooltip.Uploaded': 'Fichier reçu, en attente de parsing.',
    'status.tooltip.Parsed': 'Document parsé avec succès.',
    'status.tooltip.Chunked': 'Chunks générés, prêts à être ingérés dans un store.',
    'status.tooltip.Ingested': 'Ingéré dans au moins un store.',
    'status.tooltip.Stale': 'Chunks modifiés depuis la dernière ingestion — ré-ingestion requise.',
    'status.tooltip.Failed': 'Une étape du pipeline a échoué. Réessayez.',

    // Document library (#211, #212, #213)
    'docs.title': 'Documents',
    'docs.import': 'Importer',
    'docs.emptyTitle': 'Aucun document',
    'docs.emptySubtitle': 'Importez votre premier document pour commencer.',
    'docs.emptyAction': 'Importer un document',
    'docs.emptyFiltered': 'Aucun document ne correspond aux filtres.',
    'docs.colName': 'Nom',
    'docs.colStatus': 'État',
    'docs.colStores': 'Stores',
    'docs.colUpdated': 'Mis à jour',
    'docs.filterSearch': 'Rechercher…',
    'docs.filterClear': 'Effacer les filtres',
    'docs.selected': '{n} sélectionné(s)',
    'docs.bulkRechunk': 'Re-chunker',
    'docs.bulkPush': 'Ingérer dans un store…',
    'docs.bulkDelete': 'Supprimer',
    'docs.bulkCancel': 'Annuler la sélection',
    'docs.deleteConfirm': 'Supprimer {n} document(s) ? Cette action est irréversible.',
    'docs.pushTitle': 'Ingérer dans un store',
    'docs.pushLabel': 'Store cible',
    'docs.pushPlaceholder': 'Nom du store…',
    'docs.pushSubmit': 'Ingérer',
    'docs.pushCancel': 'Annuler',
    'docs.jobDispatched': 'Job lancé ({jobId})',

    // Doc import (#214)
    'docsNew.title': 'Importer des documents',
    'docsNew.drop': 'Déposez des PDFs ici ou cliquez pour choisir',
    'docsNew.dropHint': 'Plusieurs fichiers acceptés · PDF uniquement',
    'docsNew.queued': 'En attente',
    'docsNew.uploading': 'Import…',
    'docsNew.done': 'Importé',
    'docsNew.failed': 'Échec',
    'docsNew.viewDoc': 'Voir le document',
    'docsNew.backToLibrary': 'Retour à la bibliothèque',
    'docsNew.viewLibrary': 'Voir la bibliothèque',
    'docsNew.allDone': 'Tous les fichiers ont été importés.',

    // Coming-soon placeholders (0.6.0 doc-centric routes — #207)
    'comingSoon.title': 'Bientôt disponible',
    'comingSoon.subtitle.docsLibrary':
      "La bibliothèque de documents arrive avec la 0.6.0. Vous y verrez l'état du cycle de vie de chaque document, ses stores et ses dernières mises à jour.",
    'comingSoon.subtitle.docsNew':
      "L'import multi-fichiers (drop d'un dossier ou sélection multiple) arrive avec la 0.6.0.",
    'comingSoon.subtitle.docWorkspace':
      "L'espace de travail document (Inspect / Chunks / Ask) arrive avec la 0.6.0.",
    'comingSoon.subtitle.stores': 'La liste des stores arrive avec la 0.6.0.',
    'comingSoon.subtitle.storeDetail':
      'La vue détaillée du store (documents présents, état par store) arrive avec la 0.6.0.',
    'comingSoon.subtitle.storeQuery': 'Le playground de requête RAG arrive avec la 0.6.0.',
    'comingSoon.subtitle.runs': "L'historique des runs (audit / debug) arrive avec la 0.6.0.",
    'comingSoon.subtitle.runDetail': "Le détail d'un run arrive avec la 0.6.0.",
    'comingSoon.hint.docWorkspace': 'doc {id} · mode {mode}',
    'comingSoon.hint.storeDetail': 'store {store}',
    'comingSoon.hint.storeQuery': 'store {store}',
    'comingSoon.hint.runDetail': 'run {id}',
    'comingSoon.backHome': "Retour à l'accueil",

    // Home
    'home.title': 'Docling Studio',
    'home.subtitle':
      'Analysez, explorez et validez la structure de vos documents PDF grâce à Docling.',
    'home.documents': 'Documents',
    'home.analyses': 'Analyses',
    'home.recentDocs': 'Documents récents',

    // Studio — import
    'studio.title': 'Intelligence des documents',
    'studio.subtitle': "Importez un document PDF pour commencer l'analyse avec Docling",
    'studio.recentDocs': 'Documents récents',

    // Studio — workspace
    'studio.configure': 'Configurer',
    'studio.verify': 'Vérifier',
    'studio.addFiles': 'Ajouter des fichiers',
    'studio.analyzing': 'Analyse...',
    'studio.run': 'Exécuter',
    'studio.loaded': 'Chargé',
    'studio.analysisRunning': 'Analyse en cours...',
    'studio.failed': 'Échec',
    'studio.visual': 'Visuel',

    // Config panel
    'config.model': 'Modèle',
    'config.pipeline': 'Pipeline',
    'config.ocr': 'OCR',
    'config.ocrHint':
      'Applique la reconnaissance optique de caractères sur les pages scannées ou les images intégrées. Indispensable pour les PDF non-natifs.',
    'config.tableStructure': 'Extraction des tableaux',
    'config.tableStructureHint':
      'Détecte les tableaux dans le document et reconstruit leur structure lignes/colonnes via le modèle TableFormer, avec correspondance des cellules.',
    'config.tableMode': 'Mode tableaux',
    'config.tableModeAccurate': 'Précis',
    'config.tableModeFast': 'Rapide',
    'config.enrichment': 'Enrichissement',
    'config.codeEnrichment': 'Code',
    'config.codeEnrichmentHint':
      "Active un modèle OCR spécialisé pour les blocs de code, préservant l'indentation et la syntaxe.",
    'config.formulaEnrichment': 'Formules',
    'config.formulaEnrichmentHint':
      'Reconnaît les formules mathématiques et les convertit en LaTeX via un modèle dédié.',
    'config.pictures': 'Images',
    'config.pictureClassification': 'Classification',
    'config.pictureClassificationHint':
      'Classe chaque image détectée par type (graphique, photo, diagramme, logo…) via un modèle de classification.',
    'config.pictureDescription': 'Description',
    'config.pictureDescriptionHint':
      "Génère une description textuelle de chaque image via un Vision Language Model (VLM). Utile pour l'accessibilité et l'indexation.",
    'config.generatePictureImages': 'Extraire les images',
    'config.generatePictureImagesHint':
      "Extrait les images détectées du document et les sauvegarde en tant que fichiers séparés. Nécessaire pour l'export d'images.",
    'config.generatePageImages': 'Images de pages',
    'config.generatePageImagesHint':
      'Rasterise chaque page du PDF en image. Utile pour la visualisation ou le post-traitement visuel.',
    'config.imagesScale': 'Échelle images',
    'config.documents': 'Documents',

    // Results
    'results.elements': 'Éléments',
    'results.markdown': 'Markdown',
    'results.images': 'Images',
    'results.graph': 'Graphe',
    'results.graphLoading': 'Chargement du graphe…',
    'results.graphEmpty': 'Pas encore de graphe pour ce document (activez Neo4j).',
    // GraphView — node details panel & interactions
    'graph.nodeDetails': 'Détails du nœud',
    'graph.close': 'Fermer',
    'graph.page': 'Page',
    'graph.text': 'Texte',
    'graph.provenances': 'Provenances ({n})',
    'graph.contains': 'Contenu ({n})',
    'results.retry': 'Réessayer',
    'results.pageOf': 'Page {current} sur {total}',
    'results.noElements': 'Aucun élément détecté sur cette page',
    'results.noImages': 'Aucune image détectée dans ce document',
    'results.noMarkdown': 'Pas de contenu markdown',
    'results.runAnalysis': 'Lancez une analyse pour voir les résultats',
    'results.analysisFailed': "L'analyse a échoué",
    'results.copy': 'Copier',
    'results.copied': 'Copié !',
    'results.page': 'Page',

    // Upload
    'upload.drop': 'Déposez un PDF ici ou cliquez pour importer',
    'upload.uploading': 'Import en cours...',
    'upload.maxSize': 'Max {n}Mo',
    'upload.invalidFormat': 'Format invalide — seuls les fichiers PDF sont acceptés.',
    'upload.tooLarge': 'Fichier trop volumineux (max {n} Mo).',
    'upload.maxPages': 'Max {n} pages',

    // History
    'history.title': 'Historique',
    'history.tabAnalyses': 'Analyses',
    'history.tabDocuments': 'Documents',
    'history.empty': 'Aucune analyse. Allez dans Studio pour analyser votre premier document.',
    'history.emptyDocs': 'Aucun document. Importez un document depuis le Studio.',
    'history.open': 'Ouvrir',

    // Chunking
    'studio.prepare': 'Préparer',
    'studio.ingest': 'Ingérer',
    'studio.maintain': 'Maintenir',
    // Reasoning trace (R&D v1 — overlays a docling-agent ReasoningResult on the graph)
    'reasoning.importBtn': 'Importer une trace de raisonnement',
    'reasoning.importTitle': 'Importer une trace de raisonnement',
    'reasoning.importHint':
      'Dépose un JSON de trace de raisonnement produit par docling-agent (ou par le script R&D experiments/reasoning-trace).',
    'reasoning.drop': 'Glisse un fichier .json ici',
    'reasoning.dropSub': 'ou clique pour le choisir',
    'reasoning.parsing': 'Analyse du fichier...',
    'reasoning.pasteToggle': 'Coller le JSON à la place',
    'reasoning.pastePlaceholder': "Colle ici le contenu JSON d'une trace de raisonnement...",
    'reasoning.pasteSubmit': 'Charger',
    'reasoning.close': 'Fermer',
    'reasoning.errJson': 'JSON invalide : {msg}',
    'reasoning.errShape':
      "Le fichier n'a pas la forme d'une trace de raisonnement (answer, converged, iterations).",
    'reasoning.panelTitle': 'Trace de raisonnement',
    'reasoning.focus': 'Focus',
    'reasoning.focusHint':
      'Atténuer les éléments non visités pour faire ressortir le chemin de raisonnement.',
    'reasoning.reimport': 'Réimporter',
    'reasoning.clear': 'Effacer',
    'reasoning.query': 'Question',
    'reasoning.converged': 'Convergé',
    'reasoning.notConverged': 'Itérations max atteintes',
    'reasoning.resolved': 'sections résolues',
    'reasoning.answerLabel': 'Réponse',
    'reasoning.copy': 'Copier',
    'reasoning.copied': 'Copié ✓',
    'reasoning.copyAnswer': 'Copier la réponse dans le presse-papier',
    'reasoning.reasonPlaceholder': '— pas de justification structurée',
    'reasoning.missingWarn':
      '{n} section(s) introuvable(s) dans le graphe. Le document a peut-être été re-analysé — relance « Maintenir » ou régénère la trace.',
    'reasoning.graphNotLoadedWarn':
      'Le graphe Neo4j de ce document n\u2019est pas chargé — les itérations sont affichées mais ne peuvent pas être positionnées sur la structure. Lance « prime_neo4j » ou re-déclenche une analyse.',
    'reasoning.iterationsTitle': 'Itérations',
    'reasoning.noIterations': "L'agent n'a visité aucune section (document sans en-têtes ?).",
    'reasoning.statusAnswered': 'Répondu',
    'reasoning.statusMore': 'Continue',
    'reasoning.statusMissing': 'Absent',
    'reasoning.charsLabel': '{n} caractères',
    // Reasoning page (standalone tunnel)
    'reasoning.pageTitle': 'Reasoning Trace',
    'reasoning.pageSubtitle':
      'Importe un PDF, puis dépose une trace de raisonnement produite par docling-agent pour visualiser le chemin de raisonnement sur le graphe du document.',
    'reasoning.dropPdf': 'Dépose un PDF',
    'reasoning.dropPdfHint': 'ou clique pour en choisir un',
    'reasoning.uploading': 'Import du document...',
    'reasoning.existingDocs': 'Documents déjà analysés',
    'reasoning.noAnalyzedDocs':
      'Aucun des documents existants n\u2019a encore été analysé — lance-en un depuis Studio, ou dépose un nouveau PDF ci-dessus.',
    'reasoning.pagesCount': '{n} pages',
    'reasoning.changeDoc': 'Changer de document',
    'reasoning.modeSwitchLabel': 'Mode d\u2019affichage',
    'reasoning.modeGraph': 'Graphe',
    'reasoning.modeDocument': 'Document',
    'reasoning.docNoContent': 'Aucun contenu rendu disponible pour ce document.',
    'reasoning.analyzing': 'Analyse du document...',
    'reasoning.analyzingHint':
      'Docling analyse le PDF avec la configuration par défaut. Cela peut prendre 1 à 3 minutes selon la taille.',
    'reasoning.runBtn': 'Lancer le reasoning',
    'reasoning.runTitle': 'Lancer docling-agent',
    'reasoning.runHint':
      'Pose une question au document. Le backend appelle docling-agent via Ollama et renvoie la trace dès que la boucle converge (20-40s).',
    'reasoning.runQueryLabel': 'Question',
    'reasoning.runQueryPlaceholder': 'Ex : Quelles sont les obligations du fournisseur ?',
    'reasoning.runModelLabel': 'Modèle (optionnel)',
    'reasoning.runModelPlaceholder': 'gpt-oss:20b',
    'reasoning.runModelSub':
      'Nom du modèle Ollama. Laisser vide pour utiliser le défaut serveur (REASONING_MODEL_ID).',
    'reasoning.runSubmit': 'Lancer',
    'reasoning.running': 'docling-agent tourne... (20-40s)',
    'reasoning.runErrUnknown': 'Erreur inconnue lors de l\u2019appel à docling-agent.',
    'reasoning.cancel': 'Annuler',
    'reasoning.retry': 'Réessayer',
    'reasoning.pickAnother': 'Choisir un autre document',
    'reasoning.prepError': 'Préparation impossible',
    'reasoning.prepErrAnalysis': "L'analyse Docling a échoué ou n'a pas produit de document_json.",
    'reasoning.prepErrTimeout': "L'analyse prend trop de temps — réessaye plus tard.",
    'reasoning.prepErrUnknown': 'Erreur inconnue.',
    'chunking.settings': 'Chunking',
    'chunking.chunkerType': 'Type de chunker',
    'chunking.maxTokens': 'Tokens max',
    'chunking.mergePeers': 'Fusionner les pairs',
    'chunking.repeatTableHeader': 'Répéter en-têtes tableaux',
    'chunking.run': 'Chunker',
    'chunking.chunking': 'Chunking...',
    'chunking.chunks': 'chunks',
    'chunking.noChunks': 'Lancez le chunking pour préparer les segments.',
    'chunking.noChunksOnPage': 'Aucun chunk sur cette page.',
    'chunking.edit': 'Modifier',
    'chunking.save': 'Enregistrer',
    'chunking.saving': 'Enregistrement...',
    'chunking.cancel': 'Annuler',
    'chunking.modified': 'modifié',
    'chunking.delete': 'Supprimer',
    'chunking.deleting': 'Suppression...',
    'chunking.deleteConfirm':
      'Supprimer ce chunk ? Il sera marqué comme supprimé jusqu\u2019à la prochaine synchronisation.',
    'chunking.batchNotice':
      'Le chunking n\u2019est pas disponible pour cette analyse. Les documents volumineux trait\u00e9s par batch ne g\u00e9n\u00e8rent pas la structure interne n\u00e9cessaire au d\u00e9coupage. Coming soon !',

    // Search (legacy nav label moved to the top with the other legacy keys)
    'search.hint': 'Saisissez un terme pour rechercher dans les chunks ingérés.',

    // Ingestion / My Documents
    'ingestion.ingest': 'Ingérer',
    'ingestion.document': 'Document',
    'ingestion.chunkCount': 'Chunks prêts',
    'ingestion.successMessage': 'Ingestion terminée avec succès !',
    'ingestion.ingesting': 'Ingestion...',
    'ingestion.reindex': 'Ré-ingérer',
    'ingestion.indexed': 'Ingéré',
    'ingestion.notIndexed': 'Non ingéré',
    'ingestion.chunksIndexed': '{n} chunks ingérés',
    'ingestion.openInStudio': 'Ouvrir dans le Studio',
    'ingestion.deleteIndex': 'Retirer du store',
    'ingestion.deleteConfirm':
      'Retirer ce document de l\u2019index ? Les chunks seront supprimés mais le document source restera.',
    'ingestion.unavailable': 'Ingestion non disponible',
    'ingestion.filterAll': 'Tous',
    'ingestion.filterIndexed': 'Ingérés',
    'ingestion.filterNotIndexed': 'Non ingérés',
    'ingestion.sortName': 'Nom',
    'ingestion.sortDate': 'Date',
    'ingestion.search': 'Rechercher...',
    'ingestion.searchChunks': 'Rechercher dans les chunks…',
    'ingestion.noResults': 'Aucun résultat pour « {q} ».',
    'ingestion.stepEmbedding': 'Embedding…',
    'ingestion.stepIndexing': 'Ingestion…',
    'ingestion.stepDone': 'Terminé',
    'ingestion.opensearchConnected': 'OpenSearch connecté',
    'ingestion.opensearchDisconnected': 'OpenSearch déconnecté',

    // Pagination
    'pagination.pageOf': 'Page {current} sur {total}',
    'pagination.perPage': '/ page',

    // Settings
    'settings.title': 'Paramètres',
    'settings.version': 'Version',
    'settings.theme': 'Thème',
    'settings.themeDark': 'Sombre',
    'settings.themeLight': 'Clair',
    'settings.language': 'Langue',
    'settings.about': '\u00C0 propos',
    'settings.designArticle': 'Comment Docling Studio a \u00e9t\u00e9 con\u00e7u',

    // Inspect tab (#240, #241)
    'inspect.tabMarkdown': 'Markdown',
    'inspect.tabElements': '\u00c9l\u00e9ments',
    'inspect.tabImages': 'Images',
    'inspect.noAnalysis': 'Aucune analyse disponible',
    'inspect.noAnalysisSub': 'Analysez ce document dans le Studio pour voir sa structure.',
    'inspect.goToStudio': 'Aller dans le Studio',
    'inspect.retry': 'R\u00e9essayer',
    'inspect.noElements':
      'Aucun \u00e9l\u00e9ment \u2014 lancez une analyse pour g\u00e9n\u00e9rer la structure.',

    // Ask tab (#242)
    'ask.questionLabel': 'Question',
    'ask.questionPlaceholder': 'Ex\u00a0: Quelles sont les obligations du fournisseur\u00a0?',
    'ask.modelConfig': 'Mod\u00e8le (optionnel)',
    'ask.modelPlaceholder': 'gpt-oss:20b',
    'ask.modelHint': 'Mod\u00e8le Ollama. Laisser vide pour le d\u00e9faut serveur.',
    'ask.run': 'Lancer',
    'ask.running': 'Reasoning en cours\u2026',
    'ask.answerLabel': 'R\u00e9ponse',
    'ask.noAnalysis': 'Aucune analyse disponible',
    'ask.noAnalysisSub': 'Analysez ce document dans le Studio avant de poser une question.',

    // Doc workspace (#216, #218)
    'workspace.tabs.ask': 'Ask',
    'workspace.tabs.inspect': 'Inspect',
    'workspace.tabs.chunks': 'Chunks',
    'workspace.backToLibrary': 'Retour \u00e0 la biblioth\u00e8que',
    'workspace.modeDisabled': 'Mode d\u00e9sactiv\u00e9 pour ce d\u00e9ploiement',
    'workspace.inspectComingSoon': 'Inspect \u2014 disponible en 0.7.0',
    'workspace.inspectComingSoonHint': 'La vue arborescence + bbox arrive prochainement.',
    'workspace.askComingSoon': 'Ask \u2014 disponible en 0.7.0',
    'workspace.askComingSoonHint':
      'Le raisonnement agentique sur le document arrive prochainement.',

    // Doc tree rail (#217)
    'tree.empty': "Aucun n\u0153ud dans l'arbre.",
    'tree.expand': 'D\u00e9velopper',
    'tree.collapse': 'R\u00e9duire',

    // Chunks editor (#219, #220, #221, #222)
    'chunks.count': '{n} chunk(s)',
    'chunks.empty': "Aucun chunk \u2014 parsez le document d'abord.",
    'chunks.saving': 'Sauvegarde\u2026',
    'chunks.noTitle': '(sans titre)',
    'chunks.editPlaceholder': 'Texte du chunk\u2026',
    'chunks.mergePrev': 'Fusionner avec le pr\u00e9c\u00e9dent',
    'chunks.mergeNext': 'Fusionner avec le suivant',
    'chunks.split': 'Scinder au curseur',
    'chunks.drop': 'Supprimer',
    'chunks.add': 'Ajouter un chunk',
    'chunks.retitle': 'Renommer',
    'chunks.diffToggle': 'Afficher le diff',
    'chunks.diffClose': 'Fermer le diff',
    'chunks.diffRef': 'R\u00e9f\u00e9rence',
    'chunks.diffAdded': 'ajout\u00e9(s)',
    'chunks.diffModified': 'modifi\u00e9(s)',
    'chunks.diffRemoved': 'supprim\u00e9(s)',
    'chunks.pushTitle': 'Ing\u00e9rer dans un store',
    'chunks.pushStore': 'Store cible',
    'chunks.pushPlaceholder': 'Nom du store\u2026',
    'chunks.pushSummary': '{embeds} chunks \u00b7 ~{tokens} tokens',
    'chunks.pushConfirm': 'Ing\u00e9rer',
    'chunks.pushCancel': 'Annuler',
    'chunks.pushedJob': 'Job lanc\u00e9 : {jobId}',
    // Stale stores strip (#224)
    'chunks.stale.pushedAt': 'ing\u00e9r\u00e9 le {date}',
    'chunks.stale.reingest': 'R\u00e9-ing\u00e9rer',
    'chunks.stale.reingestAll': 'R\u00e9-ing\u00e9rer tous les obsol\u00e8tes',
    'chunks.stale.jobDispatched': 'Job lanc\u00e9 : {jobId}',

    'chunks.selected': '{n} s\u00e9lectionn\u00e9(s)',
    'chunks.bulkDrop': 'Supprimer la s\u00e9lection',
    'chunks.bulkMerge': 'Fusionner la s\u00e9lection',
    'chunks.bulkCancel': 'Annuler',

    // Stores list (#243)
    'stores.title': 'Stores',
    'stores.empty': 'Aucun store configur\u00e9.',
    'stores.colName': 'Nom',
    'stores.colType': 'Type',
    'stores.colStatus': 'Statut',
    'stores.colDocs': 'Documents',
    'stores.colChunks': 'Chunks',
    'stores.connected': 'Connect\u00e9',
    'stores.disconnected': 'D\u00e9connect\u00e9',
    'stores.error': 'Erreur',

    // Store detail (#244)
    'storeDetail.back': 'Stores',
    'storeDetail.query': 'Requ\u00eater',
    'storeDetail.empty': 'Aucun document dans ce store.',
    'storeDetail.colDoc': 'Document',
    'storeDetail.colState': '\u00c9tat',
    'storeDetail.colChunks': 'Chunks',
    'storeDetail.colIngested': 'Ing\u00e9r\u00e9 le',
    'storeDetail.remove': 'Retirer',
    'storeDetail.removeConfirm': 'Retirer \u00ab\u00a0{doc}\u00a0\u00bb du store\u00a0?',
    'storeDetail.selected': '{n} s\u00e9lectionn\u00e9(s)',
    'storeDetail.bulkRemove': 'Retirer du store',
    'storeDetail.bulkCancel': 'Annuler',
    'storeDetail.bulkConfirm': 'Retirer {n} document(s) du store\u00a0?',

    // Store query (#245)
    'storeQuery.back': 'D\u00e9tail du store',
    'storeQuery.queryLabel': 'Question',
    'storeQuery.queryPlaceholder': 'Votre question\u2026',
    'storeQuery.topKLabel': 'R\u00e9sultats (top-k)',
    'storeQuery.run': 'Rechercher',
    'storeQuery.running': 'Recherche\u2026',
    'storeQuery.empty': 'Aucun r\u00e9sultat.',
    'storeQuery.colScore': 'Score',
    'storeQuery.colDoc': 'Document',
    'storeQuery.colText': 'Extrait',
    'storeQuery.colPage': 'Pages',
    'storeQuery.viewDoc': 'Voir',

    // Disclaimer
    'disclaimer.banner':
      'Instance de d\u00e9monstration \u2014 les documents upload\u00e9s sont partag\u00e9s et temporaires (max {n} Mo). Ne pas envoyer de fichiers confidentiels.',
  },
  en: {
    // Sidebar — 0.6.0 doc-centric nav (#209)
    'nav.home': 'Home',
    'nav.docs': 'Docs',
    'nav.stores': 'Stores',
    'nav.runs': 'Runs',
    'nav.settings': 'Settings',
    'nav.collapse': 'Collapse sidebar',
    'nav.expand': 'Expand sidebar',
    // Legacy nav labels — kept because legacy pages still use them.
    'nav.studio': 'Studio',
    'nav.documents': 'Documents',
    'nav.history': 'History',
    'nav.reasoning': 'Reasoning',
    'nav.search': 'Search',

    'topbar.newAnalysis': 'New analysis',

    // Breadcrumb (0.6.0 doc workspace — #208)
    'breadcrumb.aria': 'Breadcrumb',
    'breadcrumb.studio': 'Studio',
    'breadcrumb.mode.ask': 'Ask',
    'breadcrumb.mode.inspect': 'Inspect',
    'breadcrumb.mode.chunks': 'Chunks',

    // Feature flags (0.6.0 — #210)
    'flags.allModesDisabled':
      'No doc workspace mode (Ask / Inspect / Chunks) is enabled for this deployment. Contact your administrator.',

    // Lifecycle status badges (#215)
    'status.Uploaded': 'Uploaded',
    'status.Parsed': 'Parsed',
    'status.Chunked': 'Chunked',
    'status.Ingested': 'Ingested',
    'status.Stale': 'Stale',
    'status.Failed': 'Failed',
    'status.tooltip.Uploaded': 'File received, awaiting parsing.',
    'status.tooltip.Parsed': 'Document parsed successfully.',
    'status.tooltip.Chunked': 'Chunks generated, ready to ingest into a store.',
    'status.tooltip.Ingested': 'Ingested into at least one store.',
    'status.tooltip.Stale': 'Chunks modified since last ingestion — re-ingestion required.',
    'status.tooltip.Failed': 'A pipeline step failed. Retry to recover.',

    // Document library (#211, #212, #213)
    'docs.title': 'Documents',
    'docs.import': 'Import',
    'docs.emptyTitle': 'No documents yet',
    'docs.emptySubtitle': 'Import your first document to get started.',
    'docs.emptyAction': 'Import a document',
    'docs.emptyFiltered': 'No documents match the current filters.',
    'docs.colName': 'Name',
    'docs.colStatus': 'Status',
    'docs.colStores': 'Stores',
    'docs.colUpdated': 'Updated',
    'docs.filterSearch': 'Search…',
    'docs.filterClear': 'Clear filters',
    'docs.selected': '{n} selected',
    'docs.bulkRechunk': 'Re-chunk',
    'docs.bulkPush': 'Ingest into store…',
    'docs.bulkDelete': 'Delete',
    'docs.bulkCancel': 'Cancel selection',
    'docs.deleteConfirm': 'Delete {n} document(s)? This action cannot be undone.',
    'docs.pushTitle': 'Ingest into store',
    'docs.pushLabel': 'Target store',
    'docs.pushPlaceholder': 'Store name…',
    'docs.pushSubmit': 'Ingest',
    'docs.pushCancel': 'Cancel',
    'docs.jobDispatched': 'Job dispatched ({jobId})',

    // Doc import (#214)
    'docsNew.title': 'Import documents',
    'docsNew.drop': 'Drop PDFs here or click to choose',
    'docsNew.dropHint': 'Multiple files accepted · PDF only',
    'docsNew.queued': 'Queued',
    'docsNew.uploading': 'Uploading…',
    'docsNew.done': 'Imported',
    'docsNew.failed': 'Failed',
    'docsNew.viewDoc': 'View document',
    'docsNew.backToLibrary': 'Back to library',
    'docsNew.viewLibrary': 'View library',
    'docsNew.allDone': 'All files have been imported.',

    // Coming-soon placeholders (0.6.0 doc-centric routes — #207)
    'comingSoon.title': 'Coming soon',
    'comingSoon.subtitle.docsLibrary':
      'The document library lands with 0.6.0. It will show every document with its lifecycle state, the stores it lives in, and when it was last updated.',
    'comingSoon.subtitle.docsNew':
      'Multi-file import (drop a folder or pick multiple files) lands with 0.6.0.',
    'comingSoon.subtitle.docWorkspace':
      'The doc workspace (Inspect / Chunks / Ask) lands with 0.6.0.',
    'comingSoon.subtitle.stores': 'The stores list lands with 0.6.0.',
    'comingSoon.subtitle.storeDetail':
      'The store detail view (docs present, per-store state) lands with 0.6.0.',
    'comingSoon.subtitle.storeQuery': 'The RAG query playground lands with 0.6.0.',
    'comingSoon.subtitle.runs': 'The runs history (audit / debug) lands with 0.6.0.',
    'comingSoon.subtitle.runDetail': 'Run detail lands with 0.6.0.',
    'comingSoon.hint.docWorkspace': 'doc {id} · mode {mode}',
    'comingSoon.hint.storeDetail': 'store {store}',
    'comingSoon.hint.storeQuery': 'store {store}',
    'comingSoon.hint.runDetail': 'run {id}',
    'comingSoon.backHome': 'Back to home',

    'home.title': 'Docling Studio',
    'home.subtitle':
      'Analyze, explore and validate the structure of your PDF documents with Docling.',
    'home.documents': 'Documents',
    'home.analyses': 'Analyses',
    'home.recentDocs': 'Recent documents',

    'studio.title': 'Document Intelligence',
    'studio.subtitle': 'Upload a PDF document to start analyzing with Docling',
    'studio.recentDocs': 'Recent documents',

    'studio.configure': 'Configure',
    'studio.verify': 'Verify',
    'studio.addFiles': 'Add files',
    'studio.analyzing': 'Analyzing...',
    'studio.run': 'Run',
    'studio.loaded': 'Loaded',
    'studio.analysisRunning': 'Analysis running...',
    'studio.failed': 'Failed',
    'studio.visual': 'Visual',

    'config.model': 'Model',
    'config.pipeline': 'Pipeline',
    'config.ocr': 'OCR',
    'config.ocrHint':
      'Applies Optical Character Recognition on scanned pages or embedded images. Essential for non-native PDFs.',
    'config.tableStructure': 'Table extraction',
    'config.tableStructureHint':
      'Detects tables in the document and reconstructs their row/column structure using the TableFormer model, with cell matching.',
    'config.tableMode': 'Table mode',
    'config.tableModeAccurate': 'Accurate',
    'config.tableModeFast': 'Fast',
    'config.enrichment': 'Enrichment',
    'config.codeEnrichment': 'Code',
    'config.codeEnrichmentHint':
      'Activates a specialized OCR model for code blocks, preserving indentation and syntax.',
    'config.formulaEnrichment': 'Formulas',
    'config.formulaEnrichmentHint':
      'Recognizes mathematical formulas and converts them to LaTeX using a dedicated model.',
    'config.pictures': 'Pictures',
    'config.pictureClassification': 'Classification',
    'config.pictureClassificationHint':
      'Classifies each detected image by type (chart, photo, diagram, logo…) using a classification model.',
    'config.pictureDescription': 'Description',
    'config.pictureDescriptionHint':
      'Generates a text description for each image using a Vision Language Model (VLM). Useful for accessibility and indexing.',
    'config.generatePictureImages': 'Extract pictures',
    'config.generatePictureImagesHint':
      'Extracts detected images from the document and saves them as separate files. Required for image export.',
    'config.generatePageImages': 'Page images',
    'config.generatePageImagesHint':
      'Rasterizes each PDF page as an image. Useful for visual preview or post-processing.',
    'config.imagesScale': 'Images scale',
    'config.documents': 'Documents',

    'results.elements': 'Elements',
    'results.markdown': 'Markdown',
    'results.images': 'Images',
    'results.graph': 'Graph',
    'results.graphLoading': 'Loading graph…',
    'results.graphEmpty': 'No graph yet for this document (enable Neo4j).',
    // GraphView — node details panel & interactions
    'graph.nodeDetails': 'Node details',
    'graph.close': 'Close',
    'graph.page': 'Page',
    'graph.text': 'Text',
    'graph.provenances': 'Provenances ({n})',
    'graph.contains': 'Contents ({n})',
    'results.retry': 'Retry',
    'results.pageOf': 'Page {current} of {total}',
    'results.noElements': 'No elements detected on this page',
    'results.noImages': 'No images detected in this document',
    'results.noMarkdown': 'No markdown content',
    'results.runAnalysis': 'Run an analysis to see results',
    'results.analysisFailed': 'Analysis failed',
    'results.copy': 'Copy',
    'results.copied': 'Copied!',
    'results.page': 'Page',

    'upload.drop': 'Drop a PDF here or click to upload',
    'upload.uploading': 'Uploading...',
    'upload.maxSize': 'Max {n}MB',
    'upload.invalidFormat': 'Invalid format — only PDF files are accepted.',
    'upload.tooLarge': 'File too large (max {n} MB).',
    'upload.maxPages': 'Max {n} pages',

    'history.title': 'History',
    'history.tabAnalyses': 'Analyses',
    'history.tabDocuments': 'Documents',
    'history.empty': 'No analyses yet. Go to Studio to analyze your first document.',
    'history.emptyDocs': 'No documents yet. Upload a document from the Studio.',
    'history.open': 'Open',

    'studio.prepare': 'Prepare',
    'studio.ingest': 'Ingest',
    'studio.maintain': 'Maintain',
    // Reasoning trace (R&D v1 — overlays a docling-agent ReasoningResult on the graph)
    'reasoning.importBtn': 'Import reasoning trace',
    'reasoning.importTitle': 'Import reasoning trace',
    'reasoning.importHint':
      'Drop a reasoning-trace JSON produced by docling-agent (or by the experiments/reasoning-trace R&D script).',
    'reasoning.drop': 'Drop a .json file here',
    'reasoning.dropSub': 'or click to pick one',
    'reasoning.parsing': 'Parsing file...',
    'reasoning.pasteToggle': 'Paste JSON instead',
    'reasoning.pastePlaceholder': 'Paste a reasoning-trace JSON payload here...',
    'reasoning.pasteSubmit': 'Load',
    'reasoning.close': 'Close',
    'reasoning.errJson': 'Invalid JSON: {msg}',
    'reasoning.errShape':
      "File doesn't look like a reasoning trace (answer, converged, iterations).",
    'reasoning.panelTitle': 'Reasoning trace',
    'reasoning.focus': 'Focus',
    'reasoning.focusHint': 'Dim non-visited elements to make the reasoning path stand out.',
    'reasoning.reimport': 'Re-import',
    'reasoning.clear': 'Clear',
    'reasoning.query': 'Question',
    'reasoning.converged': 'Converged',
    'reasoning.notConverged': 'Max iterations',
    'reasoning.resolved': 'sections resolved',
    'reasoning.answerLabel': 'Answer',
    'reasoning.copy': 'Copy',
    'reasoning.copied': 'Copied ✓',
    'reasoning.copyAnswer': 'Copy answer to clipboard',
    'reasoning.reasonPlaceholder': '— no structured rationale',
    'reasoning.missingWarn':
      '{n} section(s) missing from the graph. The document may have been re-analyzed — re-run Maintain or regenerate the trace.',
    'reasoning.graphNotLoadedWarn':
      "This document's Neo4j graph isn't loaded — iterations are shown but can't be positioned on the structure. Run prime_neo4j or trigger a fresh analysis.",
    'reasoning.iterationsTitle': 'Iterations',
    'reasoning.noIterations': 'Agent visited no section (document without headers?).',
    'reasoning.statusAnswered': 'Answered',
    'reasoning.statusMore': 'More needed',
    'reasoning.statusMissing': 'Missing',
    'reasoning.charsLabel': '{n} chars',
    // Reasoning page (standalone tunnel)
    'reasoning.pageTitle': 'Reasoning Trace',
    'reasoning.pageSubtitle':
      "Drop a PDF, then import a reasoning trace from docling-agent to visualize the reasoning path on the document's graph.",
    'reasoning.dropPdf': 'Drop a PDF',
    'reasoning.dropPdfHint': 'or click to pick one',
    'reasoning.uploading': 'Uploading document...',
    'reasoning.existingDocs': 'Previously analyzed documents',
    'reasoning.noAnalyzedDocs':
      'None of your existing documents have been analyzed yet — run one from Studio, or drop a new PDF above.',
    'reasoning.pagesCount': '{n} pages',
    'reasoning.changeDoc': 'Change document',
    'reasoning.modeSwitchLabel': 'View mode',
    'reasoning.modeGraph': 'Graph',
    'reasoning.modeDocument': 'Document',
    'reasoning.docNoContent': 'No rendered content available for this document.',
    'reasoning.analyzing': 'Analyzing document...',
    'reasoning.analyzingHint':
      'Docling is parsing the PDF with default settings. May take 1–3 minutes depending on size.',
    'reasoning.runBtn': 'Run reasoning',
    'reasoning.runTitle': 'Run docling-agent',
    'reasoning.runHint':
      'Ask a question against this document. The backend calls docling-agent over Ollama and returns the trace once the loop converges (20–40s).',
    'reasoning.runQueryLabel': 'Question',
    'reasoning.runQueryPlaceholder': 'e.g. What are the supplier obligations?',
    'reasoning.runModelLabel': 'Model (optional)',
    'reasoning.runModelPlaceholder': 'gpt-oss:20b',
    'reasoning.runModelSub':
      'Ollama model name. Leave empty to use the server default (REASONING_MODEL_ID).',
    'reasoning.runSubmit': 'Run',
    'reasoning.running': 'docling-agent is thinking… (20–40s)',
    'reasoning.runErrUnknown': 'Unknown error while calling docling-agent.',
    'reasoning.cancel': 'Cancel',
    'reasoning.retry': 'Retry',
    'reasoning.pickAnother': 'Pick another document',
    'reasoning.prepError': 'Preparation failed',
    'reasoning.prepErrAnalysis': 'Docling analysis failed or produced no document_json.',
    'reasoning.prepErrTimeout': 'Analysis is taking too long — try again later.',
    'reasoning.prepErrUnknown': 'Unknown error.',
    'chunking.settings': 'Chunking',
    'chunking.chunkerType': 'Chunker type',
    'chunking.maxTokens': 'Max tokens',
    'chunking.mergePeers': 'Merge peers',
    'chunking.repeatTableHeader': 'Repeat table headers',
    'chunking.run': 'Chunk',
    'chunking.chunking': 'Chunking...',
    'chunking.chunks': 'chunks',
    'chunking.noChunks': 'Run chunking to prepare segments.',
    'chunking.noChunksOnPage': 'No chunks on this page.',
    'chunking.edit': 'Edit',
    'chunking.save': 'Save',
    'chunking.saving': 'Saving...',
    'chunking.cancel': 'Cancel',
    'chunking.modified': 'modified',
    'chunking.delete': 'Delete',
    'chunking.deleting': 'Deleting...',
    'chunking.deleteConfirm':
      'Delete this chunk? It will be marked as deleted until the next sync.',
    'chunking.batchNotice':
      'Chunking is not available for this analysis. Large documents processed in batch mode do not generate the internal structure required for chunking. Coming soon!',

    'search.hint': 'Enter a term to search through ingested chunks.',

    'ingestion.ingest': 'Ingest',
    'ingestion.document': 'Document',
    'ingestion.chunkCount': 'Chunks ready',
    'ingestion.successMessage': 'Ingestion completed successfully!',
    'ingestion.ingesting': 'Ingesting...',
    'ingestion.reindex': 'Re-ingest',
    'ingestion.indexed': 'Ingested',
    'ingestion.notIndexed': 'Not ingested',
    'ingestion.chunksIndexed': '{n} chunks ingested',
    'ingestion.openInStudio': 'Open in Studio',
    'ingestion.deleteIndex': 'Remove from store',
    'ingestion.deleteConfirm':
      'Remove this document from the index? Chunks will be deleted but the source document will remain.',
    'ingestion.unavailable': 'Ingestion unavailable',
    'ingestion.filterAll': 'All',
    'ingestion.filterIndexed': 'Ingested',
    'ingestion.filterNotIndexed': 'Not ingested',
    'ingestion.sortName': 'Name',
    'ingestion.sortDate': 'Date',
    'ingestion.search': 'Search...',
    'ingestion.searchChunks': 'Search indexed chunks…',
    'ingestion.noResults': 'No results for "{q}".',
    'ingestion.stepEmbedding': 'Embedding…',
    'ingestion.stepIndexing': 'Ingesting…',
    'ingestion.stepDone': 'Done',
    'ingestion.opensearchConnected': 'OpenSearch connected',
    'ingestion.opensearchDisconnected': 'OpenSearch unreachable',

    'pagination.pageOf': 'Page {current} of {total}',
    'pagination.perPage': '/ page',

    'settings.title': 'Settings',
    'settings.version': 'Version',
    'settings.theme': 'Theme',
    'settings.themeDark': 'Dark',
    'settings.themeLight': 'Light',
    'settings.language': 'Language',
    'settings.about': 'About',
    'settings.designArticle': 'How Docling Studio was designed',

    // Inspect tab (#240, #241)
    'inspect.tabMarkdown': 'Markdown',
    'inspect.tabElements': 'Elements',
    'inspect.tabImages': 'Images',
    'inspect.noAnalysis': 'No analysis available',
    'inspect.noAnalysisSub': 'Analyze this document in Studio to see its structure.',
    'inspect.goToStudio': 'Go to Studio',
    'inspect.retry': 'Retry',
    'inspect.noElements': 'No elements — run an analysis to generate structure.',

    // Ask tab (#242)
    'ask.questionLabel': 'Question',
    'ask.questionPlaceholder': 'e.g. What are the supplier obligations?',
    'ask.modelConfig': 'Model (optional)',
    'ask.modelPlaceholder': 'gpt-oss:20b',
    'ask.modelHint': 'Ollama model name. Leave empty to use the server default.',
    'ask.run': 'Run',
    'ask.running': 'Reasoning…',
    'ask.answerLabel': 'Answer',
    'ask.noAnalysis': 'No analysis available',
    'ask.noAnalysisSub': 'Analyze this document in Studio before asking a question.',

    // Doc workspace (#216, #218)
    'workspace.tabs.ask': 'Ask',
    'workspace.tabs.inspect': 'Inspect',
    'workspace.tabs.chunks': 'Chunks',
    'workspace.backToLibrary': 'Back to library',
    'workspace.modeDisabled': 'Mode disabled for this deployment',
    'workspace.inspectComingSoon': 'Inspect \u2014 coming in 0.7.0',
    'workspace.inspectComingSoonHint': 'Tree + bbox view coming soon.',
    'workspace.askComingSoon': 'Ask \u2014 coming in 0.7.0',
    'workspace.askComingSoonHint': 'Agentic reasoning over the document coming soon.',

    // Doc tree rail (#217)
    'tree.empty': 'No nodes in tree.',
    'tree.expand': 'Expand',
    'tree.collapse': 'Collapse',

    // Chunks editor (#219, #220, #221, #222)
    'chunks.count': '{n} chunk(s)',
    'chunks.empty': 'No chunks yet \u2014 parse the document first.',
    'chunks.saving': 'Saving\u2026',
    'chunks.noTitle': '(untitled)',
    'chunks.editPlaceholder': 'Chunk text\u2026',
    'chunks.mergePrev': 'Merge with previous',
    'chunks.mergeNext': 'Merge with next',
    'chunks.split': 'Split at cursor',
    'chunks.drop': 'Drop',
    'chunks.add': 'Add chunk',
    'chunks.retitle': 'Rename',
    'chunks.diffToggle': 'Show diff',
    'chunks.diffClose': 'Close diff',
    'chunks.diffRef': 'Reference',
    'chunks.diffAdded': 'added',
    'chunks.diffModified': 'modified',
    'chunks.diffRemoved': 'removed',
    'chunks.pushTitle': 'Ingest into store',
    'chunks.pushStore': 'Target store',
    'chunks.pushPlaceholder': 'Store name\u2026',
    'chunks.pushSummary': '{embeds} chunks \u00b7 ~{tokens} tokens',
    'chunks.pushConfirm': 'Ingest',
    'chunks.pushCancel': 'Cancel',
    'chunks.pushedJob': 'Job dispatched: {jobId}',
    // Stale stores strip (#224)
    'chunks.stale.pushedAt': 'ingested on {date}',
    'chunks.stale.reingest': 'Re-ingest',
    'chunks.stale.reingestAll': 'Re-ingest all stale',
    'chunks.stale.jobDispatched': 'Job dispatched: {jobId}',

    'chunks.selected': '{n} selected',
    'chunks.bulkDrop': 'Drop selected',
    'chunks.bulkMerge': 'Merge selected',
    'chunks.bulkCancel': 'Cancel',

    // Stores list (#243)
    'stores.title': 'Stores',
    'stores.empty': 'No stores configured.',
    'stores.colName': 'Name',
    'stores.colType': 'Type',
    'stores.colStatus': 'Status',
    'stores.colDocs': 'Documents',
    'stores.colChunks': 'Chunks',
    'stores.connected': 'Connected',
    'stores.disconnected': 'Disconnected',
    'stores.error': 'Error',

    // Store detail (#244)
    'storeDetail.back': 'Stores',
    'storeDetail.query': 'Query',
    'storeDetail.empty': 'No documents in this store.',
    'storeDetail.colDoc': 'Document',
    'storeDetail.colState': 'State',
    'storeDetail.colChunks': 'Chunks',
    'storeDetail.colIngested': 'Ingested',
    'storeDetail.remove': 'Remove',
    'storeDetail.removeConfirm': 'Remove \u00ab{doc}\u00bb from store?',
    'storeDetail.selected': '{n} selected',
    'storeDetail.bulkRemove': 'Remove from store',
    'storeDetail.bulkCancel': 'Cancel',
    'storeDetail.bulkConfirm': 'Remove {n} document(s) from store?',

    // Store query (#245)
    'storeQuery.back': 'Store detail',
    'storeQuery.queryLabel': 'Question',
    'storeQuery.queryPlaceholder': 'Your question\u2026',
    'storeQuery.topKLabel': 'Results (top-k)',
    'storeQuery.run': 'Search',
    'storeQuery.running': 'Searching\u2026',
    'storeQuery.empty': 'No results.',
    'storeQuery.colScore': 'Score',
    'storeQuery.colDoc': 'Document',
    'storeQuery.colText': 'Excerpt',
    'storeQuery.colPage': 'Pages',
    'storeQuery.viewDoc': 'View',

    // Disclaimer
    'disclaimer.banner':
      'Demo instance \u2014 uploaded documents are shared and temporary (max {n} MB). Do not upload confidential files.',
  },
}

export function useI18n() {
  function t(key: string, params: Record<string, string | number> = {}): string {
    let str = messages[appLocale.value]?.[key] || messages['fr'][key] || key
    for (const [k, v] of Object.entries(params)) {
      str = str.replaceAll(`{${k}}`, String(v))
    }
    return str
  }

  return { t }
}
