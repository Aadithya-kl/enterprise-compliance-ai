import { useState, useMemo } from 'react'
import { FolderIcon, DocumentIcon } from '@heroicons/react/24/outline'

export interface IndexedFile {
  filename: string
  document_type: string
  source: string
  chunk_count: number
}

interface FileSelectorProps {
  files: IndexedFile[]
  selectedFiles: string[]
  onSelectionChange: (selected: string[]) => void
  loading?: boolean
}

function getFileExtBadge(filename: string): string {
  const ext = filename.substring(filename.lastIndexOf('.') + 1).toUpperCase()
  return ext
}

const PAGE_SIZE = 20

// Compact text categories mapping for badges without emojis
const CLEAN_CATEGORIES: Record<string, { label: string; className: string }> = {
  policy: {
    label: 'Policy',
    className: 'bg-blue-50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800'
  },
  regulation: {
    label: 'Regulation',
    className: 'bg-purple-50 dark:bg-purple-950/20 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800'
  },
  report: {
    label: 'Report',
    className: 'bg-green-50 dark:bg-green-950/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800'
  },
  general: {
    label: 'General',
    className: 'bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800'
  }
}

function getCategoryInfo(docType: string) {
  const norm = docType.toLowerCase()
  return CLEAN_CATEGORIES[norm] || {
    label: docType || 'Document',
    className: 'bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800'
  }
}

export default function FileSelector({
  files,
  selectedFiles,
  onSelectionChange,
  loading = false,
}: FileSelectorProps) {
  const [search, setSearch] = useState('')
  const [showAll, setShowAll] = useState(false)

  const allSelected = selectedFiles.length === files.length && files.length > 0

  const filteredFiles = useMemo(() => {
    if (!search.trim()) return files
    const q = search.toLowerCase()
    return files.filter(
      (f) =>
        f.filename.toLowerCase().includes(q) ||
        f.document_type.toLowerCase().includes(q)
    )
  }, [files, search])

  const displayedFiles = showAll
    ? filteredFiles
    : filteredFiles.slice(0, PAGE_SIZE)

  const handleToggleAll = () => {
    if (allSelected) {
      onSelectionChange([])
    } else {
      onSelectionChange(files.map((f) => f.filename))
    }
  }

  const handleToggleFile = (filename: string) => {
    if (selectedFiles.includes(filename)) {
      onSelectionChange(selectedFiles.filter((f) => f !== filename))
    } else {
      onSelectionChange([...selectedFiles, filename])
    }
  }

  if (loading) {
    return (
      <div className="card p-5">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Loading indexed documents...
          </span>
        </div>
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="card p-5">
        <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
          <FolderIcon className="w-8 h-8 text-gray-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">No documents indexed</p>
            <p className="text-xs mt-0.5 text-gray-500 dark:text-gray-400">
              Upload documents first to enable file-specific querying.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-200 dark:border-gray-700/60 bg-gray-50/50 dark:bg-gray-800/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderIcon className="w-5 h-5 text-brand-600 dark:text-brand-400 flex-shrink-0" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              Select Documents
            </h3>
            {selectedFiles.length > 0 && (
              <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400">
                {selectedFiles.length} selected
              </span>
            )}
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {files.length} document{files.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="px-5 py-3 border-b border-gray-100 dark:border-gray-700/40">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search files..."
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-600
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500
                       transition-colors"
          />
        </div>
      </div>

      {/* Select All */}
      <label className="flex items-center gap-3 px-5 py-2.5 border-b border-gray-100 dark:border-gray-700/40
                        cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
        <input
          type="checkbox"
          checked={allSelected}
          onChange={handleToggleAll}
          className="h-4 w-4 rounded border-gray-300 dark:border-gray-600
                     text-brand-600 focus:ring-brand-500 focus:ring-offset-0
                     dark:bg-gray-700 cursor-pointer"
        />
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          Select All Files
        </span>
        <span className="text-xs text-gray-400 dark:text-gray-500 ml-auto">
          ({files.length} documents)
        </span>
      </label>

      {/* File List */}
      <div className="max-h-64 overflow-y-auto scrollbar-thin">
        {displayedFiles.map((file) => (
          <label
            key={file.filename}
            className="flex items-center gap-3 px-5 py-2 cursor-pointer
                       hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors
                       border-b border-gray-50 dark:border-gray-800/30 last:border-b-0"
          >
            <input
              type="checkbox"
              checked={selectedFiles.includes(file.filename)}
              onChange={() => handleToggleFile(file.filename)}
              className="h-4 w-4 rounded border-gray-300 dark:border-gray-600
                         text-brand-600 focus:ring-brand-500 focus:ring-offset-0
                         dark:bg-gray-700 cursor-pointer flex-shrink-0"
            />
            <DocumentIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 dark:text-gray-100 truncate" title={file.filename}>
                {file.filename}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5 text-xs text-gray-450 dark:text-gray-500">
                <span className="flex-shrink-0">{file.chunk_count} chunks</span>
                <span>·</span>
                {(() => {
                  const cat = getCategoryInfo(file.document_type)
                  return (
                    <span
                      title={file.document_type}
                      className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-semibold truncate max-w-[120px] ${cat.className}`}
                    >
                      <span className="truncate">{cat.label}</span>
                    </span>
                  )
                })()}
              </div>
            </div>
            <span className="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider
                             bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
              {getFileExtBadge(file.filename)}
            </span>
          </label>
        ))}
      </div>

      {/* Show More / Show Less */}
      {filteredFiles.length > PAGE_SIZE && (
        <div className="px-5 py-2.5 border-t border-gray-100 dark:border-gray-700/40 text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs font-medium text-brand-600 dark:text-brand-400
                       hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
          >
            {showAll
              ? 'Show less'
              : `Show ${filteredFiles.length - PAGE_SIZE} more files`}
          </button>
        </div>
      )}
    </div>
  )
}
