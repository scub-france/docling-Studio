import type { DoclingDocument } from './docling-document.generated'

import {
  buildDoclingIndex,
  cloneDoclingDocument,
  createDoclingGroup,
  type DoclingCreateGroupOptions,
  deleteDoclingItem,
  DoclingEditError,
  editDoclingText,
  exportDoclingDocument,
  getDoclingItem,
  insertDoclingText,
  mergeAdjacentDoclingTexts,
  moveDoclingItem,
  parseDoclingDocument,
  reparentDoclingItem,
  splitDoclingText,
  type DoclingIndex,
  type DoclingInsertTextOptions,
  type DoclingNode,
  type DoclingRef,
  type DoclingTextItem,
  validateDraftDoclingDocument,
} from './editing'

export type DoclingNodeId = string

export interface DoclingEditorState {
  document: DoclingDocument
  index: DoclingIndex
  revision: number
  checkpointRevision: number
}

export type DoclingEditOperation =
  | { type: 'edit-text'; itemRef: DoclingNodeId; text: string }
  | {
      type: 'move-item'
      itemRef: DoclingNodeId
      targetParentRef: DoclingNodeId | '#/body' | '#/furniture'
      targetIndex?: number
    }
  | { type: 'reparent-item'; itemRef: DoclingNodeId; targetParentRef: DoclingNodeId | '#/body' }
  | { type: 'merge-texts'; leadingRef: DoclingNodeId; trailingRef: DoclingNodeId; spacer?: string }
  | { type: 'split-text'; itemRef: DoclingNodeId; offset: number }
  | ({ type: 'insert-text' } & DoclingInsertTextOptions)
  | ({ type: 'create-group' } & DoclingCreateGroupOptions)
  | { type: 'delete-item'; itemRef: DoclingNodeId }

export interface DoclingCommand {
  readonly type: string
  apply(state: DoclingEditorState): DoclingEditorState
  undo(state: DoclingEditorState): DoclingEditorState
}

type ItemCollectionKey =
  | 'groups'
  | 'texts'
  | 'pictures'
  | 'tables'
  | 'key_value_items'
  | 'form_items'
  | 'field_regions'
  | 'field_items'

interface ItemSnapshot {
  collectionKey: ItemCollectionKey
  collectionIndex: number
  item: DoclingNode
}

interface SubtreeSnapshot {
  rootRef: string
  parentRef: string
  parentIndex: number
  items: ItemSnapshot[]
}

const ITEM_COLLECTION_KEYS: ItemCollectionKey[] = [
  'groups',
  'texts',
  'pictures',
  'tables',
  'key_value_items',
  'form_items',
  'field_regions',
  'field_items',
]

/**
 * Frontend-only draft editor for standalone Docling manipulation.
 *
 * This session keeps stable in-session node identifiers by preserving refs while
 * editing and only renormalizing them when exporting the final DoclingDocument.
 */
export class DoclingDraftSession {
  private stateValue: DoclingEditorState
  private checkpointDocument: DoclingDocument
  private past: DoclingCommand[] = []
  private future: DoclingCommand[] = []

  constructor(initial: DoclingDocument | unknown) {
    this.stateValue = createEditorState(initial)
    this.checkpointDocument = cloneDoclingDocument(this.stateValue.document)
  }

  get document(): DoclingDocument {
    return this.stateValue.document
  }

  get index(): DoclingIndex {
    return this.stateValue.index
  }

  get state(): DoclingEditorState {
    return this.stateValue
  }

  get canUndo(): boolean {
    return this.past.length > 0
  }

  get canRedo(): boolean {
    return this.future.length > 0
  }

  get hasChanges(): boolean {
    return this.stateValue.revision !== this.stateValue.checkpointRevision
  }

  apply(input: DoclingEditOperation | DoclingCommand): DoclingDocument {
    const command = isCommand(input) ? input : createDoclingCommand(input, this.stateValue)
    this.stateValue = command.apply(this.stateValue)
    this.past.push(command)
    this.future = []
    return this.stateValue.document
  }

  undo(): DoclingDocument {
    const command = this.past.pop()
    if (!command) {
      throw new DoclingEditError('Nothing to undo')
    }
    this.stateValue = command.undo(this.stateValue)
    this.future.push(command)
    return this.stateValue.document
  }

  redo(): DoclingDocument {
    const command = this.future.pop()
    if (!command) {
      throw new DoclingEditError('Nothing to redo')
    }
    this.stateValue = command.apply(this.stateValue)
    this.past.push(command)
    return this.stateValue.document
  }

  reset(): DoclingDocument {
    this.stateValue = createEditorState(this.checkpointDocument)
    this.past = []
    this.future = []
    return this.stateValue.document
  }

  checkpoint(): DoclingDocument {
    this.checkpointDocument = cloneDoclingDocument(this.stateValue.document)
    this.stateValue = {
      ...this.stateValue,
      checkpointRevision: this.stateValue.revision,
    }
    this.past = []
    this.future = []
    return this.stateValue.document
  }

  replaceDocument(next: DoclingDocument | unknown): DoclingDocument {
    this.stateValue = createEditorState(next)
    this.checkpointDocument = cloneDoclingDocument(this.stateValue.document)
    this.past = []
    this.future = []
    return this.stateValue.document
  }

  exportDocument(): DoclingDocument {
    return exportDoclingDocument(this.stateValue.document)
  }

  resolveNodeId(ref: string): DoclingNodeId {
    if (!this.stateValue.index.itemsByRef.has(ref)) {
      throw new DoclingEditError(`Item not found: ${ref}`)
    }
    return ref
  }

  resolveRef(nodeId: DoclingNodeId): string {
    return this.resolveNodeId(nodeId)
  }
}

export function createEditorState(initial: DoclingDocument | unknown): DoclingEditorState {
  const parsed = coerceEditorDocument(initial)
  return {
    document: parsed,
    index: buildDoclingIndex(parsed),
    revision: 0,
    checkpointRevision: 0,
  }
}

function coerceEditorDocument(initial: DoclingDocument | unknown): DoclingDocument {
  try {
    return parseDoclingDocument(initial)
  } catch (error) {
    if (typeof initial !== 'object' || initial === null) {
      throw error
    }
    return validateDraftDoclingDocument(structuredClone(initial) as DoclingDocument)
  }
}

export function createDoclingCommand(
  operation: DoclingEditOperation,
  state?: DoclingEditorState,
): DoclingCommand {
  switch (operation.type) {
    case 'edit-text':
      return new EditTextCommand(operation.itemRef, operation.text)
    case 'move-item':
      return new MoveItemCommand(operation.itemRef, operation.targetParentRef, operation.targetIndex)
    case 'reparent-item': {
      const targetIndex = state
        ? getParentChildren(state.document, operation.targetParentRef).length
        : undefined
      return new MoveItemCommand(operation.itemRef, operation.targetParentRef, targetIndex)
    }
    case 'merge-texts':
      return new MergeTextsCommand(operation.leadingRef, operation.trailingRef, operation.spacer)
    case 'split-text':
      return new SplitTextCommand(operation.itemRef, operation.offset)
    case 'insert-text':
      return new InsertTextCommand(operation)
    case 'create-group':
      return new CreateGroupCommand(operation)
    case 'delete-item':
      return new DeleteItemCommand(operation.itemRef)
    default: {
      const exhaustive: never = operation
      return exhaustive
    }
  }
}

export function applyDoclingEditOperation(
  doc: DoclingDocument,
  operation: DoclingEditOperation,
): DoclingDocument {
  switch (operation.type) {
    case 'edit-text':
      return editDoclingText(doc, operation.itemRef, operation.text)
    case 'move-item':
      return moveDoclingItem(doc, operation.itemRef, operation.targetParentRef, operation.targetIndex)
    case 'reparent-item':
      return reparentDoclingItem(doc, operation.itemRef, operation.targetParentRef)
    case 'merge-texts':
      return mergeAdjacentDoclingTexts(doc, operation.leadingRef, operation.trailingRef, operation.spacer)
    case 'split-text':
      return splitDoclingText(doc, operation.itemRef, operation.offset)
    case 'insert-text':
      return insertDoclingText(doc, operation)
    case 'create-group':
      return createDoclingGroup(doc, operation)
    case 'delete-item':
      return deleteDoclingItem(doc, operation.itemRef)
    default: {
      const exhaustive: never = operation
      return exhaustive
    }
  }
}

class EditTextCommand implements DoclingCommand {
  readonly type = 'edit-text'
  private previousSnapshot: DoclingTextItem | null = null

  constructor(
    private readonly itemRef: string,
    private readonly nextText: string,
  ) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    if (!this.previousSnapshot) {
      this.previousSnapshot = snapshotTextItem(state.document, this.itemRef)
    }
    return replaceDocument(
      state,
      editDoclingText(state.document, this.itemRef, this.nextText, { normalizeRefs: false }),
    )
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    return replaceDocument(state, restoreTextSnapshot(state.document, this.previousSnapshot as DoclingTextItem))
  }
}

class MoveItemCommand implements DoclingCommand {
  readonly type = 'move-item'
  private sourceParentRef: string | null = null
  private sourceIndex: number | null = null

  constructor(
    private readonly itemRef: string,
    private readonly targetParentRef: string,
    private readonly targetIndex?: number,
  ) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    if (this.sourceParentRef == null || this.sourceIndex == null) {
      const position = locateItem(state.document, this.itemRef)
      this.sourceParentRef = position.parentRef
      this.sourceIndex = position.index
    }
    return replaceDocument(
      state,
      moveDoclingItem(
        state.document,
        this.itemRef,
        this.targetParentRef,
        this.targetIndex,
        { normalizeRefs: false },
      ),
    )
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    return replaceDocument(
      state,
      moveDoclingItem(
        state.document,
        this.itemRef,
        this.sourceParentRef as string,
        this.sourceIndex as number,
        { normalizeRefs: false },
      ),
    )
  }
}

class MergeTextsCommand implements DoclingCommand {
  readonly type = 'merge-texts'
  private leadingSnapshot: DoclingTextItem | null = null
  private trailingSnapshot: DoclingTextItem | null = null
  private parentRef: string | null = null
  private trailingSiblingIndex: number | null = null
  private trailingCollectionIndex: number | null = null

  constructor(
    private readonly leadingRef: string,
    private readonly trailingRef: string,
    private readonly spacer = ' ',
  ) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    if (!this.leadingSnapshot) {
      this.leadingSnapshot = snapshotTextItem(state.document, this.leadingRef)
      this.trailingSnapshot = snapshotTextItem(state.document, this.trailingRef)
      const location = locateItem(state.document, this.trailingRef)
      this.parentRef = location.parentRef
      this.trailingSiblingIndex = location.index
      this.trailingCollectionIndex = locateCollectionEntry(state.document, this.trailingRef).index
    }
    return replaceDocument(
      state,
      mergeAdjacentDoclingTexts(
        state.document,
        this.leadingRef,
        this.trailingRef,
        this.spacer,
        { normalizeRefs: false },
      ),
    )
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    let next = restoreTextSnapshot(state.document, this.leadingSnapshot as DoclingTextItem)
    next = insertCollectionItem(
      next,
      'texts',
      this.trailingCollectionIndex as number,
      this.trailingSnapshot as DoclingTextItem,
    )
    next = insertChildRef(next, this.parentRef as string, this.trailingSiblingIndex as number, this.trailingRef)
    return replaceDocument(state, next)
  }
}

class SplitTextCommand implements DoclingCommand {
  readonly type = 'split-text'
  private originalSnapshot: DoclingTextItem | null = null
  private createdRef: string | null = null

  constructor(
    private readonly itemRef: string,
    private readonly offset: number,
  ) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    if (!this.originalSnapshot) {
      this.originalSnapshot = snapshotTextItem(state.document, this.itemRef)
    }

    const next = splitDoclingText(state.document, this.itemRef, this.offset, { normalizeRefs: false })
    if (!this.createdRef) {
      const location = locateItem(next, this.itemRef)
      const siblings = getParentChildren(next, location.parentRef)
      this.createdRef = siblings[location.index + 1]?.$ref ?? null
      if (!this.createdRef) {
        throw new DoclingEditError(`Split did not create a trailing text item for ${this.itemRef}`)
      }
    }
    return replaceDocument(state, next)
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    let next = deleteDoclingItem(state.document, this.createdRef as string, { normalizeRefs: false })
    next = restoreTextSnapshot(next, this.originalSnapshot as DoclingTextItem)
    return replaceDocument(state, next)
  }
}

class InsertTextCommand implements DoclingCommand {
  readonly type = 'insert-text'
  private createdRef: string | null = null

  constructor(private readonly options: DoclingInsertTextOptions) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    const next = insertDoclingText(state.document, this.options, { normalizeRefs: false })
    if (!this.createdRef) {
      const siblings = getParentChildren(next, this.options.parentRef)
      const index = resolveInsertionIndex(siblings, this.options.index)
      this.createdRef = siblings[index]?.$ref ?? null
      if (!this.createdRef) {
        throw new DoclingEditError(`Insert did not create a text item under ${this.options.parentRef}`)
      }
    }
    return replaceDocument(state, next)
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    return replaceDocument(
      state,
      deleteDoclingItem(state.document, this.createdRef as string, { normalizeRefs: false }),
    )
  }
}

class CreateGroupCommand implements DoclingCommand {
  readonly type = 'create-group'
  private createdRef: string | null = null

  constructor(private readonly options: DoclingCreateGroupOptions) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    const next = createDoclingGroup(state.document, this.options, { normalizeRefs: false })
    if (!this.createdRef) {
      const siblings = getParentChildren(next, this.options.parentRef)
      const index = resolveInsertionIndex(siblings, this.options.index)
      this.createdRef = siblings[index]?.$ref ?? null
      if (!this.createdRef) {
        throw new DoclingEditError(`Create-group did not create a group under ${this.options.parentRef}`)
      }
    }
    return replaceDocument(state, next)
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    return replaceDocument(
      state,
      deleteDoclingItem(state.document, this.createdRef as string, { normalizeRefs: false }),
    )
  }
}

class DeleteItemCommand implements DoclingCommand {
  readonly type = 'delete-item'
  private snapshot: SubtreeSnapshot | null = null

  constructor(private readonly itemRef: string) {}

  apply(state: DoclingEditorState): DoclingEditorState {
    if (!this.snapshot) {
      this.snapshot = captureSubtreeSnapshot(state.document, this.itemRef)
    }
    return replaceDocument(
      state,
      deleteDoclingItem(state.document, this.itemRef, { normalizeRefs: false }),
    )
  }

  undo(state: DoclingEditorState): DoclingEditorState {
    return replaceDocument(state, restoreSubtreeSnapshot(state.document, this.snapshot as SubtreeSnapshot))
  }
}

function replaceDocument(state: DoclingEditorState, document: DoclingDocument): DoclingEditorState {
  return {
    ...state,
    document,
    index: buildDoclingIndex(document),
    revision: state.revision + 1,
  }
}

function snapshotTextItem(doc: DoclingDocument, ref: string): DoclingTextItem {
  const item = getDoclingItem(doc, ref)
  if (!item || !('text' in item)) {
    throw new DoclingEditError(`Item ${ref} is not a text item`)
  }
  return structuredClone(item as DoclingTextItem)
}

function restoreTextSnapshot(doc: DoclingDocument, snapshot: DoclingTextItem): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const item = getDoclingItem(next, snapshot.self_ref)
  if (!item || !('text' in item)) {
    throw new DoclingEditError(`Cannot restore missing text item ${snapshot.self_ref}`)
  }
  Object.assign(item, structuredClone(snapshot))
  return parseDoclingDocument(next)
}

function locateItem(doc: DoclingDocument, ref: string): { parentRef: string; index: number } {
  const item = getDoclingItem(doc, ref)
  if (!item) {
    throw new DoclingEditError(`Item not found: ${ref}`)
  }
  const parentRef = item.parent?.$ref ?? '#/body'
  const siblings = getParentChildren(doc, parentRef)
  const index = siblings.findIndex((child) => child.$ref === ref)
  if (index === -1) {
    throw new DoclingEditError(`Parent ${parentRef} does not contain ${ref}`)
  }
  return { parentRef, index }
}

function locateCollectionEntry(doc: DoclingDocument, ref: string): { key: ItemCollectionKey; index: number } {
  const entry = buildDoclingIndex(doc).collectionEntriesByRef.get(ref)
  if (!entry) {
    throw new DoclingEditError(`Collection entry not found for ${ref}`)
  }
  return entry
}

function getParentChildren(doc: DoclingDocument, parentRef: string): DoclingRef[] {
  if (parentRef === '#/body') {
    return doc.body.children
  }
  if (parentRef === '#/furniture') {
    return doc.furniture.children
  }

  const parent = getDoclingItem(doc, parentRef)
  if (!parent?.children) {
    throw new DoclingEditError(`Parent not found or not editable: ${parentRef}`)
  }
  return parent.children
}

function resolveInsertionIndex(children: readonly DoclingRef[], requestedIndex: number | undefined): number {
  return requestedIndex == null ? children.length - 1 : requestedIndex
}

function insertCollectionItem(
  doc: DoclingDocument,
  key: ItemCollectionKey,
  index: number,
  item: DoclingNode,
): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const collection = next[key] as DoclingNode[]
  collection.splice(Math.min(index, collection.length), 0, structuredClone(item))
  return parseDoclingDocument(next)
}

function insertChildRef(doc: DoclingDocument, parentRef: string, index: number, childRef: string): DoclingDocument {
  const next = cloneDoclingDocument(doc)
  const children = getParentChildren(next, parentRef)
  children.splice(Math.min(index, children.length), 0, { $ref: childRef })
  return parseDoclingDocument(next)
}

function captureSubtreeSnapshot(doc: DoclingDocument, rootRef: string): SubtreeSnapshot {
  const index = buildDoclingIndex(doc)
  const rootEntry = index.itemsByRef.get(rootRef)
  if (!rootEntry) {
    throw new DoclingEditError(`Item not found: ${rootRef}`)
  }
  const rootItem = rootEntry.item
  const parentRef = rootItem.parent?.$ref
  if (!parentRef) {
    throw new DoclingEditError(`Cannot delete root item ${rootRef}`)
  }
  const parentIndex = locateItem(doc, rootRef).index
  const refs: string[] = []
  const queue = [rootRef]
  while (queue.length > 0) {
    const currentRef = queue.shift() as string
    refs.push(currentRef)
    for (const child of index.childrenByParentRef.get(currentRef) ?? []) {
      queue.push(child.$ref)
    }
  }

  const items = refs
    .map((ref) => {
      const entry = index.collectionEntriesByRef.get(ref)
      if (!entry) {
        return null
      }
      return {
        collectionKey: entry.key,
        collectionIndex: entry.index,
        item: structuredClone(index.itemsByRef.get(ref)?.item as DoclingNode),
      } satisfies ItemSnapshot
    })
    .filter((value): value is ItemSnapshot => value !== null)

  return {
    rootRef,
    parentRef,
    parentIndex,
    items,
  }
}

function restoreSubtreeSnapshot(doc: DoclingDocument, snapshot: SubtreeSnapshot): DoclingDocument {
  let next = cloneDoclingDocument(doc)
  for (const key of ITEM_COLLECTION_KEYS) {
    const entries = snapshot.items
      .filter((item) => item.collectionKey === key)
      .sort((left, right) => left.collectionIndex - right.collectionIndex)
    if (entries.length === 0) {
      continue
    }
    const collection = next[key] as DoclingNode[]
    let offset = 0
    for (const entry of entries) {
      collection.splice(Math.min(entry.collectionIndex + offset, collection.length), 0, structuredClone(entry.item))
      offset += 1
    }
  }

  const children = getParentChildren(next, snapshot.parentRef)
  children.splice(Math.min(snapshot.parentIndex, children.length), 0, { $ref: snapshot.rootRef })
  return parseDoclingDocument(next)
}

function isCommand(value: DoclingEditOperation | DoclingCommand): value is DoclingCommand {
  return 'apply' in value && 'undo' in value
}
