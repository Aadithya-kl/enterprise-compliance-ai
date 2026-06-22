import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { complianceApi } from '../api/compliance'
import { documentsApi } from '../api/documents'
import type { AuditReport, IndexedFile } from '../types/audit'
import { riskBadgeClass, scoreColor } from '../utils/formatters'
import { useAuth } from '../store/authStore'
import { integrationsApi } from '../api/integrations'
import EvidenceDrawer from '../components/common/EvidenceDrawer'
import { simulateSourcesForReport } from '../utils/sourceSimulator'

export default function AuditHistoryPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<AuditReport | null>(null)
  
  // Document list for source simulation
  const [files, setFiles] = useState<IndexedFile[]>([])

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['audit-history'],
    queryFn: () => complianceApi.listAuditReports(0, 100),
  })

  useEffect(() => {
    documentsApi.getIndexedFiles()
      .then(setFiles)
      .catch((err) => console.error('Failed to load indexed files:', err))
  }, [])

  const deleteMutation = useMutation({
    mutationFn: (id: number) => complianceApi.deleteAuditReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit-history'] })
      setSelected(null)
    },
  })

  const loadReport = async (id: number) => {
    const report = await complianceApi.getAuditReport(id)
    setSelected(report)
  }

  // Calculate simulated sources for selected report
  const reportSources = useMemo(() => {
    if (!selected) return []
    return simulateSourcesForReport(files, selected.id)
  }, [files, selected])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-heading">Audit History</h1>
        <p className="page-subheading mt-1">
          Complete log of all compliance audit reports.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* List */}
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {reports.length} report{reports.length !== 1 ? 's' : ''}
            </span>
          </div>
          {isLoading ? (
            <div className="p-8 text-center text-sm text-gray-400">Loading...</div>
          ) : reports.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center">
                <svg className="w-6 h-6 text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-200">No Audit Reports</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Your historical compliance audits will appear here.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-800">
              {reports.map((r) => (
                <li
                  key={r.id}
                  className={`px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                    selected?.id === r.id ? 'bg-brand-50 dark:bg-brand-950/20' : ''
                  }`}
                  onClick={() => loadReport(r.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={riskBadgeClass(r.risk)}>{r.risk}</span>
                      <span className="font-mono text-xs text-gray-400">#{r.id}</span>
                    </div>
                    <span className={`text-sm font-semibold ${scoreColor(r.compliance_score)}`}>
                      {r.compliance_score}%
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {r.audit_timestamp} · {r.violation_count} violations
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Detail */}
        {selected ? (
          <div className="card p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Audit Report #{selected.id}
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">{selected.audit_timestamp}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={riskBadgeClass(selected.risk)}>{selected.risk}</span>
                <div className="flex flex-wrap gap-1">
                  <button onClick={() => integrationsApi.exportReportPdf(selected.id)} className="btn-secondary text-xs px-2 py-1">Export PDF</button>
                  <button onClick={() => integrationsApi.exportReportDocx(selected.id)} className="btn-secondary text-xs px-2 py-1">Export DOCX</button>
                </div>
                {(user?.role === 'admin' || user?.role === 'compliance_officer') && (
                  <button
                    onClick={() => deleteMutation.mutate(selected.id)}
                    disabled={deleteMutation.isPending}
                    className="btn-danger text-xs px-2 py-1"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-xs text-gray-500">Score</p>
                <p className={`text-xl font-bold ${scoreColor(selected.compliance_score)}`}>
                  {selected.compliance_score}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Violations</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {selected.violation_count}
                </p>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide mb-2">
                Issues
              </p>
              {(selected.issues || []).length === 0 ? (
                <p className="text-xs text-gray-400">No issues</p>
              ) : (
                <ul className="space-y-1">
                  {(selected.issues || []).map((issue, i) => (
                    <li key={i} className="flex gap-2 text-xs text-gray-700 dark:text-gray-300">
                      <span className="text-red-500">•</span>{issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <p className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-2">
                Recommendations
              </p>
              {(selected.recommendations || []).length === 0 ? (
                <p className="text-xs text-gray-400">No recommendations</p>
              ) : (
                <ul className="space-y-1">
                  {(selected.recommendations || []).map((rec, i) => (
                    <li key={i} className="flex gap-2 text-xs text-gray-700 dark:text-gray-300">
                      <span className="text-green-500">•</span>{rec}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="border-t border-gray-150 dark:border-gray-800/80 pt-4" />

            {/* Collapsible Evidence Panel */}
            <EvidenceDrawer
              sources={reportSources}
              title="Evidence Sources"
              retrievalMode="audit history logs"
            />
          </div>
        ) : (
          <div className="card p-8 flex items-center justify-center text-sm text-gray-400">
            Select an audit report to view details
          </div>
        )}
      </div>
    </div>
  )
}
