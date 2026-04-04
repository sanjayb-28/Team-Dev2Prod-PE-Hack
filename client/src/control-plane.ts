import type {
  ClusterEventRecord,
  ClusterSnapshotEvent,
  ClusterStatus,
  ExperimentRequestPayload,
  ResourceGroupName,
  ResourceKindName,
  ResourceLogRecord,
  ResourceRecord,
  ResourceSnapshot,
} from './types'

interface ApiEnvelope<T> {
  data: T
}

const controlPlaneUrl = (import.meta.env.VITE_CONTROL_PLANE_URL ?? '').replace(
  /\/$/,
  '',
)

function buildUrl(path: string) {
  return controlPlaneUrl ? `${controlPlaneUrl}${path}` : path
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(buildUrl(path), {
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`)
  }

  return (await response.json()) as T
}

async function sendJson<T>(path: string, method: 'POST', body?: object): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  const payload = (await response.json()) as T & { error?: { message?: string } }
  if (!response.ok) {
    throw new Error(payload.error?.message ?? `Request failed with ${response.status}`)
  }

  return payload
}

export function fetchClusterStatus() {
  return fetchJson<ApiEnvelope<ClusterStatus>>('/api/cluster/status')
}

export function fetchResourceSnapshot() {
  return fetchJson<ApiEnvelope<ResourceSnapshot>>('/api/resources')
}

export function fetchResourceDetail(kind: ResourceKindName, name: string) {
  return fetchJson<ApiEnvelope<ResourceRecord>>(`/api/resources/${kind}/${name}`)
}

export function fetchResourceEvents(kind: ResourceKindName, name: string) {
  return fetchJson<ApiEnvelope<ClusterEventRecord[]>>(
    `/api/resources/${kind}/${name}/events`,
  )
}

export function fetchResourceLogs(kind: ResourceKindName, name: string) {
  return fetchJson<ApiEnvelope<ResourceLogRecord>>(`/api/resources/${kind}/${name}/logs`)
}

export function createExperiment(payload: ExperimentRequestPayload) {
  return sendJson<ApiEnvelope<ResourceRecord>>('/api/experiments', 'POST', payload)
}

export function cancelExperiment(name: string) {
  return sendJson<ApiEnvelope<ResourceRecord>>(`/api/experiments/${name}/cancel`, 'POST')
}

export function openClusterStream(
  onSnapshot: (snapshot: ClusterSnapshotEvent) => void,
  onError: () => void,
) {
  const source = new EventSource(buildUrl('/api/stream'))

  source.addEventListener('cluster_snapshot', (event) => {
    if (!(event instanceof MessageEvent)) {
      return
    }

    try {
      onSnapshot(JSON.parse(event.data) as ClusterSnapshotEvent)
    } catch {
      onError()
    }
  })

  source.onerror = () => {
    onError()
  }

  return source
}

export const resourceGroupMeta: Array<{
  group: ResourceGroupName
  kind: ResourceKindName
  label: string
  emptyLabel: string
}> = [
  {
    group: 'deployments',
    kind: 'deployment',
    label: 'Deployments',
    emptyLabel: 'No deployments in scope.',
  },
  {
    group: 'pods',
    kind: 'pod',
    label: 'Pods',
    emptyLabel: 'No pods in scope.',
  },
  {
    group: 'services',
    kind: 'service',
    label: 'Services',
    emptyLabel: 'No services in scope.',
  },
  {
    group: 'replicaSets',
    kind: 'replicaset',
    label: 'Replica sets',
    emptyLabel: 'No replica sets in scope.',
  },
  {
    group: 'experiments',
    kind: 'experiment',
    label: 'Experiments',
    emptyLabel: 'No active fault experiments yet.',
  },
]
