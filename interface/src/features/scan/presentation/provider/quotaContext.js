import { createContext } from 'react'

export const QuotaContext = createContext({ quota: null, refresh: () => {} })
