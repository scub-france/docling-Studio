import { computed, ref, type ComputedRef, type InjectionKey } from 'vue'

/**
 * An accordion of foldable sections that remembers what the viewer folded.
 *
 * The page that owns the sections creates one and `provide`s it under
 * `ACCORDION_KEY`; each `AccordionSection` registers itself and reads its
 * open state from it. That keeps the sections independent of who renders
 * them: a feature can contribute sections to another feature's page.
 *
 * The folded ids are kept in browser storage, per viewer. Storage that is
 * missing, blocked or holds anything unexpected just falls back to the
 * defaults.
 */
export interface Accordion {
  isOpen(id: string): boolean
  toggle(id: string): void
  register(id: string): void
  unregister(id: string): void
  /** True when every registered section is folded. */
  allClosed: ComputedRef<boolean>
  /** Fold every section, or unfold them all when they all are folded. */
  toggleAll(): void
}

export const ACCORDION_KEY: InjectionKey<Accordion> = Symbol('accordion')

type KeyValueStorage = Pick<Storage, 'getItem' | 'setItem'>

export interface AccordionOptions {
  storageKey: string
  /** Sections folded until the viewer says otherwise. */
  defaultClosed?: readonly string[]
  /** Where to keep the folded ids; the browser's localStorage by default. */
  storage?: KeyValueStorage | null
}

function browserStorage(): KeyValueStorage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function readClosed(storage: KeyValueStorage | null, key: string): string[] | null {
  try {
    const raw = storage?.getItem(key)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (Array.isArray(parsed) && parsed.every((id) => typeof id === 'string')) return parsed
    return null
  } catch {
    return null
  }
}

export function createAccordion(options: AccordionOptions): Accordion {
  const storage = options.storage === undefined ? browserStorage() : options.storage
  const closed = ref<ReadonlySet<string>>(
    new Set(readClosed(storage, options.storageKey) ?? options.defaultClosed ?? []),
  )
  const ids = ref<string[]>([])

  function setClosed(next: ReadonlySet<string>): void {
    closed.value = next
    try {
      storage?.setItem(options.storageKey, JSON.stringify([...next]))
    } catch {
      // Storage full or blocked: the fold still applies for this visit.
    }
  }

  const allClosed = computed(
    () => ids.value.length > 0 && ids.value.every((id) => closed.value.has(id)),
  )

  return {
    isOpen: (id) => !closed.value.has(id),
    toggle(id) {
      const next = new Set(closed.value)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      setClosed(next)
    },
    register(id) {
      if (!ids.value.includes(id)) ids.value = [...ids.value, id]
    },
    unregister(id) {
      ids.value = ids.value.filter((known) => known !== id)
    },
    allClosed,
    toggleAll() {
      setClosed(allClosed.value ? new Set() : new Set([...closed.value, ...ids.value]))
    },
  }
}
