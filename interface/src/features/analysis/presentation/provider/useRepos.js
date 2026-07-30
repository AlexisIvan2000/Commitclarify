import { useCallback } from 'react'
import useAsyncData from '@core/utils/useAsyncData'
import { fetchRepos } from '../../data/repoApi'

export default function useRepos() {
  const load = useCallback(() => fetchRepos(), [])
  const { data, loading, error, reload } = useAsyncData(load)

  return { repos: data || [], loading, error, reload }
}
