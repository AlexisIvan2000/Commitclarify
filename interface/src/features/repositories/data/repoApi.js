import { requestJson } from '@core/network/apiClient'

export function fetchRepos() {
  return requestJson('/repos/')
}
