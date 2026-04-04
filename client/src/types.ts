export type ResourceGroupName =
  | 'deployments'
  | 'replicaSets'
  | 'pods'
  | 'services'
  | 'experiments'

export type ResourceKindName =
  | 'deployment'
  | 'replicaset'
  | 'pod'
  | 'service'
  | 'experiment'

export type ExperimentTypeName = 'pod-kill' | 'network-latency' | 'cpu-stress'

export interface HealthBlock {
  status: string
  message?: string
}

export interface WorkloadScope {
  deploymentName: string
  serviceName: string
  podPrefix: string
}

export interface ClusterStatus {
  clusterName: string
  namespace: string
  provider: string
  mode: string
  scopeLocked: boolean
  controlPlane: HealthBlock
  workload: HealthBlock
  chaosMesh: HealthBlock
  workloadScope: WorkloadScope
}

export interface ResourceRecord {
  kind: string
  name: string
  status?: string
  updatedAt?: string | null
  [key: string]: unknown
}

export interface ClusterEventRecord {
  name?: string
  type?: string
  reason?: string
  message?: string
  resourceKind?: string
  resourceName?: string
  timestamp?: string | null
}

export interface ResourceLogEntry {
  line: string
}

export interface ResourceLogRecord {
  kind?: string
  name?: string
  entries: ResourceLogEntry[]
  note?: string
}

export interface ResourceSnapshot {
  mode: string
  namespace: string
  resources: Record<ResourceGroupName, ResourceRecord[]>
  events: ClusterEventRecord[]
}

export interface ClusterSnapshotEvent {
  status: ClusterStatus
  resources: ResourceSnapshot
}

export interface ExperimentRequestPayload {
  type: ExperimentTypeName
  target: {
    kind: string
    name: string
  }
  durationSeconds: number
  parameters: Record<string, unknown>
}
