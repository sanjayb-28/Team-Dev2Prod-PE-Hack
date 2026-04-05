import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
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

const experimentActions: Array<{
  type: ExperimentTypeName
  label: string
  helper: string
  durationSeconds: number
  parameters: Record<string, unknown>
}> = [
  {
    type: 'pod-kill',
    label: 'Pod restart',
    helper: 'Temporarily remove one running pod so you can watch the platform replace it.',
    durationSeconds: 30,
    parameters: {},
  },
  {
    type: 'network-latency',
    label: 'Network latency',
    helper: 'Slow requests on purpose so you can see how the app behaves when the network drags.',
    durationSeconds: 60,
    parameters: { latencyMs: 120 },
  },
  {
    type: 'cpu-stress',
    label: 'CPU pressure',
    helper: 'Push extra CPU load onto the workload without disturbing the rest of the namespace.',
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

function describeEvidence(resource: ResourceRecord | null, inspectorState: RequestState) {
  if (inspectorState === 'loading') {
    return 'Refreshing recent events.'
  }

  if (resource?.kind !== 'experiment') {
    return 'Recent events attached to the selected resource.'
  }

  if (resource.status === 'recovered') {
    return 'This run has finished. Review the events that applied the fault and confirmed recovery.'
  }

  return 'Cluster events that show how this fault is being applied right now.'
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

  const workloadLabel = clusterStatus?.workloadScope.deploymentName ?? 'the workload'
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
  }, [selectedGroup, selectedName])

  const selectedSection = resourceGroupMeta.find(({ group }) => group === selectedGroup) ?? resourceGroupMeta[0]
  const currentResources = resourceSnapshot?.resources[selectedGroup] ?? []
  const visibleResources = deferredQuery
    ? currentResources.filter((item) =>
        item.name.toLowerCase().includes(deferredQuery.trim().toLowerCase()),
      )
    : currentResources
  const displayedResource = resourceDetail ?? currentResources.find((item) => item.name === selectedName) ?? null
  const namespaceEvents = resourceSnapshot?.events.slice(0, 6) ?? []
  const experiments = resourceSnapshot?.resources.experiments ?? []
  const activeExperiments = experiments.filter((experiment) =>
    ['running', 'pending', 'paused'].includes(String(experiment.status ?? 'unknown')),
  )
  const displayedEvidenceEvents = buildEvidenceEvents(displayedResource, resourceEvents)
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
  const workloadLabel = clusterStatus?.workloadScope.deploymentName ?? 'the workload'
  const inspectorNotice = buildInspectorNotice(displayedResource, clusterStatus)
  const rolloutWatch = buildRolloutWatch(resourceSnapshot, clusterStatus, displayedResource)
  const showDisconnectedWorkspace = pageState === 'error' && !resourceSnapshot
  const activeTargetRows = [
    {
      label: 'Current target',
      value: activeFaultTarget ? activeFaultTarget.name : workloadLabel,
    },
    {
      label: 'Type',
      value: activeFaultTarget ? labelForKind(activeFaultTarget.kind) : 'Waiting for cluster data',
    },
    {
      label: 'Scope lock',
      value: clusterStatus?.scopeLocked ? `Locked to ${clusterStatus.namespace}` : 'Open scope',
    },
    {
      label: 'Healthy pods',
      value:
        workloadPods.length > 0
          ? `${workloadPods.filter((pod) => pod.ready).length} / ${workloadPods.length} ready`
          : 'Waiting for workload pods',
    },
  ]

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
    if (!displayedResource || displayedResource.kind !== 'experiment') {
      return
    }

    setFaultActionState('running')
    setFaultActionMessage(`Stopping ${displayedResource.name}.`)

    try {
      await cancelExperiment(displayedResource.name)
      await refreshSnapshot()
      startTransition(() => {
        setFaultActionState('success')
        setFaultActionMessage('The selected fault run has been stopped.')
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
          <p className="signal__label">Service</p>
          <strong className={`signal__value signal__value--${toneForStatus(clusterStatus?.workload.status)}`}>
            {clusterStatus ? formatStatusText(clusterStatus.workload.status) : 'Loading'}
          </strong>
          <p className="signal__meta">
            {clusterStatus?.workload.message ??
              'The workload health check drives the top-line service signal.'}
          </p>
        </article>

        <article className="signal">
          <p className="signal__label">Control plane</p>
          <strong className={`signal__value signal__value--${toneForStatus(clusterStatus?.controlPlane.status)}`}>
            {clusterStatus ? formatStatusText(clusterStatus.controlPlane.status) : 'Loading'}
          </strong>
          <p className="signal__meta">
            {clusterStatus
              ? `${clusterStatus.mode} mode • scope locked to ${clusterStatus.namespace}`
              : 'Waiting for control-plane status'}
          </p>
        </article>

        <article className="signal">
          <p className="signal__label">Fault tools</p>
          <strong className={`signal__value signal__value--${toneForStatus(clusterStatus?.chaosMesh.status)}`}>
            {clusterStatus ? formatStatusText(clusterStatus.chaosMesh.status) : 'Loading'}
          </strong>
          <p className="signal__meta">
            {clusterStatus?.chaosMesh.status === 'ready'
              ? `${activeExperiments.length} active experiment${activeExperiments.length === 1 ? '' : 's'}`
              : 'Install and enable Chaos Mesh to unlock the fault controls.'}
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
                  Guarded workload
                  <InfoHint label="A workload is the application target the platform can safely stress. The live demo keeps fault actions locked to this target so the rest of the namespace stays predictable." />
                </h2>
                <p className="pane__copy">
                  Fault actions stay pinned to this target even while you inspect other cluster
                  resources.
                </p>
              </div>

              <div className="workspace-target-card__flag">Locked for the live demo</div>

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
                  : `You can inspect anything in the namespace, but fault runs stay locked to ${activeFaultTarget?.name ?? workloadLabel}.`}
              </p>
            </article>

            <aside className="workspace-inventory">
              <div className="workspace-section-heading">
                <p className="pane__eyebrow">Cluster inventory</p>
                <h2>
                  Inspect the namespace
                  <InfoHint label="The inventory is the list of cluster resources you can inspect. It is broader than the active fault target and exists to provide context, not to unlock every action." />
                </h2>
                <p className="pane__copy">
                  Use the inventory to inspect deployments, pods, services, and experiment runs
                  without losing track of the active fault target.
                </p>
              </div>

              <div className="tabs" role="tablist" aria-label="Resource groups">
                {resourceGroupMeta.map((section) => (
                  <button
                    key={section.group}
                    type="button"
                    className={section.group === selectedGroup ? 'tab tab--active' : 'tab'}
                    onClick={() => {
                      startTransition(() => {
                        setSelectedGroup(section.group)
                        setSelectedName(resourceSnapshot?.resources[section.group][0]?.name ?? null)
                      })
                    }}
                  >
                    <span>{section.label}</span>
                    <span className="tab__count">
                      {resourceSnapshot?.resources[section.group].length ?? 0}
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
                  Start a controlled fault run
                  <InfoHint label="A fault run is a temporary disruption that helps you understand how the app behaves under pressure. These controls only target the guarded workload shown above." />
                </h2>
                <p className="pane__copy">
                  Pick one temporary fault at a time. The recovery watch and the evidence
                  sections below will help you understand what changed.
                </p>
              </div>

              <div className="workspace-action-stage__target">
                <div>
                  <p className="pane__eyebrow">Current fault target</p>
                  <strong>{activeFaultTarget?.name ?? workloadLabel}</strong>
                </div>
                <p>
                  {activeFaultTarget
                    ? `${labelForKind(activeFaultTarget.kind)} selected. Faults remain pinned here even when you inspect other resources.`
                    : 'Waiting for the active target to become available.'}
                </p>
              </div>

              <div className="workspace-fault-grid">
                {experimentActions.map((action) => (
                  <button
                    key={action.type}
                    type="button"
                    className="fault-card"
                    disabled={!canRunFaults || faultActionState === 'running'}
                    onClick={() => {
                      void handleRunExperiment(action.type)
                    }}
                  >
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
                    <small>
                      {!chaosReady
                        ? 'Waiting for the fault tooling to become ready.'
                        : activeFaultType === action.type && faultActionState === 'running'
                          ? 'Starting now.'
                          : action.helper}
                    </small>
                  </button>
                ))}
              </div>

              {displayedResource?.kind === 'experiment' ? (
                <button
                  type="button"
                  className="action-list__secondary"
                  disabled={faultActionState === 'running'}
                  onClick={() => {
                    void handleCancelExperiment()
                  }}
                >
                  Stop selected experiment
                </button>
              ) : null}

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
            </aside>
          </section>

          <section className="workspace-inspector">
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

                <details className="detail-collapsible" open>
                  <summary className="detail-collapsible__summary">
                    <span>
                      Evidence and logs
                      <InfoHint label="Evidence is the plain-language proof of what changed. It combines recent cluster events with the latest matching workload logs." />
                    </span>
                    <small>{displayedEvidenceEvents.length} recent events</small>
                  </summary>
                  <div className="detail-collapsible__body">
                    <section className="detail-events">
                      <div className="detail-events__header">
                        <h3>Evidence</h3>
                        <p>{describeEvidence(displayedResource, inspectorState)}</p>
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
                          {resourceLogs.entries.slice(-20).map((entry, index) => (
                            <code key={`${index}-${entry.line}`}>{entry.line}</code>
                          ))}
                        </pre>
                      )}
                    </section>
                  </div>
                </details>

                <details className="detail-collapsible">
                  <summary className="detail-collapsible__summary">
                    <span>
                      Namespace activity
                      <InfoHint label="Namespace activity is the recent cluster-wide event feed for this demo scope. It helps you see what else changed around the selected resource." />
                    </span>
                    <small>{namespaceEvents.length} recent updates</small>
                  </summary>
                  <div className="detail-collapsible__body">
                    {namespaceEvents.length === 0 ? (
                      <p className="empty-state">No namespace events yet.</p>
                    ) : (
                      <ul className="event-list event-list--compact">
                        {namespaceEvents.map((event, index) => (
                          <li key={`${event.name ?? event.reason ?? 'namespace-event'}-${index}`}>
                            <strong>{event.resourceName ?? 'Cluster event'}</strong>
                            <p>{event.reason ?? 'Update'}</p>
                            <span>{formatUpdatedAt(event.timestamp)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </details>
              </>
            ) : (
              <p className="empty-state">
                The namespace is reachable, but there is nothing to inspect yet.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
