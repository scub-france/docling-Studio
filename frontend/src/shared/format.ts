export function formatSize(bytes: number | null | undefined): string {
  if (!bytes) return ''
  const mb = bytes / (1024 * 1024)
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`
}

export function formatRelativeTime(iso: string | null | undefined, locale = 'fr'): string {
  if (!iso) return '—'
  const diffMs = Date.now() - new Date(iso).getTime()
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  const abs = Math.abs(diffMs)
  const dir = diffMs >= 0 ? -1 : 1

  if (abs < 60_000) return rtf.format(dir * Math.round(abs / 1_000), 'second')
  if (abs < 3_600_000) return rtf.format(dir * Math.round(abs / 60_000), 'minute')
  if (abs < 86_400_000) return rtf.format(dir * Math.round(abs / 3_600_000), 'hour')
  if (abs < 30 * 86_400_000) return rtf.format(dir * Math.round(abs / 86_400_000), 'day')
  return rtf.format(dir * Math.round(abs / (30 * 86_400_000)), 'month')
}
