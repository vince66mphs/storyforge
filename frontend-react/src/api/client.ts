export class ApiError extends Error {
  status: number
  errorType: string | null
  service: string | null

  constructor(status: number, detail: string, errorType: string | null = null, service: string | null = null) {
    super(detail)
    this.status = status
    this.errorType = errorType
    this.service = service
  }

  get isServiceUnavailable() {
    return this.errorType === 'service_unavailable' || this.status === 503
  }

  get isTimeout() {
    return this.errorType === 'service_timeout' || this.status === 504
  }
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: {},
  }
  if (body !== undefined) {
    (opts.headers as Record<string, string>)['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }

  let res: Response
  try {
    res = await fetch(path, opts)
  } catch {
    throw new ApiError(0, 'Network error — server may be down', 'network_error')
  }

  if (res.status === 204) return null as T
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(
      res.status,
      err.detail || `HTTP ${res.status}`,
      err.error_type || null,
      err.service || null,
    )
  }
  return res.json()
}
