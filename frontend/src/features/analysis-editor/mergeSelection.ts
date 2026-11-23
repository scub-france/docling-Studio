/** Selection of the elements to merge, as pure updates of the selected ids. */

/** Add the id when absent, remove it when present. */
export function toggleSelectedId(selection: string[], id: string): string[] {
  return selection.includes(id)
    ? selection.filter((selected) => selected !== id)
    : [...selection, id]
}

/**
 * Toggle a group at once: deselect it when every id is already selected,
 * otherwise add the missing ones. An empty group leaves the selection as is.
 */
export function toggleSelectedIds(selection: string[], ids: string[]): string[] {
  if (!ids.length) return selection
  const allSelected = ids.every((id) => selection.includes(id))
  return allSelected
    ? selection.filter((id) => !ids.includes(id))
    : [...new Set([...selection, ...ids])]
}
