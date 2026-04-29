import type { RouteLocationRaw } from 'vue-router'

/**
 * One segment in a breadcrumb.
 *
 * - `LinkCrumb` renders as a `<RouterLink>` to `to`.
 * - `LeafCrumb` renders as a non-clickable label with `aria-current="page"`.
 *   The leaf is always the last segment; the rendering component refuses
 *   to render a leaf in a non-final position.
 */
export type LinkCrumb = { kind: 'link'; label: string; to: RouteLocationRaw }
export type LeafCrumb = { kind: 'leaf'; label: string }
export type Crumb = LinkCrumb | LeafCrumb
