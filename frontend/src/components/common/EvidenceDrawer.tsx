import { useState, useMemo } from 'react'
import { FolderOpenIcon, ChevronDownIcon, DocumentDuplicateIcon } from '@heroicons/react/24/outline'
import SourceAttributionPanel from './SourceAttributionPanel'
import type { SourceItem } from './SourceAttributionPanel'

interface EvidenceDrawerProps {
  sources: SourceItem[]
  totalChunks?: number
  retrievalMode?: string
  title?: string
}

export default function EvidenceDrawer({
  sources,
  totalChunks,
  retrievalMode,
  title = 'Evidence & Sources'
}: EvidenceDrawerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showAllSources, setShowAllSources] = useState(false)

  // Calculate contribution score percentages
  const contributionScores = useMemo(() => {
    if (!sources || sources.length === 0) return []
    
    const getWeightMultiplier = (docType: string, filename: string): number => {
      const typeLower = (docType || '').toLowerCase();
      const fileLower = (filename || '').toLowerCase();

      // High-Value Documents: Policy = 1.5, Regulation = 1.5, Standard = 1.5, Procedure = 1.5
      if (
        typeLower === 'policy' ||
        typeLower === 'regulation' ||
        typeLower === 'standard' ||
        typeLower === 'procedure' ||
        fileLower.includes('policy') ||
        fileLower.includes('regulation') ||
        fileLower.includes('standard') ||
        fileLower.includes('procedure')
      ) {
        return 1.5;
      }

      // Lower-Priority Documents: Report = 0.7, General = 0.7
      if (
        typeLower === 'report' ||
        typeLower === 'general' ||
        fileLower.includes('report') ||
        fileLower.includes('general')
      ) {
        return 0.7;
      }

      return 1.0;
    };

    // Weight logic: chunks_used * confidence * category_multiplier
    const scored = sources.map(src => {
      const chunks = src.chunks_used || 1
      const confidence = src.confidence || 10
      const multiplier = getWeightMultiplier(src.document_type, src.filename)
      const weight = chunks * confidence * multiplier
      return { src, weight }
    })
    
    const totalWeight = scored.reduce((sum, item) => sum + item.weight, 0)
    
    return scored.map(item => {
      const pct = totalWeight > 0 ? Math.round((item.weight / totalWeight) * 100) : 0
      return {
        ...item.src,
        contribution: pct
      }
    }).sort((a, b) => b.contribution - a.contribution)
  }, [sources])

  const calculatedTotalChunks = useMemo(() => {
    if (totalChunks !== undefined) return totalChunks
    return sources.reduce((sum, item) => sum + (item.chunks_used || 0), 0)
  }, [sources, totalChunks])

  if (!sources || sources.length === 0) {
    return null
  }

  const additionalCount = contributionScores.length - 3

  return (
    <div className="card border border-gray-200 dark:border-gray-800 overflow-hidden bg-white dark:bg-gray-950 transition-all duration-200">
      {/* Header Button Toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-5 py-4 text-sm font-semibold text-gray-800 dark:text-gray-200 hover:bg-gray-50/50 dark:hover:bg-gray-900/30 transition-all duration-150 focus:outline-none"
      >
        <div className="flex items-center gap-2">
          <FolderOpenIcon className="w-4.5 h-4.5 text-brand-500 dark:text-brand-400" />
          <span>
            {title} ({sources.length})
          </span>
        </div>
        <ChevronDownIcon
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
            isOpen ? 'transform rotate-180' : ''
          }`}
        />
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="border-t border-gray-150 dark:border-gray-850 p-5 space-y-5 bg-gray-50/20 dark:bg-gray-950/20 animate-in fade-in duration-200">
          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-gray-400 dark:text-gray-500 font-medium">Files Used</span>
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mt-0.5">
                {sources.length} document{sources.length !== 1 ? 's' : ''}
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500 font-medium">Chunks Retrieved</span>
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mt-0.5">
                {calculatedTotalChunks} chunk{calculatedTotalChunks !== 1 ? 's' : ''}
              </p>
            </div>
            {retrievalMode && (
              <div className="col-span-2 sm:col-span-1">
                <span className="text-gray-400 dark:text-gray-500 font-medium">Retrieval Mode</span>
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mt-0.5 capitalize">
                  {retrievalMode}
                </p>
              </div>
            )}
          </div>

          <div className="border-t border-gray-150 dark:border-gray-800/80 pt-4" />

          {/* Top Contributing Documents */}
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              <DocumentDuplicateIcon className="w-3.5 h-3.5" />
              <span>Top Contributing Documents</span>
            </div>
            <div className="space-y-2">
              {contributionScores.map((file, idx) => {
                // Determine whether to show it immediately (top 3) or when showing all contributors
                if (idx >= 3 && !showAllSources) return null

                return (
                  <div
                    key={file.filename}
                    className="flex items-center justify-between text-xs p-2.5 rounded-lg border border-gray-150 dark:border-gray-800 bg-white dark:bg-gray-950/40"
                  >
                    <span className="font-medium text-gray-700 dark:text-gray-300 truncate max-w-[70%]" title={file.filename}>
                      {file.filename}
                    </span>
                    <span className="font-semibold text-brand-600 dark:text-brand-400">
                      Contribution: {file.contribution}%
                    </span>
                  </div>
                )
              })}

              {additionalCount > 0 && (
                <button
                  type="button"
                  onClick={() => setShowAllSources(!showAllSources)}
                  className="text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors mt-1.5"
                >
                  {showAllSources ? 'Show less' : `+${additionalCount} additional supporting file${additionalCount !== 1 ? 's' : ''}`}
                </button>
              )}
            </div>
          </div>

          <div className="border-t border-gray-150 dark:border-gray-800/80 pt-4" />

          {/* Detailed Sources Toggle & Panel */}
          <div className="space-y-3">
            <div className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              Detailed Source Attribution
            </div>
            <SourceAttributionPanel sources={sources} />
          </div>
        </div>
      )}
    </div>
  )
}
