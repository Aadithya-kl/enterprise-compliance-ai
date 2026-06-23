import { useState, useEffect } from 'react'
import { documentsApi } from '../api/documents'
import type { QuestionResponse, IndexedFile } from '../types/audit'
import { extractErrorMessage } from '../utils/errors'
import FileSelector from '../components/qa/FileSelector'
import { DocumentIcon, MagnifyingGlassIcon, XMarkIcon, InboxIcon } from '@heroicons/react/24/outline'
import MarkdownRenderer from '../components/MarkdownRenderer'

export default function AskQuestionPage() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState('Analyzing Documents...')
  const [result, setResult] = useState<QuestionResponse | null>(null)
  const [error, setError] = useState('')

  // File selection state
  const [files, setFiles] = useState<IndexedFile[]>([])
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  
  // File selection state

  const fetchFiles = async () => {
    setLoadingFiles(true)
    try {
      const data = await documentsApi.getIndexedFiles()
      setFiles(data || [])
    } catch (err) {
      console.error('Failed to load indexed files:', err)
      setFiles([])
    } finally {
      setLoadingFiles(false)
    }
  }

  useEffect(() => {
    fetchFiles()
  }, [])

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>
    if (loading) {
      const stages = ['Classifying Intent...', 'Running Hybrid Search...', 'Retrieving Evidence...', 'Validating Evidence...', 'Generating Response...']
      let idx = 0
      setLoadingStage(stages[0])
      interval = setInterval(() => {
        idx = Math.min(idx + 1, stages.length - 1)
        setLoadingStage(stages[idx])
      }, 1500)
    }
    return () => clearInterval(interval)
  }, [loading])

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
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
    if (!files || files.length === 0) {
      return loading ? 'Searching...' : 'Get Answer'
    }
    const count = (selectedFiles || []).length > 0 ? selectedFiles.length : files.length
    if (loading) {
      return `Searching Across ${count} File${count !== 1 ? 's' : ''}...`
    }
    return `Get Answer (${count} File${count !== 1 ? 's' : ''})`
  }

  return (
    <div className="max-w-7xl mx-auto w-full px-4 space-y-6 pb-12">
      <div>
        <h1 className="page-heading">Ask Questions</h1>
        <p className="page-subheading mt-1">
          Query your compliance documents. Restrict the search to specific files or search across all indexed data.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left/Main column: Form and Answer */}
        <div className="lg:col-span-3 space-y-6">
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
                disabled={!question.trim() || loading || (!files || files.length === 0)}
                className="btn-primary flex items-center justify-center gap-2 px-5"
              >
                {loading && (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                )}
                <span>{loading ? loadingStage : getButtonText()}</span>
              </button>

              {(files || []).length > 0 && (selectedFiles || []).length > 0 && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Searching in <span className="font-semibold text-brand-600 dark:text-brand-400">{selectedFiles.length}</span> selected files
                </span>
              )}
            </div>
          </form>

          {(!files || files.length === 0) && !loading && !loadingFiles && (
            <div className="card p-8 text-center space-y-4 border-dashed border-2 border-brand-200 dark:border-brand-900 bg-brand-50/10 dark:bg-brand-950/5">
                <div className="mx-auto w-12 h-12 rounded-full bg-brand-100 dark:bg-brand-900/50 flex items-center justify-center">
                    <InboxIcon className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <div>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Knowledge Base Empty</h3>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                        There are no documents in your compliance repository. Connect Google Drive or upload files to start querying.
                    </p>
                </div>
            </div>
          )}

          {/* Selected Documents Section */}
          {(files || []).length > 0 && (
            <div className="card p-4 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400">
              <span>SELECTED DOCUMENTS FOR QUERY</span>
              <span>{!(selectedFiles || []).length ? 'All Documents' : `${selectedFiles.length} Selected`}</span>
            </div>
            {!(selectedFiles || []).length ? (
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
          )}

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
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Enterprise Compliance Answer</p>
                    <div className="flex items-center gap-2">
                        <button onClick={() => navigator.clipboard.writeText(result.answer)} className="p-1.5 text-gray-400 hover:text-brand-500 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-800" title="Copy">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                        </button>
                        <button onClick={() => {
                            const blob = new Blob([result.answer], { type: 'text/markdown' })
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement('a')
                            a.href = url
                            a.download = `compliance-answer-${Date.now()}.md`
                            a.click()
                        }} className="p-1.5 text-gray-400 hover:text-brand-500 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-800" title="Export .md">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                        </button>
                        <button onClick={() => handleAsk(new Event('submit') as unknown as React.FormEvent)} className="p-1.5 text-gray-400 hover:text-brand-500 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-800" title="Regenerate">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        </button>
                        <div className="w-px h-4 bg-gray-200 dark:bg-gray-700 mx-1"></div>
                        <button className="p-1.5 text-gray-400 hover:text-green-500 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-800" title="Helpful">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.514" /></svg>
                        </button>
                        <button className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-800" title="Not Helpful">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.514" /></svg>
                        </button>
                    </div>
                  </div>
                  <div className="text-sm">
                    <MarkdownRenderer content={result.answer} />
                  </div>
                  
                  {/* Phase 6: Diagnostics */}
                  {result.diagnostics && (
                    <div className="mt-8 border-t border-gray-100 dark:border-gray-800/70 pt-6">
                      <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-4">Retrieval Diagnostics</p>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700/50">
                          <p className="text-[10px] text-gray-500 uppercase">Strategy</p>
                          <p className="text-xs font-semibold mt-1 text-gray-900 dark:text-gray-200 capitalize">{result.diagnostics.strategy?.replace(/_/g, ' ') || 'N/A'}</p>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700/50">
                          <p className="text-[10px] text-gray-500 uppercase">Coverage</p>
                          <p className="text-xs font-semibold mt-1 text-gray-900 dark:text-gray-200">{result.diagnostics.coverage || 'N/A'}</p>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700/50">
                          <p className="text-[10px] text-gray-500 uppercase">Searched vs Used</p>
                          <p className="text-xs font-semibold mt-1 text-gray-900 dark:text-gray-200">{result.diagnostics.documents_used ?? 0} / {result.diagnostics.documents_searched ?? 0}</p>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700/50">
                          <p className="text-[10px] text-gray-500 uppercase">Total Chunks</p>
                          <p className="text-xs font-semibold mt-1 text-gray-900 dark:text-gray-200">{result.diagnostics.total_chunks ?? 0}</p>
                        </div>
                      </div>
                      
                      {Object.keys(result.diagnostics.distribution || {}).length > 0 && (
                        <div className="mt-4">
                          <p className="text-[10px] text-gray-500 uppercase mb-2">Chunk Distribution</p>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(result.diagnostics.distribution || {}).map(([file, count]) => (
                              <div key={file} className="text-xs px-2 py-1 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 rounded-md border border-brand-100 dark:border-brand-800">
                                <span className="opacity-70 mr-1">{file}:</span>
                                <span className="font-semibold">{count as number}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Dynamic Suggested Questions */}
              {result.suggested_questions && result.suggested_questions.length > 0 && (
                <div className="card p-5 border border-brand-100 dark:border-brand-900/30 bg-brand-50/20 dark:bg-brand-950/10">
                    <p className="text-[10px] font-bold text-brand-500 dark:text-brand-400 uppercase tracking-widest mb-3">Suggested Follow-up Questions</p>
                    <div className="flex flex-wrap gap-2">
                    {result.suggested_questions.map((q: string) => (
                        <button
                        key={q}
                        onClick={() => { setQuestion(q); setTimeout(() => handleAsk(new Event('submit') as unknown as React.FormEvent), 50) }}
                        className="px-4 py-2 text-xs font-medium rounded-lg bg-white dark:bg-gray-800 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800 hover:bg-brand-50 dark:hover:bg-brand-900/50 hover:border-brand-300 dark:hover:border-brand-700 transition-all shadow-sm flex items-center gap-2"
                        >
                        <span>{q}</span>
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                        </button>
                    ))}
                    </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right column: Document selector */}
        <div className="lg:col-span-1">
          <FileSelector
            files={files || []}
            selectedFiles={selectedFiles || []}
            onSelectionChange={setSelectedFiles}
            loading={loadingFiles}
          />
        </div>
      </div>
    </div>
  )
}
