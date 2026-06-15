import { useMemo } from 'react'
import { ArrowTopRightOnSquareIcon, DocumentIcon } from '@heroicons/react/24/outline'
import SourceBadge from './SourceBadge'

export interface SourceItem {
  filename: string
  document_type: string
  chunks_used: number
  confidence: number
  drive_web_view_link?: string | null
}

interface SourceAttributionPanelProps {
  sources: SourceItem[]
}

const getConfidenceBarColor = (score: number) => {
  if (score >= 80) return 'bg-green-500'
  if (score >= 50) return 'bg-amber-500'
  return 'bg-red-500'
}


export default function SourceAttributionPanel({ sources }: SourceAttributionPanelProps) {
  const sortedSources = useMemo(() => {
    return [...sources].sort((a, b) => b.confidence - a.confidence)
  }, [sources])

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
      {sortedSources.map((src, i) => (
        <div
          key={i}
          className="flex flex-col p-4 rounded-xl border border-gray-150 dark:border-gray-700/60 bg-gray-50/40 dark:bg-gray-800/10 hover:bg-gray-50/70 dark:hover:bg-gray-800/25 transition-all duration-200"
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-2.5 min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <DocumentIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span
                className="text-xs font-semibold text-gray-900 dark:text-gray-100 truncate"
                title={src.filename}
              >
                {src.filename}
              </span>
            </div>
            <SourceBadge documentType={src.document_type} />
          </div>

          {/* Relevance Score bar */}
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-450 dark:text-gray-500 font-medium">Relevance Score</span>
              <span className="font-bold text-gray-800 dark:text-gray-250">{src.confidence}%</span>
            </div>
            <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${getConfidenceBarColor(src.confidence)}`}
                style={{ width: `${src.confidence}%` }}
              />
            </div>
          </div>

          {/* Bottom alignment */}
          <div className="mt-3 pt-3 flex items-center justify-between border-t border-gray-100 dark:border-gray-800/70 text-xs">
            <span className="text-gray-500 dark:text-gray-400">
              Chunks Used: <span className="font-semibold text-gray-700 dark:text-gray-300">{src.chunks_used}</span>
            </span>

            {src.drive_web_view_link && (
              <a
                href={src.drive_web_view_link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 font-semibold text-brand-600 dark:text-brand-400 hover:underline hover:text-brand-700"
              >
                <span>View Source</span>
                <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5 flex-shrink-0" />
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
