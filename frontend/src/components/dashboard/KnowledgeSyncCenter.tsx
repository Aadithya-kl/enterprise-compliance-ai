import { CloudArrowDownIcon, DocumentTextIcon } from '@heroicons/react/24/outline'

interface SyncCenterProps {
  stats: Record<string, any>
  onSyncComplete?: () => void
}

export default function KnowledgeSyncCenter({ stats }: SyncCenterProps) {
  const sources = [
    {
      id: 'google_drive',
      name: 'Google Drive',
      description: 'Corporate policies, risk registers, and operational docs.',
      icon: CloudArrowDownIcon,
      color: 'text-blue-500 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-900/20'
    },
    {
      id: 'notion',
      name: 'Notion Workspace',
      description: 'Engineering specs, wikis, and team knowledge.',
      icon: DocumentTextIcon,
      color: 'text-gray-900 dark:text-gray-100',
      bg: 'bg-gray-100 dark:bg-gray-800'
    }
  ]

  return (
    <div className="space-y-4">
      {sources.map(source => {
        const sourceStats = stats?.[source.id]
        const isConnected = sourceStats?.sources_connected > 0

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
            </div>
          </div>
        )
      })}
    </div>
  )
}
