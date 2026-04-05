import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from 'react'

import {
  cancelExperiment,
  createExperiment,
  fetchClusterStatus,
  fetchResourceDetail,
  fetchResourceEvents,
  fetchResourceLogs,
  fetchResourceSnapshot,
  openClusterStream,
  resourceGroupMeta,
} from '../control-plane'
import type {
  ClusterEventRecord,
  ClusterStatus,
  ExperimentTypeName,
  ResourceGroupName,
  ResourceKindName,
  ResourceLogRecord,
  ResourceRecord,
  ResourceSnapshot,
} from '../types'

type RequestState = 'loading' | 'ready' | 'error'
type ConnectionState = 'connecting' | 'live' | 'offline'
type FaultActionState = 'idle' | 'running' | 'error' | 'success'

const EVIDENCE_EVENT_LIMIT = 4
const NAMESPACE_EVENT_LIMIT = 5
const LOG_LINE_LIMIT = 12

const experimentActions: Array<{
  type: ExperimentTypeName
  label: string
  helper: string
  impact: string
  durationSeconds: number
  parameters: Record<string, unknown>
}> = [
  {
    type: 'pod-kill',
    label: 'Pod restart',
    helper: 'Temporarily remove one running pod so you can watch the platform replace it.',
    impact: 'One pod is removed so Kubernetes has to replace it.',
    durationSeconds: 30,
    parameters: {},
  },
  {
    type: 'network-latency',
    label: 'Network latency',
    helper: 'Slow requests on purpose so you can see how the app behaves when the network drags.',
    impact: 'Requests become slower so you can read degradation clearly.',
    durationSeconds: 60,
    parameters: { latencyMs: 120 },
  },
  {
    type: 'cpu-stress',
    label: 'CPU pressure',
    helper: 'Push extra CPU load onto the workload without disturbing the rest of the namespace.',
    impact: 'One pod is put under compute pressure while the service tries to stay live.',
    durationSeconds: 60,
    parameters: { cpuLoad: 80 },
  },
]

function InfoHint({ label }: { label: string }) {
  const [open, setOpen] = useState(false)

  return (
    <span
      className="info-hint"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="info-hint__trigger"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        i
      </button>
      {open ? <span className="info-hint__panel">{label}</span> : null}
    </span>
  )
}

function formatExperimentType(value: unknown) {
  const experimentType = String(value ?? 'fault-run')
  if (experimentType === 'pod-kill') {
    return 'Pod restart'
  }
  if (experimentType === 'network-latency') {
    return 'Network latency'
  }
  if (experimentType === 'cpu-stress') {
    return 'CPU pressure'
  }
  return formatStatusText(experimentType)
}

function ensureSelection(
  snapshot: ResourceSnapshot,
  preferredGroup: ResourceGroupName,
  preferredName: string | null,
) {
  const currentGroupItems = snapshot.resources[preferredGroup]
  if (preferredName && currentGroupItems.some((item) => item.name === preferredName)) {
    return { group: preferredGroup, name: preferredName }
  }

  if (currentGroupItems.length > 0) {
    return { group: preferredGroup, name: currentGroupItems[0].name }
  }

  for (const { group } of resourceGroupMeta) {
    const items = snapshot.resources[group]
    if (items.length > 0) {
      return { group, name: items[0].name }
    }
  }

  return { group: preferredGroup, name: null }
}

function formatStatusText(status: string) {
  return status.replace(/([A-Z])/g, ' $1').replace(/^./, (value) => value.toUpperCase())
}

function buildEvidenceEvents(resource: ResourceRecord | null, events: ClusterEventRecord[]) {
  if (resource?.kind !== 'experiment') {
    return events.slice(0, 5)
  }

  const highlightedReasons = new Set(['Applied', 'Started', 'Recovered', 'TimeUp'])
  const preferredEvents = events.filter((event) =>
    highlightedReasons.has(String(event.reason ?? '')),
  )

  if (preferredEvents.length > 0) {
    return preferredEvents.slice(0, 5)
  }

  return events.slice(0, 5)
}

function describeEvidence(resource: ResourceRecord | null) {
  if (resource?.kind !== 'experiment') {
    return 'Recent events attached to the selected resource.'
  }

  if (resource.status === 'recovered') {
    return 'This run has finished. Review the events that applied the fault and confirmed recovery.'
  }

  return 'Cluster events that show how this fault is being applied right now.'
}

function describeEvidenceFeedState(inspectorState: RequestState) {
  if (inspectorState === 'loading') {
    return { label: 'Fetching', tone: 'warn' as const }
  }

  if (inspectorState === 'error') {
    return { label: 'Retrying', tone: 'bad' as const }
  }

  return { label: 'Live', tone: 'good' as const }
}

function describeLogs(resource: ResourceRecord | null, logs: ResourceLogRecord | null) {
  if (logs?.note) {
    return logs.note
  }

  if (resource?.kind === 'experiment' && resource.status === 'recovered') {
    return 'The latest workload logs from the recovery path appear here when they are available.'
  }

  if (resource?.kind === 'experiment') {
    return 'The latest workload logs for this active fault run appear here.'
  }

  return 'Recent lines from the selected resource.'
}

function describeEmptyLogs(resource: ResourceRecord | null) {
  if (resource?.kind === 'experiment' && resource.status === 'recovered') {
    return 'This run has already recovered, and there are no more workload lines to show.'
  }

  if (resource?.kind === 'experiment') {
    return 'The workload has not emitted any matching log lines yet.'
  }

  return 'No log lines are available right now.'
}

function buildInspectorNotice(resource: ResourceRecord | null, clusterStatus: ClusterStatus | null) {
  if (!resource || resource.kind !== 'experiment') {
    return null
  }

  const workloadLabel = clusterStatus?.workloadScope.displayName ?? 'the workload'
  if (resource.status === 'recovered') {
    return `This fault run has finished. Start a new run on ${workloadLabel} when you want another proof point.`
  }

  if (resource.status === 'running') {
    return 'This fault run is active. Watch the event timeline and workload logs for live impact signals.'
  }

  if (resource.status === 'pending') {
    return 'The cluster has accepted this fault run and is still applying it.'
  }

  return null
}

function formatUpdatedAt(value: unknown) {
  if (typeof value !== 'string' || !value) {
    return 'Waiting for the first cluster update'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Waiting for the first cluster update'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function buildResourceRows(resource: ResourceRecord | null) {
  if (!resource) {
    return []
  }

  const rows: Array<{ label: string; value: string }> = []
  const kind = String(resource.kind)

  if (kind === 'deployment' || kind === 'replicaSet') {
    rows.push({
      label: 'Readiness',
      value: `${resource.readyReplicas ?? 0} / ${resource.desiredReplicas ?? 0} ready`,
    })
  }

  if (kind === 'pod') {
    rows.push({
      label: 'Ready',
      value: resource.ready ? 'Yes' : 'No',
    })
    rows.push({
      label: 'Restarts',
      value: String(resource.restartCount ?? 0),
    })
  }

  if (kind === 'service') {
    rows.push({
      label: 'Type',
      value: String(resource.type ?? 'ClusterIP'),
    })
    rows.push({
      label: 'Cluster IP',
      value: String(resource.clusterIp ?? 'Not assigned'),
    })
    rows.push({
      label: 'Ports',
      value: Array.isArray(resource.ports)
        ? resource.ports.join(', ')
        : 'No ports published',
    })
  }

  if (kind === 'experiment') {
    rows.push({
      label: 'Fault',
      value: formatExperimentType(resource.type),
    })
    rows.push({
      label: 'Target',
      value: String(resource.target ?? 'Waiting for target'),
    })
    if (typeof resource.targetKind === 'string' && resource.targetKind) {
      rows.push({
        label: 'Scope',
        value: formatStatusText(resource.targetKind),
      })
    }
    if (typeof resource.latencyMs === 'number') {
      rows.push({
        label: 'Latency',
        value: `${resource.latencyMs} ms`,
      })
    }
    if (typeof resource.cpuLoad === 'number') {
      rows.push({
        label: 'CPU load',
        value: `${resource.cpuLoad}%`,
      })
    }
    if (typeof resource.durationSeconds === 'number') {
      rows.push({
        label: 'Duration',
        value: `${resource.durationSeconds} seconds`,
      })
    }
  }

  rows.push({
    label: 'Status',
    value: formatStatusText(String(resource.status ?? 'unknown')),
  })
  rows.push({
    label: 'Last change',
    value: formatUpdatedAt(resource.updatedAt),
  })

  return rows
}

function summarizeResource(resource: ResourceRecord) {
  switch (resource.kind) {
    case 'deployment':
    case 'replicaSet':
      return `${resource.readyReplicas ?? 0} of ${resource.desiredReplicas ?? 0} ready`
    case 'pod':
      return `${resource.ready ? 'Ready' : 'Not ready'} • ${resource.restartCount ?? 0} restarts`
    case 'service':
      return `${resource.type ?? 'ClusterIP'} • ${
        Array.isArray(resource.ports) ? resource.ports.join(', ') : 'No ports'
      }`
    case 'experiment':
      if (resource.type === 'network-latency' && typeof resource.latencyMs === 'number') {
        const duration =
          typeof resource.durationSeconds === 'number' ? ` for ${resource.durationSeconds}s` : ''
        return `${resource.latencyMs} ms delay${duration} • ${formatStatusText(String(resource.status ?? 'unknown'))}`
      }
      if (resource.type === 'cpu-stress' && typeof resource.cpuLoad === 'number') {
        const duration =
          typeof resource.durationSeconds === 'number' ? ` for ${resource.durationSeconds}s` : ''
        return `${resource.cpuLoad}% load${duration} • ${formatStatusText(String(resource.status ?? 'unknown'))}`
      }
      return `${formatStatusText(String(resource.status ?? 'unknown'))} • ${formatExperimentType(resource.type)}`
    default:
      return formatStatusText(String(resource.status ?? 'unknown'))
  }
}

function labelForKind(kind: string) {
  if (kind === 'pod') {
    return 'Pod'
  }
  if (kind === 'service') {
    return 'Service'
  }
  if (kind === 'deployment') {
    return 'Deployment'
  }
  if (kind === 'replicaSet') {
    return 'ReplicaSet'
  }
  if (kind === 'experiment') {
    return 'Experiment'
  }
  return formatStatusText(kind)
}

function asNumber(value: unknown) {
  return typeof value === 'number' ? value : 0
}

function getWorkloadDeployment(
  snapshot: ResourceSnapshot | null,
  clusterStatus: ClusterStatus | null,
) {
  if (!snapshot || !clusterStatus) {
    return null
  }

  return (
    snapshot.resources.deployments.find(
      (resource) => resource.name === clusterStatus.workloadScope.deploymentName,
    ) ?? null
  )
}

function getWorkloadPods(snapshot: ResourceSnapshot | null, clusterStatus: ClusterStatus | null) {
  if (!snapshot || !clusterStatus) {
    return []
  }

  return snapshot.resources.pods.filter((resource) =>
    resource.name.startsWith(clusterStatus.workloadScope.podPrefix),
  )
}

function getWorkloadService(
  snapshot: ResourceSnapshot | null,
  clusterStatus: ClusterStatus | null,
) {
  if (!snapshot || !clusterStatus) {
    return null
  }

  return (
    snapshot.resources.services.find(
      (resource) => resource.name === clusterStatus.workloadScope.serviceName,
    ) ?? null
  )
}

function getLatestWorkloadPod(pods: ResourceRecord[]) {
  return (
    pods
      .slice()
      .sort((left, right) =>
        String(left.updatedAt ?? '').localeCompare(String(right.updatedAt ?? '')),
      )
      .at(-1) ?? null
  )
}

function buildRolloutWatch(
  snapshot: ResourceSnapshot | null,
  clusterStatus: ClusterStatus | null,
  displayedResource: ResourceRecord | null,
) {
  const deployment = getWorkloadDeployment(snapshot, clusterStatus)
  const pods = getWorkloadPods(snapshot, clusterStatus)
  const latestPod = getLatestWorkloadPod(pods)

  if (!clusterStatus || !deployment) {
    return null
  }

  const desiredReplicas = asNumber(deployment.desiredReplicas)
  const readyReplicas = asNumber(deployment.readyReplicas)
  const readyPods = pods.filter((pod) => pod.ready).length
  const restartingPods = pods.filter((pod) => asNumber(pod.restartCount) > 0).length
  const rolloutActive =
    readyReplicas < desiredReplicas ||
    (pods.length > 0 && readyPods < pods.length) ||
    clusterStatus.workload.status === 'degraded'
  const watchingRecovery =
    displayedResource?.kind === 'experiment' &&
    (displayedResource.status === 'running' ||
      displayedResource.status === 'pending' ||
      displayedResource.status === 'recovered')

  let title = 'Workload is steady'
  let note = 'The locked deployment is ready for the next check.'

  if (rolloutActive) {
    title = 'Replacement is settling'
    note = 'The workload is still moving back toward a steady state.'
  } else if (displayedResource?.kind === 'experiment' && displayedResource.status === 'recovered') {
    title = 'Recovery is complete'
    note = 'The fault run has ended and the workload has settled again.'
  } else if (watchingRecovery) {
    title = 'Watching live recovery'
    note = 'The workload is holding while the current fault run is active.'
  }

  return {
    title,
    note,
    tone: rolloutActive ? 'warn' : 'good',
    rows: [
      {
        label: 'Deployment',
        value: `${readyReplicas} / ${desiredReplicas} ready`,
      },
      {
        label: 'Workload pods',
        value: pods.length > 0 ? `${readyPods} / ${pods.length} ready` : 'Waiting for pods',
      },
      {
        label: 'Latest pod',
        value: latestPod?.name ?? 'Waiting for a workload pod',
      },
      {
        label: 'Restarts',
        value:
          restartingPods === 0
            ? 'No recent restarts'
            : `${restartingPods} pod${restartingPods === 1 ? '' : 's'} restarting`,
      },
    ],
  }
}

function toneForStatus(status?: string) {
  if (status === 'healthy' || status === 'ready' || status === 'active' || status === 'running') {
    return 'good'
  }
  if (status === 'degraded' || status === 'pending') {
    return 'warn'
  }
  if (status === 'unreachable' || status === 'failed' || status === 'unknown') {
    return 'bad'
  }
  return 'quiet'
}

function matchesWorkloadScope(resource: ResourceRecord | null, clusterStatus: ClusterStatus | null) {
  if (!resource || !clusterStatus) {
    return false
  }

  const scope = clusterStatus.workloadScope
  if (resource.kind === 'deployment') {
    return resource.name === scope.deploymentName
  }
  if (resource.kind === 'service') {
    return resource.name === scope.serviceName
  }
  if (resource.kind === 'pod') {
    return resource.name.startsWith(scope.podPrefix)
  }
  return false
}

function filterGroupResources(group: ResourceGroupName, resources: ResourceRecord[]) {
  if (group !== 'replicaSets') {
    return resources
  }

  return resources.filter(
    (resource) =>
      asNumber(resource.desiredReplicas) > 0 ||
      asNumber(resource.readyReplicas) > 0 ||
      asNumber(resource.availableReplicas) > 0,
  )
}

function describeFaultStage(experiment: ResourceRecord | null) {
  if (!experiment) {
    return {
      title: 'Ready for the next drill',
      tone: 'good' as const,
      detail: 'No active fault run is changing the workload right now.',
    }
  }

  if (experiment.status === 'pending') {
    return {
      title: 'Fault is starting',
      tone: 'warn' as const,
      detail: `${formatExperimentType(experiment.type)} has been accepted by the cluster and is still being applied.`,
    }
  }

  if (experiment.status === 'running') {
    if (experiment.type === 'pod-kill') {
      return {
        title: 'Pod replacement in progress',
        tone: 'warn' as const,
        detail: 'One pod is being removed so Kubernetes can prove it can replace the URL shortener cleanly.',
      }
    }

    if (experiment.type === 'network-latency') {
      return {
        title: 'Traffic is being slowed',
        tone: 'warn' as const,
        detail: 'The cluster is delaying requests on purpose so you can watch how the service behaves under network drag.',
      }
    }

    return {
      title: 'One pod is under pressure',
      tone: 'warn' as const,
      detail: 'Extra CPU load is being pushed onto the workload while the cluster tries to keep the service responsive.',
    }
  }

  if (experiment.status === 'recovered') {
    return {
      title: 'Last drill recovered',
      tone: 'good' as const,
      detail: `${formatExperimentType(experiment.type)} has finished and the workload has settled again.`,
    }
  }

  return {
    title: 'Waiting for cluster feedback',
    tone: 'quiet' as const,
    detail: 'The fault run exists, but the cluster has not reported a stable state yet.',
  }
}

function buildResilienceProof(
  experiment: ResourceRecord | null,
  clusterStatus: ClusterStatus | null,
  rolloutWatch: ReturnType<typeof buildRolloutWatch>,
  workloadPods: ResourceRecord[],
  workloadLabel: string,
) {
  const readyPods = workloadPods.filter((pod) => pod.ready).length
  const totalPods = workloadPods.length
  const latestPod = getLatestWorkloadPod(workloadPods)
  const workloadTone = toneForStatus(clusterStatus?.workload.status)

  let title = 'Service is steady'
  let note = `${workloadLabel} is healthy and ready for the next drill.`

  if (experiment?.status === 'running' && experiment.type === 'pod-kill') {
    title = 'Replacement path is visible'
    note =
      readyPods > 0
        ? `The cluster is replacing one pod while ${workloadLabel} still has healthy capacity.`
        : `The cluster is replacing the affected pod right now.`
  } else if (experiment?.status === 'running' && experiment.type === 'network-latency') {
    title = 'Degradation drill is active'
    note = `Requests are being delayed on purpose. Watch continuity and pod health while the service absorbs the slowdown.`
  } else if (experiment?.status === 'running' && experiment.type === 'cpu-stress') {
    title = 'Pressure drill is active'
    note = `One workload pod is under CPU pressure while the service tries to stay available.`
  } else if (experiment?.status === 'recovered') {
    title = 'Recovery completed'
    note = `${workloadLabel} has returned to a steady state after the last drill.`
  } else if (rolloutWatch?.tone === 'warn') {
    title = 'Recovery is still settling'
    note = rolloutWatch.note
  }

  return {
    title,
    tone: rolloutWatch?.tone === 'warn' ? 'warn' : workloadTone,
    note,
    rows: [
      {
        label: 'Service',
        value: clusterStatus ? formatStatusText(clusterStatus.workload.status) : 'Waiting',
      },
      {
        label: 'Healthy pods',
        value: totalPods > 0 ? `${readyPods} / ${totalPods} ready` : 'Waiting for workload pods',
      },
      {
        label: 'Active fault',
        value: experiment ? formatExperimentType(experiment.type) : 'None',
      },
      {
        label: 'Latest pod',
        value: latestPod?.name ?? 'Waiting for a workload pod',
      },
    ],
  }
}

export default function WorkspacePage() {
  const [clusterStatus, setClusterStatus] = useState<ClusterStatus | null>(null)
  const [resourceSnapshot, setResourceSnapshot] = useState<ResourceSnapshot | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<ResourceGroupName>('deployments')
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [resourceDetail, setResourceDetail] = useState<ResourceRecord | null>(null)
  const [resourceEvents, setResourceEvents] = useState<ClusterEventRecord[]>([])
  const [resourceLogs, setResourceLogs] = useState<ResourceLogRecord | null>(null)
  const [query, setQuery] = useState('')
  const [pageState, setPageState] = useState<RequestState>('loading')
  const [inspectorState, setInspectorState] = useState<RequestState>('ready')
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting')
  const [faultActionState, setFaultActionState] = useState<FaultActionState>('idle')
  const [faultActionMessage, setFaultActionMessage] = useState<string | null>(null)
  const [activeFaultType, setActiveFaultType] = useState<ExperimentTypeName | null>(null)
  const [snapshotVersion, setSnapshotVersion] = useState(0)
  const [showNamespaceActivity, setShowNamespaceActivity] = useState(false)
  const [dismissedExperimentNames, setDismissedExperimentNames] = useState<string[]>([])
  const lastActiveExperimentNameRef = useRef<string | null>(null)
  const pendingStopExperimentNameRef = useRef<string | null>(null)

  const deferredQuery = useDeferredValue(query)

  const applySnapshot = useEffectEvent(
    (nextStatus: ClusterStatus, nextResources: ResourceSnapshot) => {
      const nextSelection = ensureSelection(nextResources, selectedGroup, selectedName)

      startTransition(() => {
        setClusterStatus(nextStatus)
        setResourceSnapshot(nextResources)
        setSelectedGroup(nextSelection.group)
        setSelectedName(nextSelection.name)
        setPageState('ready')
        setConnectionState('live')
        setSnapshotVersion((current) => current + 1)
      })
    },
  )

  async function refreshSnapshot() {
    try {
      const [statusResponse, resourceResponse] = await Promise.all([
        fetchClusterStatus(),
        fetchResourceSnapshot(),
      ])
      const nextSelection = ensureSelection(
        resourceResponse.data,
        selectedGroup,
        selectedName,
      )

      startTransition(() => {
        setClusterStatus(statusResponse.data)
        setResourceSnapshot(resourceResponse.data)
        setSelectedGroup(nextSelection.group)
        setSelectedName(nextSelection.name)
        setPageState('ready')
        setConnectionState('live')
        setSnapshotVersion((current) => current + 1)
      })
    } catch {
      startTransition(() => {
        setConnectionState('offline')
      })
    }
  }

  useEffect(() => {
    let cancelled = false

    async function loadInitialState() {
      try {
        const [statusResponse, resourceResponse] = await Promise.all([
          fetchClusterStatus(),
          fetchResourceSnapshot(),
        ])
        if (!cancelled) {
          applySnapshot(statusResponse.data, resourceResponse.data)
        }
      } catch {
        if (!cancelled) {
          startTransition(() => {
            setPageState('error')
            setConnectionState('offline')
          })
        }
      }
    }

    loadInitialState()

    const stream = openClusterStream(
      (snapshot) => {
        if (!cancelled) {
          applySnapshot(snapshot.status, snapshot.resources)
        }
      },
      () => {
        if (!cancelled) {
          startTransition(() => {
            setConnectionState('offline')
          })
        }
      },
    )

    return () => {
      cancelled = true
      stream.close()
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const currentName = selectedName

    if (!currentName) {
      return () => {
        cancelled = true
      }
    }

    const resourceName = currentName

    async function loadInspector() {
      const kind = resourceGroupMeta.find(
        ({ group }) => group === selectedGroup,
      )?.kind as ResourceKindName

      setInspectorState('loading')

      try {
        const [detailResponse, eventsResponse, logsResponse] = await Promise.all([
          fetchResourceDetail(kind, resourceName),
          fetchResourceEvents(kind, resourceName),
          fetchResourceLogs(kind, resourceName),
        ])

        if (!cancelled) {
          startTransition(() => {
            setResourceDetail(detailResponse.data)
            setResourceEvents(eventsResponse.data)
            setResourceLogs(logsResponse.data)
            setInspectorState('ready')
          })
        }
      } catch {
        if (!cancelled) {
          startTransition(() => {
            setInspectorState('error')
            setResourceLogs(null)
          })
        }
      }
    }

    loadInspector()

    return () => {
      cancelled = true
    }
  }, [selectedGroup, selectedName, snapshotVersion])

  const resourceSections = resourceGroupMeta
    .map((section) => ({
      ...section,
      items: filterGroupResources(section.group, resourceSnapshot?.resources[section.group] ?? []),
    }))
    .filter((section) => section.group !== 'replicaSets' || section.items.length > 0)
  const selectedSection =
    resourceSections.find(({ group }) => group === selectedGroup) ?? resourceSections[0] ?? resourceGroupMeta[0]
  const currentResources = 'items' in selectedSection ? selectedSection.items : []
  const visibleResources = deferredQuery
    ? currentResources.filter((item) =>
        item.name.toLowerCase().includes(deferredQuery.trim().toLowerCase()),
      )
    : currentResources
  const displayedResource = resourceDetail ?? currentResources.find((item) => item.name === selectedName) ?? null
  const namespaceEvents = resourceSnapshot?.events ?? []
  const experiments = resourceSnapshot?.resources.experiments ?? []
  const activeExperiments = experiments.filter(
    (experiment) =>
      ['running', 'pending', 'paused'].includes(String(experiment.status ?? 'unknown')) &&
      !dismissedExperimentNames.includes(String(experiment.name ?? '')),
  )
  const currentExperiment = activeExperiments[0] ?? null
  const displayedEvidenceEvents = buildEvidenceEvents(displayedResource, resourceEvents).slice(
    0,
    EVIDENCE_EVENT_LIMIT,
  )
  const visibleNamespaceEvents = namespaceEvents.slice(
    0,
    showNamespaceActivity ? 10 : NAMESPACE_EVENT_LIMIT,
  )
  const chaosReady = clusterStatus?.chaosMesh.status === 'ready'
  const workloadDeployment = getWorkloadDeployment(resourceSnapshot, clusterStatus)
  const workloadService = getWorkloadService(resourceSnapshot, clusterStatus)
  const workloadPods = getWorkloadPods(resourceSnapshot, clusterStatus)
  const selectedResourceIsInScope = matchesWorkloadScope(displayedResource, clusterStatus)
  const activeFaultTarget =
    (displayedResource && selectedResourceIsInScope ? displayedResource : null) ??
    workloadDeployment ??
    workloadService ??
    workloadPods[0] ??
    null
  const canRunFaults = Boolean(activeFaultTarget && chaosReady)
  const workloadLabel = clusterStatus?.workloadScope.displayName ?? 'the workload'
  const workloadSystemName = clusterStatus?.workloadScope.deploymentName ?? 'workload-api'
  const inspectorNotice = buildInspectorNotice(displayedResource, clusterStatus)
  const evidenceFeedState = describeEvidenceFeedState(inspectorState)
  const rolloutWatch = buildRolloutWatch(resourceSnapshot, clusterStatus, displayedResource)
  const faultStage = describeFaultStage(currentExperiment)
  const resilienceProof = buildResilienceProof(
    currentExperiment,
    clusterStatus,
    rolloutWatch,
    workloadPods,
    workloadLabel,
  )
  const showDisconnectedWorkspace = pageState === 'error' && !resourceSnapshot
  const readyWorkloadPods = workloadPods.filter((pod) => pod.ready).length
  const runLocked = !canRunFaults || faultActionState === 'running' || activeExperiments.length > 0
  const currentExperimentAction =
    currentExperiment
      ? experimentActions.find((action) => action.type === currentExperiment.type) ?? null
      : null
  const activeTargetRows = [
    {
      label: 'Application',
      value: workloadLabel,
    },
    {
      label: 'Deployment',
      value: clusterStatus?.workloadScope.deploymentName ?? workloadSystemName,
    },
    {
      label: 'Service',
      value: workloadService?.name ?? clusterStatus?.workloadScope.serviceName ?? 'Waiting for service',
    },
    {
      label: 'Healthy pods',
      value:
        workloadPods.length > 0
          ? `${readyWorkloadPods} / ${workloadPods.length} ready`
          : 'Waiting for workload pods',
    },
  ]

  useEffect(() => {
    if (resourceSections.length === 0) {
      return
    }

    const matchingSection = resourceSections.find((section) => section.group === selectedGroup)
    if (!matchingSection) {
      startTransition(() => {
        setSelectedGroup(resourceSections[0].group)
        setSelectedName(resourceSections[0].items[0]?.name ?? null)
      })
      return
    }

    if (selectedName && !matchingSection.items.some((resource) => resource.name === selectedName)) {
      startTransition(() => {
        setSelectedName(matchingSection.items[0]?.name ?? null)
      })
    }
  }, [resourceSections, selectedGroup, selectedName])

  useEffect(() => {
    if (activeExperiments.length > 0) {
      lastActiveExperimentNameRef.current = String(activeExperiments[0].name ?? '')
      return
    }

    if (!lastActiveExperimentNameRef.current) {
      return
    }

    const completedName = lastActiveExperimentNameRef.current
    lastActiveExperimentNameRef.current = null
    const stopWasRequested = pendingStopExperimentNameRef.current === completedName
    pendingStopExperimentNameRef.current = null

    if (stopWasRequested) {
      return
    }

    startTransition(() => {
      setActiveFaultType(null)
      setFaultActionState('success')
      setFaultActionMessage(`${completedName} has ended and the cluster reported recovery.`)
    })
  }, [activeExperiments])

  useEffect(() => {
    if (dismissedExperimentNames.length === 0) {
      return
    }

    const liveExperiments = resourceSnapshot?.resources.experiments ?? []
    const liveExperimentNames = new Set(
      liveExperiments
        .filter((experiment) =>
          ['running', 'pending', 'paused'].includes(String(experiment.status ?? 'unknown')),
        )
        .map((experiment) => String(experiment.name ?? '')),
    )

    const nextDismissed = dismissedExperimentNames.filter((name) => liveExperimentNames.has(name))
    if (nextDismissed.length !== dismissedExperimentNames.length) {
      startTransition(() => {
        setDismissedExperimentNames(nextDismissed)
      })
    }
  }, [dismissedExperimentNames, resourceSnapshot])

  async function handleRunExperiment(type: ExperimentTypeName) {
    if (!activeFaultTarget) {
      setFaultActionState('error')
      setFaultActionMessage(`Wait for ${workloadLabel} before starting a fault run.`)
      return
    }

    const action = experimentActions.find((item) => item.type === type)
    if (!action) {
      return
    }

    setFaultActionState('running')
    setActiveFaultType(type)
    setFaultActionMessage(`Starting ${action.label.toLowerCase()} on ${activeFaultTarget.name}.`)

    try {
      const response = await createExperiment({
        type,
        target: {
          kind: activeFaultTarget.kind,
          name: activeFaultTarget.name,
        },
        durationSeconds: action.durationSeconds,
        parameters: action.parameters,
      })

      lastActiveExperimentNameRef.current = response.data.name
      await refreshSnapshot()
      startTransition(() => {
        setSelectedGroup('experiments')
        setSelectedName(response.data.name)
        setFaultActionState('success')
        setFaultActionMessage(`${action.label} is now running.`)
      })
    } catch (error) {
      startTransition(() => {
        setFaultActionState('error')
        setFaultActionMessage(
          error instanceof Error ? error.message : 'The control plane could not start that fault run.',
        )
      })
    } finally {
      startTransition(() => {
        setActiveFaultType(null)
      })
    }
  }

  async function handleCancelExperiment() {
    const experimentToCancel =
      displayedResource?.kind === 'experiment' ? displayedResource : currentExperiment

    if (!experimentToCancel) {
      return
    }

    setFaultActionState('running')
    setFaultActionMessage(`Stopping ${experimentToCancel.name}.`)

    try {
      await cancelExperiment(experimentToCancel.name)
      await refreshSnapshot()
      pendingStopExperimentNameRef.current = experimentToCancel.name
      startTransition(() => {
        setDismissedExperimentNames((current) =>
          current.includes(experimentToCancel.name)
            ? current
            : [...current, experimentToCancel.name],
        )
        setActiveFaultType(null)
        setFaultActionState('success')
        setFaultActionMessage('The selected fault run has been stopped. Waiting for the cluster to clear it from the feed.')
      })
    } catch (error) {
      startTransition(() => {
        setFaultActionState('error')
        setFaultActionMessage(
          error instanceof Error ? error.message : 'The control plane could not stop that fault run.',
        )
      })
    }
  }

  return (
    <div className="workspace-page">
      <header className="workspace-masthead">
        <div className="workspace-masthead__copy">
          <p className="eyebrow">Workspace</p>
          <h1>Run guided faults and inspect recovery.</h1>
          <p className="workspace-masthead__intro">
            Stay focused on one workload, one namespace, and one clear recovery story at a time.
          </p>
        </div>

        <div className="workspace-masthead__scope">
          <div className={`presence presence--${connectionState}`}>
            <span className="presence__dot" />
            <span>
              {connectionState === 'live'
                ? 'Live updates'
                : connectionState === 'connecting'
                  ? 'Connecting'
                  : 'Offline'}
            </span>
          </div>
          <dl>
            <div>
              <dt>Cluster</dt>
              <dd>{clusterStatus?.clusterName ?? 'Waiting for cluster'}</dd>
            </div>
            <div>
              <dt>Namespace</dt>
              <dd>{clusterStatus?.namespace ?? 'Waiting for namespace'}</dd>
            </div>
            <div>
              <dt>Provider</dt>
              <dd>{clusterStatus?.provider ?? 'Waiting for provider'}</dd>
            </div>
          </dl>
        </div>
      </header>

      <section className="workspace-overview">
        <article className="signal">
          <p className="signal__label">URL shortener API</p>
          <strong className={`signal__value signal__value--${toneForStatus(clusterStatus?.workload.status)}`}>
            {workloadPods.length > 0 ? `${readyWorkloadPods} / ${workloadPods.length} ready` : 'Loading'}
          </strong>
          <p className="signal__meta">
            {clusterStatus
              ? `${workloadLabel} • deployment/${workloadSystemName}`
              : 'Waiting for workload status.'}
          </p>
        </article>

        <article className="signal">
          <p className="signal__label">Service continuity</p>
          <strong className={`signal__value signal__value--${toneForStatus(clusterStatus?.workload.status)}`}>
            {clusterStatus ? formatStatusText(clusterStatus.workload.status) : 'Loading'}
          </strong>
          <p className="signal__meta">
            {clusterStatus?.workload.message ??
              'The workload health check drives the top-line continuity signal.'}
          </p>
        </article>

        <article className="signal">
          <p className="signal__label">Fault status</p>
          <strong className={`signal__value signal__value--${faultStage.tone}`}>
            {faultStage.title}
          </strong>
          <p className="signal__meta">
            {faultStage.detail}
          </p>
        </article>
      </section>

      {showDisconnectedWorkspace ? (
        <main className="workspace-offline">
          <section className="workspace-offline__panel">
            <p className="pane__eyebrow">Connection</p>
            <h2>Workspace is waiting for the live control plane.</h2>
            <p className="workspace-offline__copy">
              The operating surface could not load the cluster right now. When the
              connection returns, resources, actions, and recovery details will appear here.
            </p>

            <div className="workspace-offline__actions">
              <button
                type="button"
                className="button button--primary"
                onClick={() => {
                  void refreshSnapshot()
                }}
              >
                Retry connection
              </button>
            </div>

            <dl className="workspace-offline__grid">
              <div>
                <dt>Control plane</dt>
                <dd>Needs to answer the workspace status and resource requests.</dd>
              </div>
              <div>
                <dt>Workload</dt>
                <dd>The locked service should be reachable again before faults are started.</dd>
              </div>
              <div>
                <dt>Next step</dt>
                <dd>Retry once the environment is back, then the workspace will repopulate.</dd>
              </div>
            </dl>
          </section>
        </main>
      ) : (
        <>
          <section className="workspace-focus">
            <article className="workspace-target-card">
              <div className="workspace-section-heading">
                <p className="pane__eyebrow">Active target</p>
                <h2>
                  {workloadLabel}
                  <InfoHint label="This is the application target the platform can safely stress. In the live environment, fault actions stay pinned to this API so the rest of the namespace remains context, not confusion." />
                </h2>
                <p className="pane__copy">
                  Fault actions stay pinned to the live URL shortener API even while you inspect
                  other cluster resources.
                </p>
              </div>

              <div className="workspace-target-card__flag">Guarded fault target</div>

              <dl className="workspace-target-card__grid">
                {activeTargetRows.map((row) => (
                  <div key={row.label}>
                    <dt>{row.label}</dt>
                    <dd>{row.value}</dd>
                  </div>
                ))}
              </dl>

              <p className="workspace-target-card__note">
                {selectedResourceIsInScope && displayedResource
                  ? `You are currently inspecting ${displayedResource.name}, which is inside the guarded fault scope.`
                  : `You can inspect anything in the namespace, but fault runs stay locked to ${workloadLabel}.`}
              </p>
            </article>

            <aside className="workspace-inventory">
              <div className="workspace-section-heading">
                <p className="pane__eyebrow">Cluster inventory</p>
                <h2>
                  Other resources
                  <InfoHint label="The inventory is the surrounding cluster context. It helps you inspect pods, services, replica sets, and experiment runs without changing which application the fault buttons target." />
                </h2>
                <p className="pane__copy">
                  Inspect the rest of the namespace without losing the active target or the
                  current recovery story.
                </p>
              </div>

              <div className="tabs" role="tablist" aria-label="Resource groups">
                {resourceSections.map((section) => (
                  <button
                    key={section.group}
                    type="button"
                    className={section.group === selectedGroup ? 'tab tab--active' : 'tab'}
                    onClick={() => {
                      startTransition(() => {
                        setSelectedGroup(section.group)
                        setSelectedName(section.items[0]?.name ?? null)
                      })
                    }}
                  >
                    <span>{section.label}</span>
                    <span className="tab__count">
                      {section.items.length}
                    </span>
                  </button>
                ))}
              </div>

              <label className="search">
                <span className="search__label">Filter</span>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={`Find a ${selectedSection.label.toLowerCase()}`}
                />
              </label>

              <div className="resource-list" role="list">
                {visibleResources.length === 0 ? (
                  <p className="empty-state">{selectedSection.emptyLabel}</p>
                ) : (
                  visibleResources.map((resource) => (
                    <button
                      key={resource.name}
                      type="button"
                      className={
                        resource.name === selectedName
                          ? 'resource-list__item resource-list__item--active'
                          : 'resource-list__item'
                      }
                      onClick={() => {
                        startTransition(() => {
                          setSelectedName(resource.name)
                        })
                      }}
                    >
                      <div>
                        <strong>{resource.name}</strong>
                        <p>{summarizeResource(resource)}</p>
                      </div>
                      <span
                        className={`resource-list__status resource-list__status--${toneForStatus(
                          String(resource.status ?? 'unknown'),
                        )}`}
                      >
                        {formatStatusText(String(resource.status ?? 'unknown'))}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </aside>
          </section>

          <section className="workspace-action-stage">
            <div className="workspace-action-stage__main">
              <div className="workspace-section-heading workspace-section-heading--wide">
                <p className="pane__eyebrow">Fault controls</p>
                <h2>
                  Run a controlled chaos drill
                  <InfoHint label="A chaos drill is a temporary disruption that helps you understand how the app behaves under pressure. These controls only target the guarded URL shortener API shown above." />
                </h2>
                <p className="pane__copy">
                  Start one drill at a time, then watch how the cluster absorbs it and whether
                  the URL shortener stays healthy.
                </p>
              </div>

              <div className="workspace-action-stage__target">
                <div>
                  <p className="pane__eyebrow">Current fault target</p>
                  <strong>{workloadLabel}</strong>
                  <span className="workspace-action-stage__target-meta">
                    {activeFaultTarget
                      ? `${labelForKind(activeFaultTarget.kind)} • ${activeFaultTarget.name}`
                      : `deployment • ${workloadSystemName}`}
                  </span>
                </div>
                <p>
                  {activeFaultTarget
                    ? `Faults stay pinned here even while you inspect other resources, so the resilience proof remains clear.`
                    : 'Waiting for the active target to become available.'}
                </p>
              </div>

              {currentExperiment ? (
                <section className="active-fault-card">
                  <div className="active-fault-card__header">
                    <div>
                      <p className="pane__eyebrow">Active drill</p>
                      <h3>
                        {currentExperimentAction?.label ?? formatExperimentType(currentExperiment.type)}
                        <InfoHint label="While a drill is active, the start buttons are hidden so the page stays focused on one cluster event at a time. Stop the current drill or wait for recovery before starting the next one." />
                      </h3>
                    </div>
                    <span
                      className={`resource-list__status resource-list__status--${toneForStatus(
                        String(currentExperiment.status ?? 'unknown'),
                      )}`}
                    >
                      {formatStatusText(String(currentExperiment.status ?? 'unknown'))}
                    </span>
                  </div>
                  <p className="active-fault-card__body">
                    {currentExperimentAction?.helper ?? 'A live drill is changing the workload right now.'}
                  </p>
                  <dl className="active-fault-card__grid">
                    <div>
                      <dt>Fault</dt>
                      <dd>{currentExperimentAction?.label ?? formatExperimentType(currentExperiment.type)}</dd>
                    </div>
                    <div>
                      <dt>Effect</dt>
                      <dd>{currentExperimentAction?.impact ?? 'Waiting for impact details.'}</dd>
                    </div>
                    <div>
                      <dt>Target</dt>
                      <dd>{String(currentExperiment.target ?? workloadLabel)}</dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>
                        {typeof currentExperiment.durationSeconds === 'number'
                          ? `${currentExperiment.durationSeconds}s`
                          : 'Until recovery is confirmed'}
                      </dd>
                    </div>
                  </dl>
                  <div className="active-fault-card__actions">
                    <button
                      type="button"
                      className="button button--primary"
                      disabled={faultActionState === 'running'}
                      onClick={() => {
                        void handleCancelExperiment()
                      }}
                    >
                      {faultActionState === 'running' ? 'Stopping drill' : 'Stop active drill'}
                    </button>
                    <p>
                      The other drill buttons are hidden until this run ends so the recovery story
                      stays clear.
                    </p>
                  </div>
                </section>
              ) : (
                <div className="workspace-fault-grid">
                  {experimentActions.map((action) => (
                    <article key={action.type} className="fault-card">
                      <div className="fault-card__header">
                        <span className="fault-card__eyebrow">Temporary fault</span>
                        <InfoHint
                          label={
                            action.type === 'pod-kill'
                              ? 'This removes one running pod so Kubernetes replaces it. Use it to see whether the app recovers cleanly.'
                              : action.type === 'network-latency'
                                ? 'This adds delay to requests so you can watch how the app behaves when the network slows down.'
                                : 'This raises CPU load on the workload so you can see whether the app stays responsive under compute pressure.'
                          }
                        />
                      </div>
                      <span className="fault-card__title">{action.label}</span>
                      <p className="fault-card__body">{action.helper}</p>
                      <dl className="fault-card__facts">
                        <div>
                          <dt>Effect</dt>
                          <dd>{action.impact}</dd>
                        </div>
                        <div>
                          <dt>Duration</dt>
                          <dd>{action.durationSeconds}s</dd>
                        </div>
                      </dl>
                      <button
                        type="button"
                        className="button button--primary fault-card__cta"
                        disabled={runLocked}
                        onClick={() => {
                          void handleRunExperiment(action.type)
                        }}
                      >
                        {activeFaultType === action.type && faultActionState === 'running'
                          ? 'Starting drill'
                          : `Run ${action.label}`}
                      </button>
                    </article>
                  ))}
                </div>
              )}

              {faultActionMessage ? (
                <div
                  className={
                    faultActionState === 'error'
                      ? 'message message--error'
                      : faultActionState === 'success'
                        ? 'message message--success'
                        : 'message'
                  }
                >
                  {faultActionMessage}
                </div>
              ) : null}
            </div>

            <aside className="workspace-action-stage__watch">
              {rolloutWatch ? (
                <section className="rollout-watch">
                  <div className="detail-events__header">
                    <h3>
                      Recovery watch
                      <InfoHint label="Recovery watch is the quickest way to see whether the guarded workload is still healthy, replacing pods, or already settled again." />
                    </h3>
                    <p>{rolloutWatch.note}</p>
                  </div>
                  <strong
                    className={`rollout-watch__status rollout-watch__status--${rolloutWatch.tone}`}
                  >
                    {rolloutWatch.title}
                  </strong>
                  <dl className="rollout-watch__grid">
                    {rolloutWatch.rows.map((row) => (
                      <div key={row.label}>
                        <dt>{row.label}</dt>
                        <dd>{row.value}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ) : null}

              <section className="workspace-proof">
                <div className="detail-events__header">
                  <h3>
                    Resilience proof
                    <InfoHint label="This panel translates the live cluster state into a plain-language summary of whether the service stayed available, how many pods remained healthy, and what the last drill changed." />
                  </h3>
                  <p>{resilienceProof.note}</p>
                </div>
                <strong
                  className={`workspace-proof__status workspace-proof__status--${resilienceProof.tone}`}
                >
                  {resilienceProof.title}
                </strong>
                <dl className="workspace-proof__grid">
                  {resilienceProof.rows.map((row) => (
                    <div key={row.label}>
                      <dt>{row.label}</dt>
                      <dd>{row.value}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            </aside>
          </section>

          <section className="workspace-detail-grid">
            <article className="workspace-inspector workspace-inspector--resource">
              <div className="pane__header workspace-inspector__header">
                <p className="pane__eyebrow">Selected resource</p>
                <h2>{displayedResource?.name ?? 'Choose a resource'}</h2>
                <p className="pane__copy">
                  {displayedResource
                    ? summarizeResource(displayedResource)
                    : 'Pick a deployment, pod, service, or experiment to inspect it.'}
                </p>
              </div>

              {displayedResource ? (
                <>
                  <dl className="detail-grid">
                    {buildResourceRows(displayedResource).map((row) => (
                      <div key={row.label}>
                        <dt>{row.label}</dt>
                        <dd>{row.value}</dd>
                      </div>
                    ))}
                  </dl>

                  {inspectorNotice ? <div className="message">{inspectorNotice}</div> : null}
                  {!selectedResourceIsInScope && displayedResource.kind !== 'experiment' ? (
                    <div className="message">
                      You are inspecting {displayedResource.name}. Fault actions remain locked to{' '}
                      {activeFaultTarget?.name ?? workloadLabel} so the demo target stays clear.
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="empty-state workspace-empty-state">
                  The namespace is reachable, but there is nothing to inspect yet.
                </p>
              )}
            </article>

            <article className="workspace-inspector workspace-inspector--evidence">
              <div className="pane__header workspace-inspector__header">
                <p className="pane__eyebrow">Evidence and logs</p>
                <h2>
                  Live proof feed
                  <InfoHint label="This feed shows the clearest recent proof for the selected resource: what the cluster reported and what the workload logged. It stays short on purpose so the signal is readable during a demo." />
                </h2>
                <p className="pane__copy">
                  {displayedResource
                    ? 'The right-hand feed stays focused on only the most useful recent evidence.'
                    : 'Select a resource to unlock the live evidence feed.'}
                </p>
              </div>

              {displayedResource ? (
                <div className="workspace-evidence-grid">
                  <section className="detail-events">
                    <div className="detail-events__header">
                      <div className="detail-events__title">
                        <h3>Evidence</h3>
                        <span
                          className={`detail-events__status detail-events__status--${evidenceFeedState.tone}`}
                        >
                          {evidenceFeedState.label}
                        </span>
                      </div>
                      <p>{describeEvidence(displayedResource)}</p>
                    </div>

                    {displayedEvidenceEvents.length === 0 ? (
                      <p className="empty-state">No recent events for this resource.</p>
                    ) : (
                      <ul className="event-list">
                        {displayedEvidenceEvents.map((event, index) => (
                          <li key={`${event.name ?? event.reason ?? 'event'}-${index}`}>
                            <strong>{event.reason ?? event.type ?? 'Status update'}</strong>
                            <p>{event.message ?? 'The cluster reported a state change without extra notes.'}</p>
                            <span>{formatUpdatedAt(event.timestamp)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>

                  <section className="detail-events detail-events--logs">
                    <div className="detail-events__header">
                      <h3>Logs</h3>
                      <p>{describeLogs(displayedResource, resourceLogs)}</p>
                    </div>

                    {!resourceLogs || resourceLogs.entries.length === 0 ? (
                      <p className="empty-state">{describeEmptyLogs(displayedResource)}</p>
                    ) : (
                      <pre className="log-block">
                        {resourceLogs.entries.slice(-LOG_LINE_LIMIT).map((entry, index) => (
                          <code key={`${index}-${entry.line}`}>{entry.line}</code>
                        ))}
                      </pre>
                    )}
                  </section>
                </div>
              ) : (
                <p className="empty-state workspace-empty-state">
                  Select a resource to load recent cluster evidence and matching workload logs.
                </p>
              )}
            </article>
          </section>

          <section className="workspace-activity-card">
            <div className="workspace-activity-card__header">
              <div className="workspace-section-heading">
                <p className="pane__eyebrow">Namespace activity</p>
                <h2>
                  Recent cluster updates
                  <InfoHint label="Namespace activity is the compact cluster-wide feed for this demo scope. It gives you the top recent changes without flooding the page with every single event." />
                </h2>
                <p className="pane__copy">
                  Only the newest updates are shown here so the page stays readable while a drill
                  is running.
                </p>
              </div>

              <button
                type="button"
                className="button button--secondary workspace-activity-card__toggle"
                onClick={() => setShowNamespaceActivity((current) => !current)}
              >
                {showNamespaceActivity ? 'Collapse feed' : 'Show feed'}
              </button>
            </div>

            {showNamespaceActivity ? (
              visibleNamespaceEvents.length === 0 ? (
                <p className="empty-state workspace-empty-state">No namespace events yet.</p>
              ) : (
                <>
                  <ul className="event-list event-list--compact">
                    {visibleNamespaceEvents.map((event, index) => (
                      <li key={`${event.name ?? event.reason ?? 'namespace-event'}-${index}`}>
                        <strong>{event.resourceName ?? 'Cluster event'}</strong>
                        <p>
                          {event.reason ?? 'Update'}
                          {event.message ? ` • ${event.message}` : ''}
                        </p>
                        <span>{formatUpdatedAt(event.timestamp)}</span>
                      </li>
                    ))}
                  </ul>
                  {namespaceEvents.length > visibleNamespaceEvents.length ? (
                    <p className="workspace-activity-card__note">
                      Showing the latest {visibleNamespaceEvents.length} namespace updates.
                    </p>
                  ) : null}
                </>
              )
            ) : (
              <p className="workspace-activity-card__note">
                Open the feed when you want wider cluster context around the selected resource.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
