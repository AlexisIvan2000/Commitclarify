import { useContext } from 'react'
import { QuotaContext } from './quotaContext'

export default function useQuota() {
  return useContext(QuotaContext)
}
