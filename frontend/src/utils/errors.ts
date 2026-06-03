/**
 * Centralised utility to extract a human-readable string message from
 * various API error formats, preventing React render crashes from objects in JSX.
 */
export function extractErrorMessage(error: any): string {
  if (!error) return 'An unknown error occurred.'

  // 1. Plain string error
  if (typeof error === 'string') {
    return error
  }

  // 2. Axios response error with custom body details
  if (error.response && error.response.data) {
    const data = error.response.data

    // 2.1. FastAPI/Pydantic validation detail array
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((err: any) => {
            if (err && typeof err === 'object') {
              const field = err.loc ? err.loc[err.loc.length - 1] : ''
              const fieldName = typeof field === 'string'
                ? field.charAt(0).toUpperCase() + field.slice(1)
                : String(field)
              let msg = err.msg || 'Invalid value'
              if (msg.startsWith('Value error, ')) {
                msg = msg.slice('Value error, '.length)
              }
              const prefix = field && field !== 'body' ? `${fieldName}: ` : ''
              return `${prefix}${msg}`
            }
            return String(err)
        })
        .join('; ')
    }

    // 2.2. Standard FastAPI HTTPException detail string
    if (typeof data.detail === 'string') {
      return data.detail
    }

    // 2.3. Common standard message property
    if (typeof data.message === 'string') {
      return data.message
    }

    // 2.4. JSON serializable object error fallback
    try {
      return JSON.stringify(data)
    } catch {
      return 'Failed to parse error response data.'
    }
  }

  // 3. Native Javascript Error object
  if (error instanceof Error) {
    return error.message
  }
  if (error.message && typeof error.message === 'string') {
    return error.message
  }

  // 4. Raw fallback object serialization
  try {
    return JSON.stringify(error)
  } catch {
    return String(error)
  }
}
