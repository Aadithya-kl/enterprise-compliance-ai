import { useState, useEffect } from 'react'
import { documentsApi } from '../api/documents'
import type { QuestionResponse, IndexedFile } from '../types/audit'
import { extractErrorMessage } from '../utils/errors'
import FileSelector from '../components/qa/FileSelector'
import EvidenceDrawer from '../components/common/EvidenceDrawer'
import { DocumentIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'

export default function AskQuestionPage() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QuestionResponse | null>(null)
  const [error, setError] = useState('')

  // File selection state
  const [files, setFiles] = useState<IndexedFile[]>([])
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  
  // Accordion visibility states
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  const fetchFiles = async () => {
    setLoadingFiles(true)
    try {
      const data = await documentsApi.getIndexedFiles()
      setFiles(data)
    } catch (err) {
      console.error('Failed to load indexed files:', err)
    } finally {
      setLoadingFiles(false)
    }
  }

  useEffect(() => {
    fetchFiles()
  }, [])

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setShowDiagnostics(false)
    try {
      const res = await documentsApi.ask(question.trim(), selectedFiles)
      setResult(res)
    } catch (err: unknown) {
      setError(extractErrorMessage(err) ?? 'Failed to get answer.')
    } finally {
      setLoading(false)
    }
  }

  const EXAMPLE_QUESTIONS = [
    'What are the data retention requirements in the regulation?',
    'Does our policy address incident response procedures?',
    'What are the penalties for non-compliance?',
    'Is two-factor authentication required?',
  ]

  const getButtonText = () => {
    if (files.length === 0) {
      return loading ? 'Searching...' : 'Get Answer'
    }
    const count = selectedFiles.length > 0 ? selectedFiles.length : files.length
    if (loading) {
      return `Searching Across ${count} File${count !== 1 ? 's' : ''}...`
    }
    return `Get Answer (${count} File${count !== 1 ? 's' : ''})`
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div>
        <h1 className="page-heading">Ask Questions</h1>
        <p className="page-subheading mt-1">
          Query your compliance documents. Restrict the search to specific files or search across all indexed data.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left/Main column: Form and Answer */}
        <div className="lg:col-span-2 space-y-6">
          {/* Question Form */}
          <form onSubmit={handleAsk} className="card p-5 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                Your Question
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={3}
                className="input resize-none"
                placeholder="e.g. What are the data retention requirements?"
              />
            </div>
            <div className="flex items-center justify-between">
              <button
                type="submit"
                disabled={!question.trim() || loading}
                className="btn-primary flex items-center justify-center gap-2 px-5"
              >
                {loading && (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                )}
                <span>{getButtonText()}</span>
              </button>

              {files.length > 0 && selectedFiles.length > 0 && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Searching in <span className="font-semibold text-brand-600 dark:text-brand-400">{selectedFiles.length}</span> selected files
                </span>
              )}
            </div>
          </form>

          {/* Selected Documents Section */}
          <div className="card p-4 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400">
              <span>SELECTED DOCUMENTS FOR QUERY</span>
              <span>{selectedFiles.length === 0 ? 'All Documents' : `${selectedFiles.length} Selected`}</span>
            </div>
            {selectedFiles.length === 0 ? (
              <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
                <MagnifyingGlassIcon className="w-3.5 h-3.5 text-brand-500" />
                <span>All indexed files in the knowledge base will be queried.</span>
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1 scrollbar-thin">
                {selectedFiles.map((fname) => (
                  <div
                    key={fname}
                    className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-xs font-medium bg-brand-50/50 dark:bg-brand-950/20 text-brand-700 dark:text-brand-400 border border-brand-200/50 dark:border-brand-850"
                  >
                    <DocumentIcon className="w-3 h-3 text-gray-400" />
                    <span className="truncate max-w-[180px]">{fname}</span>
                    <button
                      type="button"
                      onClick={() => setSelectedFiles(selectedFiles.filter((f) => f !== fname))}
                      className="hover:bg-brand-100 dark:hover:bg-brand-900 rounded-full p-0.5 text-brand-400 hover:text-brand-600 dark:hover:text-brand-300 transition-colors"
                    >
                      <XMarkIcon className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Example Questions */}
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium uppercase tracking-wider">Example questions:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => setQuestion(q)}
                  className="px-3.5 py-1.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800
                             text-gray-700 dark:text-gray-300 border border-transparent hover:border-gray-200
                             hover:bg-brand-50 dark:hover:bg-brand-950/20
                             hover:text-brand-700 dark:hover:text-brand-400 transition-all duration-200"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="px-4 py-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Answer Card */}
          {result && (
            <div className="space-y-6">
              <div className="card p-6 space-y-6">
                <div>
                  <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-1.5">Question</p>
                  <p className="text-base font-semibold text-gray-900 dark:text-white leading-snug">{result.question}</p>
                </div>

                <div className="border-t border-gray-100 dark:border-gray-800/70" />

                <div>
                  <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-2">Grounded Answer</p>
                  <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap font-normal">
                    {result.answer}
                  </p>
                </div>
              </div>

              {/* Shared EvidenceDrawer Component */}
              {result.sources && result.sources.length > 0 && (
                <EvidenceDrawer
                  sources={result.sources}
                  totalChunks={result.diagnostics?.total_chunks}
                  retrievalMode={result.diagnostics?.retrieval_mode}
                  title="Evidence Sources"
                />
              )}

              {/* Compact Diagnostics Summary and Collapsible Drawer */}
              {result.diagnostics && (
                <div className="card p-5 space-y-3.5 border border-gray-200 dark:border-gray-800">
                  <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
                    Query Performance Summary
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-xs">
                    <div>
                      <span className="text-gray-450 dark:text-gray-500 font-medium">Retrieved Chunks</span>
                      <p className="font-semibold text-gray-900 dark:text-white mt-0.5">
                        {result.diagnostics.total_chunks} chunks
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-450 dark:text-gray-500 font-medium">Files Used</span>
                      <p className="font-semibold text-gray-900 dark:text-white mt-0.5">
                        {result.diagnostics.matched_files.length} file{result.diagnostics.matched_files.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-450 dark:text-gray-500 font-medium">Retrieval Mode</span>
                      <p className="font-semibold text-gray-900 dark:text-white mt-0.5 capitalize">
                        {result.diagnostics.retrieval_mode === 'filtered' ? 'Filtered Search' : 'Global Search'}
                      </p>
                    </div>
                  </div>

                  <div className="border-t border-gray-150/50 dark:border-gray-800/50 pt-3 mt-3">
                    <button
                      type="button"
                      onClick={() => setShowDiagnostics(!showDiagnostics)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors focus:outline-none"
                    >
                      <span>
                        {showDiagnostics
                          ? 'Hide Technical Diagnostics ▲'
                          : `Show Technical Diagnostics (${result.diagnostics.total_chunks} chunks) ▼`}
                      </span>
                    </button>

                    {showDiagnostics && (
                      <div className="mt-3.5 p-4 rounded-lg bg-gray-100/50 dark:bg-gray-850/40 text-xs font-mono text-gray-650 dark:text-gray-300 space-y-2.5 border border-gray-200/50 dark:border-gray-850/85 animate-in fade-in duration-200">
                        <div className="grid grid-cols-2 gap-y-1.5 border-b border-gray-200/40 dark:border-gray-800/40 pb-2.5 mb-2.5">
                          <div><span className="text-gray-455 dark:text-gray-500 font-bold">Mode:</span> <span className="text-gray-850 dark:text-gray-150">{result.diagnostics.retrieval_mode === 'filtered' ? 'Filtered' : 'Global'}</span></div>
                          <div><span className="text-gray-455 dark:text-gray-500 font-bold">Chunks Retrieved:</span> <span className="text-gray-850 dark:text-gray-150">{result.diagnostics.total_chunks}</span></div>
                          <div><span className="text-gray-455 dark:text-gray-500 font-bold">Files Selected:</span> <span className="text-gray-850 dark:text-gray-150">{result.diagnostics.selected_files.length}</span></div>
                          <div><span className="text-gray-455 dark:text-gray-500 font-bold">Files Used:</span> <span className="text-gray-850 dark:text-gray-150">{result.diagnostics.matched_files.length}</span></div>
                        </div>

                        <div>
                          <div className="text-gray-455 dark:text-gray-500 font-bold uppercase mb-0.5">[Selected Files]</div>
                          <div className="text-gray-800 dark:text-gray-200 break-all">{result.diagnostics.selected_files.length > 0 ? result.diagnostics.selected_files.join(', ') : 'None'}</div>
                        </div>
                        <div>
                          <div className="text-gray-455 dark:text-gray-500 font-bold uppercase mb-0.5">[Matched Filenames]</div>
                          <div className="text-gray-800 dark:text-gray-200 break-all">{result.diagnostics.matched_files.length > 0 ? result.diagnostics.matched_files.join(', ') : 'None'}</div>
                        </div>
                        <div>
                          <div className="text-gray-455 dark:text-gray-500 font-bold uppercase mb-1">[Chunks Per File]</div>
                          <ul className="list-disc list-inside ml-2 space-y-0.5">
                            {Object.entries(result.diagnostics.retrieved_chunks_per_file).map(([fname, count]) => (
                              <li key={fname}>
                                <span className="text-gray-700 dark:text-gray-200">{fname}</span>: {count} chunk{count !== 1 ? 's' : ''}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right column: Document selector */}
        <div className="lg:col-span-1">
          <FileSelector
            files={files}
            selectedFiles={selectedFiles}
            onSelectionChange={setSelectedFiles}
            loading={loadingFiles}
          />
        </div>
      </div>
    </div>
  )
}
