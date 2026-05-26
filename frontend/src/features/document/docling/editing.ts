import { doclingDocument, type DoclingDocument } from './docling-document.generated'

export type { DoclingDocument } from './docling-document.generated'

export type DoclingRef = { $ref: string }

export type DoclingNode = {
  self_ref: string
  parent?: DoclingRef | null
  children?: DoclingRef[]
}

export type DoclingTextItem = DoclingDocument['texts'][number] &
  DoclingNode & {
    text: string
    orig?: string | null
    prov?: DoclingProvenance[] | null
  }

export type DoclingGroupItem = DoclingDocument['groups'][number] & DoclingNode
export type DoclingTextLabel = DoclingDocument['texts'][number]['label']
export type DoclingGroupLabel = DoclingDocument['groups'][number]['label']
export type DoclingContentLayer = DoclingDocument['body']['content_layer']

export type DoclingBoundingBox = {
  l: number
  t: number
  r: number
  b: number
  coord_origin?: string
}

export type DoclingProvenance = {
  page_no: number
  bbox?: DoclingBoundingBox | null
  charspan?: number[] | null
}

export interface DoclingInsertTextOptions {
  parentRef: string
  text: string
  index?: number
  label?: DoclingTextLabel
  contentLayer?: DoclingContentLayer
  orig?: string | null
  prov?: DoclingProvenance[]
}

export interface DoclingCreateGroupOptions {
  parentRef: string
  index?: number
  name?: string
  label?: DoclingGroupLabel
  contentLayer?: DoclingContentLayer
}

export interface DoclingMutationOptions {
  normalizeRefs?: boolean
}

export interface DoclingIndexEntry {
  ref: string
  item: DoclingNode
  collectionKey: ItemCollectionKey | RootCollectionKey
  index: number | null
}

export interface DoclingIndex {
  itemsByRef: Map<string, DoclingIndexEntry>
  childrenByParentRef: Map<string, readonly DoclingRef[]>
  collectionEntriesByRef: Map<string, { key: ItemCollectionKey; index: number }>
  textRefs: Set<string>
  groupRefs: Set<string>
}

const ITEM_COLLECTION_KEYS = [
  'groups',
  'texts',
  'pictures',
  'tables',
  'key_value_items',
  'form_items',
  'field_regions',
  'field_items',
] as const

const ROOT_COLLECTION_KEYS = ['body', 'furniture'] as const

type ItemCollectionKey = (typeof ITEM_COLLECTION_KEYS)[number]
type RootCollectionKey = (typeof ROOT_COLLECTION_KEYS)[number]

let tempRefCounter = 0
const CANONICAL_REF_PATTERN = /^#(?:\/([\w-]+)(?:\/(\d+))?)?$/
const doclingIndexCache = new WeakMap<DoclingDocument, DoclingIndex>()

/** Thrown when a frontend Docling edit would leave the document inconsistent. */
export class DoclingEditError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'DoclingEditError'
  }
}

/** Parse the raw JSON and enforce additional structural invariants. */
export function parseDoclingDocument(value: unknown): DoclingDocument {
  const parsed = doclingDocument.parse(value)
  cacheDoclingIndex(parsed, computeDoclingIndex(parsed))
  return parsed
}

/** Re-validate a document we already typed as `DoclingDocument`. */
export function validateDoclingDocument(doc: DoclingDocument): DoclingDocument {
  return parseDoclingDocument(doc)
}

/** Deep clone a document and re-validate the clone. */
export function cloneDoclingDocument(doc: DoclingDocument): DoclingDocument {
  const clone = structuredClone(doc)
  return hasNonCanonicalRefs(clone) ? validateDraftDoclingDocument(clone) : parseDoclingDocument(clone)
}

/** Stable JSON output for persistence, debugging, or draft export. */
export function stringifyDoclingDocument(doc: DoclingDocument): string {
  return JSON.stringify(doc, null, 2)
}

/** Normalize collection refs into canonical `#/collection/N` form for export. */
export function exportDoclingDocument(doc: DoclingDocument): DoclingDocument {
  return finalizeDoclingDocument(cloneDoclingDocument(doc), { normalizeRefs: true })
}

/**
 * Validate an in-session draft document that may contain temporary non-canonical
 * refs. This enforces graph consistency without requiring Docling export refs.
 */
export function validateDraftDoclingDocument(doc: DoclingDocument): DoclingDocument {
  invalidateDoclingIndex(doc)
  cacheDoclingIndex(doc, computeDoclingIndex(doc))
  return doc
}

/**
 * Build an indexed view over the document and enforce structural invariants:
 * unique refs, reciprocal parent/child links, reachability from body/furniture,
 * and duplicate-free child lists.
 */
export function buildDoclingIndex(doc: DoclingDocument): DoclingIndex {
  const cached = doclingIndexCache.get(doc)
  if (cached) {
    return cached
  }

  return cacheDoclingIndex(doc, computeDoclingIndex(doc))
}

function computeDoclingIndex(doc: DoclingDocument): DoclingIndex {
  const itemsByRef = new Map<string, DoclingIndexEntry>()
  const childrenByParentRef = new Map<string, readonly DoclingRef[]>()
  const collectionEntriesByRef = new Map<string, { key: ItemCollectionKey; index: number }>()
  const textRefs = new Set<string>()
  const groupRefs = new Set<string>()

  const registerRoot = (key: RootCollectionKey, item: DoclingNode): void => {
    registerEntry({ ref: item.self_ref, item, collectionKey: key, index: null })
    childrenByParentRef.set(item.self_ref, item.children ?? [])
  }

  const registerCollection = (key: ItemCollectionKey, items: DoclingNode[]): void => {
    items.forEach((item, index) => {
      registerEntry({ ref: item.self_ref, item, collectionKey: key, index })
      collectionEntriesByRef.set(item.self_ref, { key, index })
      childrenByParentRef.set(item.self_ref, item.children ?? [])
      if (key === 'texts') textRefs.add(item.self_ref)
      if (key === 'groups') groupRefs.add(item.self_ref)
    })
  }

  const registerEntry = (entry: DoclingIndexEntry): void => {
    if (itemsByRef.has(entry.ref)) {
      throw new DoclingEditError(`Duplicate self_ref detected: ${entry.ref}`)
    }
    itemsByRef.set(entry.ref, entry)
  }

  registerRoot('body', doc.body as DoclingNode)
  registerRoot('furniture', doc.furniture as DoclingNode)

  for (const key of ITEM_COLLECTION_KEYS) {
    registerCollection(key, doc[key] as DoclingNode[])
  }

  const parentByChildRef = new Map<string, string>()
  for (const [parentRef, children] of childrenByParentRef) {
    const seen = new Set<string>()
    for (const child of children) {
      if (seen.has(child.$ref)) {
        throw new DoclingEditError(`Duplicate child ref ${child.$ref} under parent ${parentRef}`)
      }
      seen.add(child.$ref)

      const childEntry = itemsByRef.get(child.$ref)
      if (!childEntry) {
        throw new DoclingEditError(`Unresolved child ref ${child.$ref} under parent ${parentRef}`)
      }
      if (parentByChildRef.has(child.$ref)) {
        throw new DoclingEditError(`Item ${child.$ref} is attached to multiple parents`)
      }
      parentByChildRef.set(child.$ref, parentRef)
    }
  }

  for (const [ref, entry] of itemsByRef) {
    if (entry.collectionKey === 'body' || entry.collectionKey === 'furniture') {
      if (entry.item.parent) {
        throw new DoclingEditError(`Root item ${ref} cannot have a parent`)
      }
      continue
    }

    const declaredParentRef = entry.item.parent?.$ref
    if (!declaredParentRef) {
      throw new DoclingEditError(`Item ${ref} is missing its parent ref`)
    }

    if (!itemsByRef.has(declaredParentRef)) {
      throw new DoclingEditError(`Item ${ref} references unknown parent ${declaredParentRef}`)
    }

    const containerParentRef = parentByChildRef.get(ref)
    if (!containerParentRef) {
      throw new DoclingEditError(`Item ${ref} is not attached in any parent children list`)
    }

    if (containerParentRef !== declaredParentRef) {
      throw new DoclingEditError(
        `Item ${ref} declares parent ${declaredParentRef} but is attached under ${containerParentRef}`,
      )
    }
  }

  const reachable = new Set<string>()
  const visiting = new Set<string>()
  const visit = (ref: string): void => {
    if (visiting.has(ref)) {
      throw new DoclingEditError(`Cycle detected at ${ref}`)
    }
    if (reachable.has(ref)) {
      return
    }

    visiting.add(ref)
    for (const child of childrenByParentRef.get(ref) ?? []) {
      visit(child.$ref)
    }
    visiting.delete(ref)
    reachable.add(ref)
  }

  visit('#/body')
  visit('#/furniture')

  for (const ref of itemsByRef.keys()) {
    if (!reachable.has(ref)) {
      throw new DoclingEditError(`Item ${ref} is unreachable from body or furniture roots`)
    }
  }

  return {
    itemsByRef,
    childrenByParentRef,
    collectionEntriesByRef,
    textRefs,
    groupRefs,
  }
}

/** Resolve any item by `self_ref`. Returns `null` when not found. */
export function getDoclingItem(doc: DoclingDocument, ref: string): DoclingNode | null {
  return buildDoclingIndex(doc).itemsByRef.get(ref)?.item ?? null
}

/** Update a text node while preserving a valid Docling document. */
export function editDoclingText(
  doc: DoclingDocument,
  itemRef: string,
  text: string,
  options: DoclingMutationOptions = {},
): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const item = requireTextItem(next, itemRef)

  item.text = text
  item.orig = text
  for (const provenance of item.prov ?? []) {
    provenance.charspan = [0, text.length]
  }

  return finalizeDoclingDocument(next, options)
}

/**
 * Move an existing item under a new parent and insert it at a precise sibling
 * index. This is the general reorder/reparent primitive.
 */
export function moveDoclingItem(
  doc: DoclingDocument,
  itemRef: string,
  targetParentRef: string,
  targetIndex?: number,
  options: DoclingMutationOptions = {},
): DoclingDocument {
  if (isRootRef(itemRef)) {
    throw new DoclingEditError(`Cannot move root item ${itemRef}`)
  }
  if (itemRef === targetParentRef) {
    throw new DoclingEditError('An item cannot become its own parent')
  }

  const next = cloneDoclingDocument(doc)
  const child = requireNode(next, itemRef)
  const targetChildren = requireEditableParentChildren(next, targetParentRef)

  if (isDescendantRef(next, itemRef, targetParentRef)) {
    throw new DoclingEditError('Cannot move an item into its own descendant')
  }

  const oldParentRef = child.parent?.$ref ?? null
  const oldChildren = getParentChildren(next, oldParentRef)
  if (!oldChildren) {
    throw new DoclingEditError(`Cannot resolve current parent for ${itemRef}`)
  }

  const oldIndex = oldChildren.findIndex((candidate) => candidate.$ref === itemRef)
  if (oldIndex === -1) {
    throw new DoclingEditError(`Current parent does not contain ${itemRef}`)
  }

  oldChildren.splice(oldIndex, 1)

  let resolvedIndex = clampInsertionIndex(targetChildren, targetIndex)
  if (oldChildren === targetChildren && oldIndex < resolvedIndex) {
    resolvedIndex -= 1
  }
  removeChildRef(targetChildren, itemRef)
  targetChildren.splice(resolvedIndex, 0, { $ref: itemRef })
  child.parent = { $ref: targetParentRef }

  return finalizeDoclingDocument(next, options)
}

/** Backwards-compatible append-to-parent helper built on `moveDoclingItem()`. */
export function reparentDoclingItem(
  doc: DoclingDocument,
  childRef: string,
  targetParentRef: string,
  options: DoclingMutationOptions = {},
): DoclingDocument {
  const targetChildren = requireEditableParentChildren(doc, targetParentRef)
  return moveDoclingItem(doc, childRef, targetParentRef, targetChildren.length, options)
}

/** Merge two adjacent text siblings into the leading item. */
export function mergeAdjacentDoclingTexts(
  doc: DoclingDocument,
  leadingRef: string,
  trailingRef: string,
  spacer = ' ',
  options: DoclingMutationOptions = {},
): DoclingDocument {
  assertAdjacentTextSiblings(doc, leadingRef, trailingRef)

  const next = cloneDoclingDocument(doc)
  const leading = requireTextItem(next, leadingRef)
  const trailing = requireTextItem(next, trailingRef)
  const parentRef = leading.parent?.$ref ?? null
  const siblings = getParentChildren(next, parentRef)
  if (!siblings) {
    throw new DoclingEditError('Cannot resolve sibling order for merge')
  }

  const leadingOrig = leading.orig ?? leading.text
  const trailingOrig = trailing.orig ?? trailing.text
  const joiner = joinText(leading.text, trailing.text, spacer)

  leading.text = `${leading.text}${joiner}${trailing.text}`
  leading.orig = `${leadingOrig}${joiner}${trailingOrig}`
  mergeProvenance(leading, trailing)

  removeChildRef(siblings, trailingRef)
  removeItemFromCollection(next, trailingRef)

  return finalizeDoclingDocument(next, {
    normalizeRefs: options.normalizeRefs ?? true,
  })
}

/** Split one text node into two adjacent text nodes. */
export function splitDoclingText(
  doc: DoclingDocument,
  itemRef: string,
  offset: number,
  options: DoclingMutationOptions = {},
): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const item = requireTextItem(next, itemRef)

  if (offset <= 0 || offset >= item.text.length) {
    throw new DoclingEditError(`Split offset ${offset} is out of bounds for ${itemRef}`)
  }

  const parentRef = item.parent?.$ref ?? '#/body'
  const siblings = getParentChildren(next, parentRef)
  if (!siblings) {
    throw new DoclingEditError(`Cannot resolve sibling order for split on ${itemRef}`)
  }

  const itemIndex = siblings.findIndex((candidate) => candidate.$ref === itemRef)
  if (itemIndex === -1) {
    throw new DoclingEditError(`Parent does not contain ${itemRef}`)
  }

  const collectionIndex = next.texts.findIndex((candidate) => candidate.self_ref === itemRef)
  if (collectionIndex === -1) {
    throw new DoclingEditError(`Cannot resolve text collection position for ${itemRef}`)
  }

  const leadingText = item.text.slice(0, offset)
  const trailingText = item.text.slice(offset)
  const leadingOrig = (item.orig ?? item.text).slice(0, offset)
  const trailingOrig = (item.orig ?? item.text).slice(offset)

  item.text = leadingText
  item.orig = leadingOrig
  for (const provenance of item.prov ?? []) {
    provenance.charspan = [0, leadingText.length]
  }

  const trailing = createTextItem({
    selfRef: createTempRef('texts'),
    parentRef,
    text: trailingText,
    label: item.label,
    contentLayer: (item as { content_layer?: DoclingContentLayer }).content_layer ?? 'body',
    orig: trailingOrig,
    prov: structuredClone(item.prov ?? []).map((provenance) => ({
      ...provenance,
      charspan: [0, trailingText.length],
    })),
  })

  next.texts.splice(collectionIndex + 1, 0, trailing)
  siblings.splice(itemIndex + 1, 0, { $ref: trailing.self_ref })

  return finalizeDoclingDocument(next, {
    normalizeRefs: options.normalizeRefs ?? true,
  })
}

/** Insert a new text node under the body or a group. */
export function insertDoclingText(
  doc: DoclingDocument,
  options: DoclingInsertTextOptions,
  mutationOptions: DoclingMutationOptions = {},
): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const parentChildren = requireEditableParentChildren(next, options.parentRef)
  const text = createTextItem({
    selfRef: createTempRef('texts'),
    parentRef: options.parentRef,
    text: options.text,
    label: options.label ?? 'text',
    contentLayer: options.contentLayer ?? 'body',
    orig: options.orig ?? options.text,
    prov: structuredClone(options.prov ?? []),
  })

  next.texts.push(text)
  parentChildren.splice(clampInsertionIndex(parentChildren, options.index), 0, { $ref: text.self_ref })

  return finalizeDoclingDocument(next, {
    normalizeRefs: mutationOptions.normalizeRefs ?? true,
  })
}

/** Create an empty group under the body or another group. */
export function createDoclingGroup(
  doc: DoclingDocument,
  options: DoclingCreateGroupOptions,
  mutationOptions: DoclingMutationOptions = {},
): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const parentChildren = requireEditableParentChildren(next, options.parentRef)
  const group = {
    self_ref: createTempRef('groups'),
    parent: { $ref: options.parentRef },
    children: [],
    content_layer: options.contentLayer ?? 'body',
    name: options.name ?? 'group',
    label: options.label ?? 'section',
    meta: null,
  } as DoclingGroupItem

  next.groups.push(group)
  parentChildren.splice(clampInsertionIndex(parentChildren, options.index), 0, { $ref: group.self_ref })

  return finalizeDoclingDocument(next, {
    normalizeRefs: mutationOptions.normalizeRefs ?? true,
  })
}

/** Delete an item and its descendants, then renormalize all collection refs. */
export function deleteDoclingItem(
  doc: DoclingDocument,
  itemRef: string,
  options: DoclingMutationOptions = {},
): DoclingDocument {
  if (isRootRef(itemRef)) {
    throw new DoclingEditError(`Cannot delete root item ${itemRef}`)
  }

  const next = cloneDoclingDocument(doc)
  const refsToDelete = collectDescendantRefs(next, itemRef)
  refsToDelete.add(itemRef)

  const item = requireNode(next, itemRef)
  const parentRef = item.parent?.$ref ?? null
  const siblings = getParentChildren(next, parentRef)
  if (!siblings) {
    throw new DoclingEditError(`Cannot resolve parent list for ${itemRef}`)
  }
  removeChildRef(siblings, itemRef)

  for (const key of ITEM_COLLECTION_KEYS) {
    const collection = next[key] as DoclingNode[]
    next[key] = collection.filter((candidate) => !refsToDelete.has(candidate.self_ref)) as never
  }

  return finalizeDoclingDocument(next, {
    normalizeRefs: options.normalizeRefs ?? true,
  })
}

function requireNode(doc: DoclingDocument, ref: string): DoclingNode {
  const item = buildDoclingIndex(doc).itemsByRef.get(ref)?.item
  if (!item) {
    throw new DoclingEditError(`Item not found: ${ref}`)
  }
  return item
}

function requireTextItem(doc: DoclingDocument, ref: string): DoclingTextItem {
  const item = requireNode(doc, ref)
  if (!isTextItem(item)) {
    throw new DoclingEditError(`Item ${ref} is not a text item`)
  }
  return item
}

function requireEditableParentChildren(doc: DoclingDocument, ref: string): DoclingRef[] {
  if (ref === '#/body') {
    return doc.body.children
  }

  const item = requireNode(doc, ref)
  if (!isGroupItem(item)) {
    throw new DoclingEditError(`Target parent is not editable: ${ref}`)
  }
  item.children ??= []
  return item.children
}

function isTextItem(value: DoclingNode): value is DoclingTextItem {
  return typeof (value as { text?: unknown }).text === 'string'
}

function isGroupItem(value: DoclingNode): value is DoclingGroupItem {
  return value.self_ref.startsWith('#/groups/')
}

function isRootRef(ref: string): boolean {
  return ref === '#/body' || ref === '#/furniture'
}

function getParentChildren(doc: DoclingDocument, parentRef: string | null): DoclingRef[] | null {
  if (!parentRef || parentRef === '#/body') {
    return doc.body.children
  }
  if (parentRef === '#/furniture') {
    return doc.furniture.children
  }

  const item = buildDoclingIndex(doc).itemsByRef.get(parentRef)?.item
  return item?.children ?? null
}

function removeItemFromCollection(doc: DoclingDocument, ref: string): void {
  const collectionKey = getCollectionKey(ref)
  if (!collectionKey) {
    throw new DoclingEditError(`Cannot delete non-collection item ${ref}`)
  }

  const collection = doc[collectionKey] as DoclingNode[]
  const index = collection.findIndex((item) => item.self_ref === ref)
  if (index === -1) {
    throw new DoclingEditError(`Item not found in collection: ${ref}`)
  }
  collection.splice(index, 1)
}

function getCollectionKey(ref: string): ItemCollectionKey | null {
  const match = /^#\/([^/]+)\//.exec(ref)
  if (!match) return null
  const key = match[1] as ItemCollectionKey
  return ITEM_COLLECTION_KEYS.includes(key) ? key : null
}

function removeChildRef(children: DoclingRef[], ref: string): void {
  const index = children.findIndex((candidate) => candidate.$ref === ref)
  if (index !== -1) {
    children.splice(index, 1)
  }
}

function assertAdjacentTextSiblings(
  doc: DoclingDocument,
  leadingRef: string,
  trailingRef: string,
): void {
  const leading = requireTextItem(doc, leadingRef)
  const trailing = requireTextItem(doc, trailingRef)
  const leadingParent = leading.parent?.$ref ?? null
  const trailingParent = trailing.parent?.$ref ?? null

  if (leadingParent !== trailingParent) {
    throw new DoclingEditError('Text items must share the same parent to merge')
  }

  const siblings = getParentChildren(doc, leadingParent)
  if (!siblings) {
    throw new DoclingEditError('Cannot resolve sibling order for merge')
  }

  const refs = siblings.map((item) => item.$ref)
  const leadingIndex = refs.indexOf(leadingRef)
  const trailingIndex = refs.indexOf(trailingRef)

  if (leadingIndex === -1 || trailingIndex === -1) {
    throw new DoclingEditError('Text items are not present in the parent children list')
  }
  if (trailingIndex !== leadingIndex + 1) {
    throw new DoclingEditError('Text items must be adjacent siblings to merge')
  }
}

function mergeProvenance(leading: DoclingTextItem, trailing: DoclingTextItem): void {
  const leadingProv = leading.prov ?? []
  if (leadingProv.length === 0) {
    return
  }

  for (const provenance of leadingProv) {
    provenance.charspan = [0, leading.text.length]
  }

  const trailingProv = trailing.prov ?? []
  if (trailingProv.length === 0) {
    return
  }

  const leadBox = leadingProv[0]?.bbox
  const trailBox = trailingProv[0]?.bbox
  if (leadBox && trailBox) {
    leadingProv[0].bbox = {
      l: Math.min(leadBox.l, trailBox.l),
      t: Math.min(leadBox.t, trailBox.t),
      r: Math.max(leadBox.r, trailBox.r),
      b: Math.max(leadBox.b, trailBox.b),
      coord_origin: leadBox.coord_origin,
    }
  }

  if (trailingProv.length > 1) {
    leadingProv.push(...structuredClone(trailingProv.slice(1)))
  }
}

function normalizeDoclingReferences(doc: DoclingDocument): void {
  const refMap = new Map<string, string>()

  for (const key of ITEM_COLLECTION_KEYS) {
    const collection = doc[key] as DoclingNode[]
    collection.forEach((item, index) => {
      const nextRef = `#/${key}/${index}`
      refMap.set(item.self_ref, nextRef)
      item.self_ref = nextRef
    })
  }

  const allNodes = [
    doc.body as DoclingNode,
    doc.furniture as DoclingNode,
    ...ITEM_COLLECTION_KEYS.flatMap((key) => doc[key] as DoclingNode[]),
  ]

  for (const node of allNodes) {
    if (node.parent && refMap.has(node.parent.$ref)) {
      node.parent.$ref = refMap.get(node.parent.$ref) as string
    }
    for (const child of node.children ?? []) {
      if (refMap.has(child.$ref)) {
        child.$ref = refMap.get(child.$ref) as string
      }
    }
  }
}

function finalizeDoclingDocument(
  doc: DoclingDocument,
  options: { normalizeRefs?: boolean } = {},
): DoclingDocument {
  invalidateDoclingIndex(doc)
  if (options.normalizeRefs ?? false) {
    normalizeDoclingReferences(doc)
    return parseDoclingDocument(doc)
  }
  return validateDraftDoclingDocument(doc)
}

function cacheDoclingIndex(doc: DoclingDocument, index: DoclingIndex): DoclingIndex {
  doclingIndexCache.set(doc, index)
  return index
}

function invalidateDoclingIndex(doc: DoclingDocument): void {
  doclingIndexCache.delete(doc)
}

function hasNonCanonicalRefs(doc: DoclingDocument): boolean {
  const refs: string[] = [doc.body.self_ref, doc.furniture.self_ref]
  const nodes = [doc.body as DoclingNode, doc.furniture as DoclingNode]

  for (const key of ITEM_COLLECTION_KEYS) {
    for (const item of doc[key] as DoclingNode[]) {
      refs.push(item.self_ref)
      nodes.push(item)
    }
  }

  for (const node of nodes) {
    if (node.parent) {
      refs.push(node.parent.$ref)
    }
    for (const child of node.children ?? []) {
      refs.push(child.$ref)
    }
  }

  return refs.some((ref) => !CANONICAL_REF_PATTERN.test(ref))
}

function collectDescendantRefs(doc: DoclingDocument, ref: string): Set<string> {
  const index = buildDoclingIndex(doc)
  const descendants = new Set<string>()
  const visit = (parentRef: string): void => {
    for (const child of index.childrenByParentRef.get(parentRef) ?? []) {
      if (descendants.has(child.$ref)) continue
      descendants.add(child.$ref)
      visit(child.$ref)
    }
  }
  visit(ref)
  return descendants
}

function isDescendantRef(doc: DoclingDocument, ancestorRef: string, candidateRef: string): boolean {
  const descendants = collectDescendantRefs(doc, ancestorRef)
  return descendants.has(candidateRef)
}

function clampInsertionIndex(children: readonly DoclingRef[], index: number | undefined): number {
  if (index == null) {
    return children.length
  }
  if (index < 0 || index > children.length) {
    throw new DoclingEditError(`Target index ${index} is outside 0..${children.length}`)
  }
  return index
}

function joinText(leading: string, trailing: string, spacer: string): string {
  if (!leading || !trailing) return ''
  if (!spacer) return ''
  if (/\s$/.test(leading) || /^\s/.test(trailing)) {
    return ''
  }
  return spacer
}

function createTempRef(key: ItemCollectionKey): string {
  tempRefCounter += 1
  return `#/${key}/__temp_${tempRefCounter}`
}

function createTextItem(options: {
  selfRef: string
  parentRef: string
  text: string
  label: DoclingTextLabel
  contentLayer: DoclingContentLayer
  orig: string | null
  prov: DoclingProvenance[]
}): DoclingTextItem {
  return {
    self_ref: options.selfRef,
    parent: { $ref: options.parentRef },
    children: [],
    comments: [],
    content_layer: options.contentLayer,
    formatting: null,
    hyperlink: null,
    label: options.label,
    meta: null,
    prov: options.prov,
    orig: options.orig,
    source: [],
    text: options.text,
  } as DoclingTextItem
}
