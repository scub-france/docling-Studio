/**
 * Design-token access for canvas drawing.
 *
 * A canvas cannot use `var(--token)`, so the overlays read the resolved
 * values of the tokens defined in app/App.vue. The computed style is read
 * once per reader, so a draw creates one reader and asks it for every token
 * it needs. Values come back trimmed; an unknown token (or jsdom, which does
 * not resolve the theme) gives an empty string, which the canvas ignores.
 */
export type CssTokenReader = (name: string) => string

export function createCssTokenReader(el: Element): CssTokenReader {
  const styles = window.getComputedStyle(el)
  return (name) => styles.getPropertyValue(name).trim()
}
