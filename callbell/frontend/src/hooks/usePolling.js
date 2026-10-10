import { useCallback, useEffect, useRef, useState } from 'react'

// Calls fn() now and every `ms`. Returns { data, error, refresh }.
export function usePolling(fn, ms = 2000, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const refresh = useCallback(async () => {
    try {
      setData(await fnRef.current())
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, ms)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, refresh, ...deps])

  return { data, error, refresh }
}
