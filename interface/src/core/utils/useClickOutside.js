import { useEffect } from 'react'

export default function useClickOutside(ref, callback) {
  useEffect(() => {
    function handle(event) {
      if (ref.current && !ref.current.contains(event.target)) callback()
    }

    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [ref, callback])
}
