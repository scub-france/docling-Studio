import type { RouteLocationNormalizedLoaded } from 'vue-router'

/** What the dev route badge shows: the route's name, else its path. */
export function routeLabel(route: Pick<RouteLocationNormalizedLoaded, 'name' | 'path'>): string {
  return route.name ? String(route.name) : route.path
}
