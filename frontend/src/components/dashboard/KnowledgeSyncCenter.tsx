import { useState, useEffect } from 'react'
import { integrationsApi } from '../../api/integrations'
import type { SyncResponse, SyncStatus } from '../../api/integrations'
import { ArrowPathIcon, CloudArrowDownIcon, DocumentTextIcon } from '@heroicons/react/24/outline'

interface SyncCenterProps {
  stats: Record<string, any>
  onSyncComplete: () => void
}

export default function KnowledgeSyncCenter({ stats, onSyncComplete }: SyncCenterProps) {
  const [syncJobs, setSyncJobs] = useState<Record<string, string>>({})
  const [syncStatuses, setSyncStatuses] = useState<Record<string, SyncStatus>>({})
  const [syncing, setSyncing] = useState<Record<string, boolean>>({})
  const [syncError, setSyncError] = useState<string | null>(null)

  useEffect(() => {
    const activeSources = Object.keys(syncJobs).filter(source => syncing[source])
    if (activeSources.length === 0) return

    const interval = setInterval(async () => {
      for (const source of activeSources) {
        const jobId = syncJobs[source]
        if (!jobId) continue

        try {
          const status = await integrationsApi.getSyncStatus(jobId)
          setSyncStatuses(prev => ({ ...prev, [source]: status }))

          if (status.status === 'Sync Complete' || status.status.startsWith('Failed')) {
            setSyncing(prev => ({ ...prev, [source]: false }))
            onSyncComplete()
          }
        } catch (err) {
          console.error('Error polling sync status', err)
        }
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [syncJobs, syncing, onSyncComplete])

  const handleSync = async (source: string, apiCall: () => Promise<SyncResponse>) => {
    setSyncing(prev => ({ ...prev, [source]: true }))
    setSyncError(null)
    try {
      const res = await apiCall()
      setSyncJobs(prev => ({ ...prev, [source]: res.job_id }))
      setSyncStatuses(prev => ({
        ...prev,
        [source]: {
          job_id: res.job_id,
          status: res.status,
          documents_processed: 0,
          total_documents: 0,
          chunks_generated: 0,
          started_at: new Date().toISOString(),
          completed_at: null
        }
      }))
    } catch (err: any) {
      console.error(`Failed to start sync ${source}:`, err)
      setSyncing(prev => ({ ...prev, [source]: false }))
      setSyncError(`Failed to sync ${source}: ${err?.message || 'Server error'}`)
    }
  }

  const sources = [
    {
      id: 'google_drive',
      name: 'Google Drive',
      description: 'Corporate policies, risk registers, and operational docs.',
      icon: CloudArrowDownIcon,
      syncCall: integrationsApi.syncGoogleDrive,
      color: 'text-blue-500 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-900/20'
    },
    {
      id: 'notion',
      name: 'Notion Workspace',
      description: 'Engineering specs, wikis, and team knowledge.',
      icon: DocumentTextIcon,
      syncCall: integrationsApi.syncNotion,
      color: 'text-gray-900 dark:text-gray-100',
      bg: 'bg-gray-100 dark:bg-gray-800'
    }
  ]

  return (
    <div className="space-y-4">
      {syncError && (
        <div className="px-4 py-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-center justify-between">
          <span className="text-sm text-red-700 dark:text-red-400">{syncError}</span>
          <button onClick={() => setSyncError(null)} className="text-red-500 hover:text-red-700 dark:hover:text-red-300">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}
      {sources.map(source => {
        const sourceStats = stats?.[source.id]
        const isConnected = sourceStats?.sources_connected > 0
        const isSyncing = syncing[source.id]
        const currentStatus = syncStatuses[source.id]

        return (
          <div key={source.id} className="flex flex-col p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm transition-all hover:border-brand-200 dark:hover:border-brand-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg ${source.bg}`}>
                  <source.icon className={`w-6 h-6 ${source.color}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white">{source.name}</h3>
                    {isConnected ? (
                      <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-400 rounded-full">Connected</span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider text-gray-500 bg-gray-100 dark:bg-gray-800 dark:text-gray-400 rounded-full">Not Configured</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{source.description}</p>
                  <div className="flex items-center gap-4 mt-2">
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                      <span className="text-brand-600 dark:text-brand-400 mr-1">{sourceStats?.total_documents ?? 0}</span> Documents
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500 border-l border-gray-200 dark:border-gray-700 pl-4">
                      Last Sync: {sourceStats?.last_sync && sourceStats.last_sync !== 'Never' ? sourceStats.last_sync : 'Never'}
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <button
                  onClick={() => handleSync(source.id, source.syncCall)}
                  disabled={!isConnected || isSyncing}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                    !isConnected 
                      ? 'bg-gray-50 text-gray-400 cursor-not-allowed dark:bg-gray-800/50 dark:text-gray-600'
                      : 'bg-brand-50 text-brand-700 hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-400 dark:hover:bg-brand-900/50'
                  }`}
                >
                  <ArrowPathIcon className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                  {isSyncing ? 'Syncing...' : 'Sync Now'}
                </button>
              </div>
            </div>
            
            {/* Sync Progress Tracker */}
            {(isSyncing || (currentStatus && (currentStatus.status === 'Sync Complete' || currentStatus.status.startsWith('Failed')))) && (
              <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-semibold text-gray-700 dark:text-gray-300">Status: {currentStatus?.status || 'Starting...'}</span>
                  {currentStatus?.total_documents > 0 && (
                    <span className="text-gray-500">{currentStatus.documents_processed} / {currentStatus.total_documents} files</span>
                  )}
                </div>
                
                {/* Progress bar */}
                {currentStatus?.total_documents > 0 && (
                  <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700 mb-2">
                    <div 
                      className="bg-brand-600 h-1.5 rounded-full transition-all duration-500 ease-out" 
                      style={{ width: `${Math.min(100, Math.max(0, (currentStatus.documents_processed / currentStatus.total_documents) * 100))}%` }}
                    ></div>
                  </div>
                )}
                
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{currentStatus?.chunks_generated || 0} chunks generated</span>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
