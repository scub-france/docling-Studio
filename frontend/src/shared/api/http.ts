interface FetchOptions extends RequestInit {
  skipContentType?: boolean
}

export async function apiFetch<T = unknown>(url: string, options: FetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }

  if (!options.skipContentType) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail ? `${response.status}: ${detail}` : `API error: ${response.status}`)
  }
  if (response.status === 204) return null as T
  return response.json() as Promise<T>
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) return null
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((e: { loc?: unknown[]; msg?: string }) => {
          const loc = Array.isArray(e.loc) ? e.loc.join('.') : ''
          return loc ? `${loc}: ${e.msg ?? ''}` : (e.msg ?? '')
        })
        .filter(Boolean)
        .join('; ')
    }
    return null
  } catch {
    return null
  }
}
