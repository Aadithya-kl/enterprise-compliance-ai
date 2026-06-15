import { DocumentTextIcon, ShieldCheckIcon, ChartBarIcon, DocumentIcon } from '@heroicons/react/24/outline'

const CATEGORIES: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; className: string }> = {
  policy: {
    label: 'Policy',
    icon: DocumentTextIcon,
    className: 'bg-blue-50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800'
  },
  regulation: {
    label: 'Regulation',
    icon: ShieldCheckIcon,
    className: 'bg-purple-50 dark:bg-purple-950/20 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800'
  },
  report: {
    label: 'Report',
    icon: ChartBarIcon,
    className: 'bg-green-50 dark:bg-green-950/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800'
  },
  general: {
    label: 'General',
    icon: DocumentIcon,
    className: 'bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800'
  }
}

interface SourceBadgeProps {
  documentType: string
}

export default function SourceBadge({ documentType }: SourceBadgeProps) {
  const norm = documentType?.toLowerCase()
  const cat = CATEGORIES[norm] || {
    label: documentType || 'Document',
    icon: DocumentIcon,
    className: 'bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800'
  }
  const Icon = cat.icon
  return (
    <span
      title={documentType}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-semibold leading-none truncate max-w-[120px] ${cat.className}`}
    >
      <Icon className="w-3 h-3 flex-shrink-0" />
      <span className="truncate">{cat.label}</span>
    </span>
  )
}
