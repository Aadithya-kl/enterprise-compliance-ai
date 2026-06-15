import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { complianceApi } from '../api/compliance'
import { documentsApi } from '../api/documents'
import type { ComplianceReportResponse, WorkflowRunResponse, IndexedFile } from '../types/audit'
import { riskBadgeClass, scoreColor } from '../utils/formatters'
import { extractErrorMessage } from '../utils/errors'
import EvidenceDrawer from '../components/common/EvidenceDrawer'
import { integrationsApi } from '../api/integrations'
import {
  FolderOpenIcon,
  ArrowDownTrayIcon,
  DocumentIcon,
  MagnifyingGlassIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import FileSelector from '../components/qa/FileSelector'

export default function ComplianceReportsPage() {
  const queryClient = useQueryClient()
  const [quickReport, setQuickReport] = useState<ComplianceReportResponse | null>(null)
  const [workflowResult, setWorkflowResult] = useState<WorkflowRunResponse | null>(null)

  // Document list & selection state
  const [files, setFiles] = useState<IndexedFile[]>([])
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  const [evidenceOpen, setEvidenceOpen] = useState(false)

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

  const reportMutation = useMutation({
    mutationFn: (selected?: string[]) => complianceApi.generateReport(selected),
    onSuccess: (data) => {
      setQuickReport(data)
      setEvidenceOpen(false)
      queryClient.invalidateQueries({ queryKey: ['audit-history-recent'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })

  const workflowMutation = useMutation({
    mutationFn: (selected?: string[]) => complianceApi.runWorkflow('policy', 'regulation', selected),
    onSuccess: (data) => {
      setWorkflowResult(data)
      setEvidenceOpen(false)
      queryClient.invalidateQueries({ queryKey: ['audit-history-recent'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })

  const error = reportMutation.error || workflowMutation.error

  const handleExportPdf = async (id: number | null) => {
    if (!id) return
    try {
      await integrationsApi.exportReportPdf(id)
    } catch (err) {
      console.error('Export PDF failed:', err)
    }
  }

  const handleExportDocx = async (id: number | null) => {
    if (!id) return
    try {
      await integrationsApi.exportReportDocx(id)
    } catch (err) {
      console.error('Export DOCX failed:', err)
    }
  }

  const getGenerateButtonLabel = () => {
    if (reportMutation.isPending) return 'Generating...'
    const count = selectedFiles.length
    return count > 0 ? `Generate Report (${count} File${count !== 1 ? 's' : ''})` : 'Generate Report (All Files)'
  }

  const getWorkflowButtonLabel = () => {
    if (workflowMutation.isPending) return 'Running Workflow...'
    const count = selectedFiles.length
    return count > 0 ? `Run Full Workflow (${count} File${count !== 1 ? 's' : ''})` : 'Run Full Workflow (All Files)'
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div>
        <h1 className="page-heading">Compliance Reports</h1>
        <p className="page-subheading mt-1">
          Generate AI-powered compliance gap analysis reports from your uploaded documents.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left/Main Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Action cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Quick Report */}
            <div className="card p-5 flex flex-col justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                  Quick Compliance Report
                </h2>
                <p className="text-xs text-gray-500 mb-4">
                  Generates a structured compliance analysis and saves it to the audit log.
                </p>
              </div>
              <button
                onClick={() => { setWorkflowResult(null); reportMutation.mutate(selectedFiles) }}
                disabled={reportMutation.isPending || workflowMutation.isPending}
                className="btn-primary w-full"
              >
                {getGenerateButtonLabel()}
              </button>
            </div>

            {/* Full Workflow */}
            <div className="card p-5 border-brand-200 dark:border-brand-800 bg-brand-50/30 dark:bg-brand-950/10 flex flex-col justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                  Full AI Workflow
                </h2>
                <p className="text-xs text-gray-500 mb-4">
                  Runs the complete multi-agent pipeline: Compliance Agent, Risk Agent, Report Agent.
                </p>
              </div>
              <button
                onClick={() => { setQuickReport(null); workflowMutation.mutate(selectedFiles) }}
                disabled={reportMutation.isPending || workflowMutation.isPending}
                className="btn-primary w-full bg-brand-700 hover:bg-brand-800"
              >
                {getWorkflowButtonLabel()}
              </button>
            </div>
          </div>

          {/* Selected Documents Section */}
          <div className="card p-4 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400">
              <span>SELECTED DOCUMENTS FOR ANALYSIS</span>
              <span>{selectedFiles.length === 0 ? 'All Documents' : `${selectedFiles.length} Selected`}</span>
            </div>
            {selectedFiles.length === 0 ? (
              <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
                <MagnifyingGlassIcon className="w-3.5 h-3.5 text-brand-500" />
                <span>All indexed files in the knowledge base will be analyzed.</span>
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

          {/* Progress Indicator */}
          {workflowMutation.isPending && (
            <div className="card p-5 space-y-3.5 border border-brand-200 dark:border-brand-800 bg-brand-50/5 dark:bg-brand-950/5">
              <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
                AI Agent Workflow Progress
              </div>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-semibold">
                <div className="flex items-center gap-2">
                  <div className="h-5 w-5 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-400 flex items-center justify-center text-[10px] animate-pulse">
                    1
                  </div>
                  <div>
                    <p className="text-gray-950 dark:text-white">Compliance Agent</p>
                    <p className="text-[10px] text-brand-600 dark:text-brand-400 animate-pulse font-normal">Analyzing policy gaps...</p>
                  </div>
                </div>
                <div className="hidden sm:block text-gray-300 dark:text-gray-700">→</div>
                <div className="flex items-center gap-2">
                  <div className="h-5 w-5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-400 flex items-center justify-center text-[10px]">
                    2
                  </div>
                  <div>
                    <p className="text-gray-500">Risk Agent</p>
                    <p className="text-[10px] text-gray-400 font-normal">Waiting...</p>
                  </div>
                </div>
                <div className="hidden sm:block text-gray-300 dark:text-gray-700">→</div>
                <div className="flex items-center gap-2">
                  <div className="h-5 w-5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-400 flex items-center justify-center text-[10px]">
                    3
                  </div>
                  <div>
                    <p className="text-gray-500">Report Agent</p>
                    <p className="text-[10px] text-gray-400 font-normal">Waiting...</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="px-4 py-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
              {extractErrorMessage(error)}
            </div>
          )}

          {/* Quick Report Result */}
          {quickReport && (
            <div className="space-y-4">
              <ReportDetailsCard
                retrievedChunkCount={quickReport.retrieved_chunk_count}
                filesUsed={quickReport.files_used}
                retrievalMode={quickReport.retrieval_mode}
                workflowType="Quick Report"
                timestamp={quickReport.audit_timestamp}
                allFiles={files}
              />

              <ReportCard
                title="Compliance Report"
                risk={quickReport.risk}
                score={quickReport.compliance_score}
                violations={quickReport.violation_count}
                issues={quickReport.issues}
                recommendations={quickReport.recommendations}
                sources={quickReport.sources || []}
              />

              {/* Action Bar */}
              <div className="flex flex-wrap items-center gap-3 bg-white dark:bg-gray-950 p-4 rounded-xl border border-gray-150 dark:border-gray-800">
                {quickReport.sources && quickReport.sources.length > 0 && (
                  <button
                    onClick={() => setEvidenceOpen(!evidenceOpen)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                  >
                    <FolderOpenIcon className="w-3.5 h-3.5" />
                    <span>View Sources</span>
                  </button>
                )}
                {quickReport.id && (
                  <>
                    <button
                      onClick={() => handleExportPdf(quickReport.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                    >
                      <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </button>
                    <button
                      onClick={() => handleExportDocx(quickReport.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                    >
                      <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                      <span>Download DOCX</span>
                    </button>
                  </>
                )}
              </div>

              {/* Evidence Drawer */}
              {quickReport.sources && quickReport.sources.length > 0 && (
                <div className={evidenceOpen ? '' : 'hidden'}>
                  <EvidenceDrawer
                    sources={quickReport.sources}
                    totalChunks={quickReport.retrieved_chunk_count ?? undefined}
                    retrievalMode={quickReport.retrieval_mode ?? undefined}
                    title="Evidence Sources"
                  />
                </div>
              )}
            </div>
          )}

          {/* Workflow Result */}
          {workflowResult?.success && (
            <div className="space-y-4">
              <div className="card p-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Risk Level</p>
                  <span className={`mt-1 ${riskBadgeClass(workflowResult.risk_level ?? '')}`}>
                    {workflowResult.risk_level}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Compliance Score</p>
                  <p className={`text-2xl font-bold ${scoreColor(workflowResult.compliance_score ?? 0)}`}>
                    {workflowResult.compliance_score}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Violations</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {workflowResult.total_violations}
                  </p>
                </div>
              </div>

              <div className="card p-5 space-y-3.5 border border-green-200 dark:border-green-800 bg-green-50/5">
                <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
                  AI Agent Workflow Path
                </div>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-semibold">
                  <div className="flex items-center gap-2">
                    <div className="h-5 w-5 rounded-full bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-400 flex items-center justify-center text-[10px]">
                      ✓
                    </div>
                    <div>
                      <p className="text-gray-900 dark:text-gray-100">Compliance Agent</p>
                      <p className="text-[10px] text-green-600 dark:text-green-400 font-medium">Completed</p>
                    </div>
                  </div>
                  <div className="hidden sm:block text-green-300 dark:text-green-800">→</div>
                  <div className="flex items-center gap-2">
                    <div className="h-5 w-5 rounded-full bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-400 flex items-center justify-center text-[10px]">
                      ✓
                    </div>
                    <div>
                      <p className="text-gray-900 dark:text-gray-100">Risk Agent</p>
                      <p className="text-[10px] text-green-600 dark:text-green-400 font-medium">Completed</p>
                    </div>
                  </div>
                  <div className="hidden sm:block text-green-300 dark:text-green-800">→</div>
                  <div className="flex items-center gap-2">
                    <div className="h-5 w-5 rounded-full bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-400 flex items-center justify-center text-[10px]">
                      ✓
                    </div>
                    <div>
                      <p className="text-gray-900 dark:text-gray-100">Report Agent</p>
                      <p className="text-[10px] text-green-600 dark:text-green-400 font-medium">Completed</p>
                    </div>
                  </div>
                </div>
              </div>

              <ReportDetailsCard
                retrievedChunkCount={workflowResult.retrieved_chunk_count}
                filesUsed={workflowResult.files_used}
                retrievalMode={workflowResult.retrieval_mode}
                workflowType="Full AI Workflow"
                timestamp={new Date().toISOString().replace('T', ' ').slice(0, 19)}
                allFiles={files}
              />

              {workflowResult.executive_summary && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    Executive Summary
                  </h3>
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {workflowResult.executive_summary}
                  </p>
                </div>
              )}

              {/* Action Bar */}
              <div className="flex flex-wrap items-center gap-3 bg-white dark:bg-gray-950 p-4 rounded-xl border border-gray-150 dark:border-gray-800">
                {workflowResult.sources && workflowResult.sources.length > 0 && (
                  <button
                    onClick={() => setEvidenceOpen(!evidenceOpen)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                  >
                    <FolderOpenIcon className="w-3.5 h-3.5" />
                    <span>View Sources</span>
                  </button>
                )}
                {workflowResult.saved_report_id && (
                  <>
                    <button
                      onClick={() => handleExportPdf(workflowResult.saved_report_id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                    >
                      <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </button>
                    <button
                      onClick={() => handleExportDocx(workflowResult.saved_report_id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                    >
                      <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                      <span>Download DOCX</span>
                    </button>
                  </>
                )}
              </div>

              {/* Evidence Drawer */}
              {workflowResult.sources && workflowResult.sources.length > 0 && (
                <div className={evidenceOpen ? '' : 'hidden'}>
                  <EvidenceDrawer
                    sources={workflowResult.sources}
                    totalChunks={workflowResult.retrieved_chunk_count ?? undefined}
                    retrievalMode={workflowResult.retrieval_mode ?? undefined}
                    title="Evidence Sources"
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Document selector */}
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

function ReportDetailsCard({
  retrievedChunkCount,
  filesUsed,
  retrievalMode,
  workflowType,
  timestamp,
  allFiles
}: {
  retrievedChunkCount?: number | null
  filesUsed?: string[] | null
  retrievalMode?: string | null
  workflowType: string
  timestamp: string
  allFiles: IndexedFile[]
}) {
  if (retrievedChunkCount === undefined || retrievedChunkCount === null) {
    return (
      <div className="card p-5 space-y-3 border border-gray-200 dark:border-gray-800">
        <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
          Compliance Report Details
        </div>
        <p className="text-xs text-gray-500 italic">Retrieval metadata is Unavailable for this report.</p>
      </div>
    )
  }

  let policies = 0
  let regulations = 0
  let reports = 0
  let general = 0

  if (filesUsed) {
    filesUsed.forEach((fname) => {
      const matchedFile = allFiles.find((f) => f.filename === fname)
      if (matchedFile) {
        const typeLower = matchedFile.document_type.toLowerCase()
        if (typeLower === 'policy') policies++
        else if (typeLower === 'regulation') regulations++
        else if (typeLower === 'report') reports++
        else general++
      } else {
        const fileLower = fname.toLowerCase()
        if (fileLower.includes('policy')) policies++
        else if (fileLower.includes('regulation')) regulations++
        else if (fileLower.includes('report')) reports++
        else general++
      }
    })
  }

  return (
    <div className="card p-5 space-y-3.5 border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
      <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
        Compliance Report Details
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-xs">
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Documents Used</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">
            {filesUsed ? `${filesUsed.length} file${filesUsed.length !== 1 ? 's' : ''}` : 'Unavailable'}
          </p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Policies Count</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{policies}</p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Regulations Count</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{regulations}</p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Reports Count</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{reports}</p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">General Documents</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{general}</p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Retrieved Chunks</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{retrievedChunkCount} chunks</p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Analysis Scope</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5 capitalize">
            {retrievalMode || 'Unavailable'}
          </p>
        </div>
        <div>
          <span className="text-gray-450 dark:text-gray-500 font-medium">Workflow Type</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5 capitalize">{workflowType}</p>
        </div>
        <div className="col-span-2 sm:col-span-1">
          <span className="text-gray-450 dark:text-gray-500 font-medium">Generation Time</span>
          <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{timestamp}</p>
        </div>
      </div>
      <div className="border-t border-gray-150/50 dark:border-gray-800/50 pt-2.5">
        <span className="text-[10px] text-gray-450 dark:text-gray-500 font-medium">
          Retrieved chunk count sourced from actual workflow/retrieval metadata.
        </span>
      </div>
    </div>
  )
}

function ReportCard({
  title,
  risk,
  score,
  violations,
  issues,
  recommendations,
  sources,
}: {
  title: string
  risk: string
  score: number
  violations: number
  issues: string[]
  recommendations: string[]
  sources: any[]
}) {
  const [expandedIssues, setExpandedIssues] = useState<Record<string, boolean>>({})
  const [expandedRecommendations, setExpandedRecommendations] = useState<Record<string, boolean>>({})

  const getEvidenceForFinding = (finding: string) => {
    if (!sources || sources.length === 0) return []
    const findingLower = finding.toLowerCase()

    const matched = sources.filter((src) => {
      const fname = src.filename.toLowerCase()
      const words = findingLower.split(/\W+/)
      const overlaps = words.filter((w) => w.length > 3 && fname.includes(w))
      return overlaps.length > 0 || src.document_type.toLowerCase() === 'policy'
    })

    if (matched.length === 0) {
      return sources.filter((src) => src.document_type.toLowerCase() === 'policy')
    }

    return matched
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h2>
        <div className="flex items-center gap-3">
          <span className={riskBadgeClass(risk)}>{risk} Risk</span>
          <span className={`font-semibold text-sm ${scoreColor(score)}`}>{score}%</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide mb-2">
            Issues ({violations})
          </h3>
          <ul className="space-y-3">
            {issues.length === 0 ? (
              <li className="text-xs text-gray-400">No issues identified</li>
            ) : (
              issues.map((issue, i) => {
                const evidence = getEvidenceForFinding(issue)
                const isExpanded = !!expandedIssues[`issue-${i}`]
                return (
                  <li key={i} className="flex flex-col text-xs text-gray-700 dark:text-gray-300">
                    <div className="flex gap-2">
                      <span className="text-red-500 flex-shrink-0">•</span>
                      <span>{issue}</span>
                    </div>
                    {evidence.length > 0 && (
                      <div className="pl-3.5 mt-1">
                        <button
                          type="button"
                          onClick={() => setExpandedIssues((prev) => ({ ...prev, [`issue-${i}`]: !prev[`issue-${i}`] }))}
                          className="text-[10px] text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-semibold focus:outline-none"
                        >
                          {isExpanded ? 'Hide Supporting Evidence ▲' : 'Show Supporting Evidence ▼'}
                        </button>
                        {isExpanded && (
                          <div className="mt-1.5 p-2.5 rounded-lg bg-gray-50 dark:bg-gray-900/50 border border-gray-150 dark:border-gray-800 text-[10px] space-y-1.5 text-gray-600 dark:text-gray-400 font-medium animate-in fade-in duration-150">
                            {evidence.map((src) => (
                              <div key={src.filename} className="flex justify-between items-center gap-4">
                                <span className="truncate max-w-[70%]" title={src.filename}>
                                  {src.filename} ({src.document_type})
                                </span>
                                <span>
                                  {src.chunks_used !== undefined ? `Chunks: ${src.chunks_used}` : ''}
                                  {src.confidence !== undefined ? ` | Rel: ${src.confidence}%` : ''}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </li>
                )
              })
            )}
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-2">
            Recommendations
          </h3>
          <ul className="space-y-3">
            {recommendations.length === 0 ? (
              <li className="text-xs text-gray-400">No recommendations</li>
            ) : (
              recommendations.map((rec, i) => {
                const evidence = getEvidenceForFinding(rec)
                const isExpanded = !!expandedRecommendations[`rec-${i}`]
                return (
                  <li key={i} className="flex flex-col text-xs text-gray-700 dark:text-gray-300">
                    <div className="flex gap-2">
                      <span className="text-green-500 flex-shrink-0">•</span>
                      <span>{rec}</span>
                    </div>
                    {evidence.length > 0 && (
                      <div className="pl-3.5 mt-1">
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedRecommendations((prev) => ({
                              ...prev,
                              [`rec-${i}`]: !prev[`rec-${i}`],
                            }))
                          }
                          className="text-[10px] text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-semibold focus:outline-none"
                        >
                          {isExpanded ? 'Hide Supporting Evidence ▲' : 'Show Supporting Evidence ▼'}
                        </button>
                        {isExpanded && (
                          <div className="mt-1.5 p-2.5 rounded-lg bg-gray-50 dark:bg-gray-900/50 border border-gray-150 dark:border-gray-800 text-[10px] space-y-1.5 text-gray-600 dark:text-gray-400 font-medium animate-in fade-in duration-150">
                            {evidence.map((src) => (
                              <div key={src.filename} className="flex justify-between items-center gap-4">
                                <span className="truncate max-w-[70%]" title={src.filename}>
                                  {src.filename} ({src.document_type})
                                </span>
                                <span>
                                  {src.chunks_used !== undefined ? `Chunks: ${src.chunks_used}` : ''}
                                  {src.confidence !== undefined ? ` | Rel: ${src.confidence}%` : ''}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </li>
                )
              })
            )}
          </ul>
        </div>
      </div>
    </div>
  )
}
