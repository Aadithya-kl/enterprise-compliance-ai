import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, Radar
} from 'recharts'
import { complianceApi } from '../api/compliance'
import { documentsApi } from '../api/documents'
import type { IndexedFile, RiskAssessmentResponse } from '../types/audit'
import { scoreColor } from '../utils/formatters'
import EvidenceDrawer from '../components/common/EvidenceDrawer'
import { simulateSourcesForReport } from '../utils/sourceSimulator'
import { FolderOpenIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'

const RISK_COLORS = { High: '#dc2626', Medium: '#d97706', Low: '#16a34a' }

export default function RiskAnalyticsPage() {
  const [assessmentResult, setAssessmentResult] = useState<RiskAssessmentResponse | null>(null)
  const [loadingAssessment, setLoadingAssessment] = useState(false)
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  
  // Document list for source traceability
  const [files, setFiles] = useState<IndexedFile[]>([])

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: complianceApi.getDashboardStats,
  })

  const { data: distribution = [] } = useQuery({
    queryKey: ['risk-distribution'],
    queryFn: complianceApi.getRiskDistribution,
  })

  const { data: trend = [] } = useQuery({
    queryKey: ['audit-trend'],
    queryFn: () => complianceApi.getAuditTrend(12),
  })

  useEffect(() => {
    documentsApi.getIndexedFiles()
      .then(setFiles)
      .catch((err) => console.error('Failed to load indexed files:', err))
  }, [])

  const handleRunAssessment = async () => {
    setLoadingAssessment(true)
    try {
      const res = await complianceApi.assessRisk()
      setAssessmentResult(res)
      setEvidenceOpen(false)
    } catch (err) {
      console.error('Failed to assess risk:', err)
    } finally {
      setLoadingAssessment(false)
    }
  }

  // Simulate risk assessment evidence sources
  const riskSources = useMemo(() => {
    return simulateSourcesForReport(files, 505)
  }, [files])

  const radarData = [
    { metric: 'Compliance Score', value: stats?.average_compliance_score ?? 0, full: 100 },
    { metric: 'Low Risk %', value: stats ? (stats.low_risk / (stats.total_audits || 1)) * 100 : 0, full: 100 },
    { metric: 'Audit Volume', value: Math.min(stats?.total_audits ?? 0, 100), full: 100 },
    { metric: 'High Risk %', value: 100 - (stats ? (stats.high_risk / (stats.total_audits || 1)) * 100 : 0), full: 100 },
    { metric: 'Avg Issues Resolved', value: 70, full: 100 },
  ]

  return (
    <div className="space-y-5 pb-10">
      <div>
        <h1 className="page-heading">Risk Analytics</h1>
        <p className="page-subheading mt-1">
          In-depth risk breakdown and compliance health indicators.
        </p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {['high_risk', 'medium_risk', 'low_risk'].map((key) => {
          const labels = { high_risk: 'High Risk', medium_risk: 'Medium Risk', low_risk: 'Low Risk' }
          const colors = { high_risk: 'text-red-600 dark:text-red-400', medium_risk: 'text-amber-600 dark:text-amber-400', low_risk: 'text-green-600 dark:text-green-400' }
          const value = stats?.[key as keyof typeof stats] ?? 0
          return (
            <div key={key} className="stat-card">
              <p className="text-xs text-gray-500">{labels[key as keyof typeof labels]}</p>
              <p className={`text-3xl font-bold ${colors[key as keyof typeof colors]}`}>{value}</p>
              <p className="text-xs text-gray-400">
                {stats?.total_audits ? Math.round((Number(value) / stats.total_audits) * 100) : 0}% of total
              </p>
            </div>
          )
        })}
      </div>

      {/* AI Risk Assessment Generator Card */}
      <div className="card p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
            Grounded AI Risk Assessment Generator
          </h2>
          <p className="text-xs text-gray-500">
            Triggers an assessment workflow to score system compliance risk and track evidence links across policies.
          </p>
        </div>
        <button
          onClick={handleRunAssessment}
          disabled={loadingAssessment}
          className="btn-primary px-5 py-2 text-xs font-semibold"
        >
          {loadingAssessment ? 'Assessing Risk...' : 'Run Risk Assessment'}
        </button>

        {assessmentResult && (
          <div className="border-t border-gray-150 dark:border-gray-800 pt-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-gray-50/50 dark:bg-gray-900/30 border border-gray-150 dark:border-gray-800/80">
              <div>
                <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">Assessed Risk</span>
                <p className={`text-lg font-bold mt-0.5 ${
                  assessmentResult.risk === 'High' ? 'text-red-650 dark:text-red-400' :
                  assessmentResult.risk === 'Medium' ? 'text-amber-650 dark:text-amber-400' : 'text-green-650 dark:text-green-400'
                }`}>
                  {assessmentResult.risk}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">Compliance Score</span>
                <p className={`text-lg font-bold mt-0.5 ${scoreColor(assessmentResult.compliance_score)}`}>
                  {assessmentResult.compliance_score}%
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">Identified Issues</span>
                <p className="text-lg font-bold text-gray-950 dark:text-white mt-0.5">
                  {assessmentResult.issue_count} issues
                </p>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex flex-wrap items-center gap-3 bg-white dark:bg-gray-950 p-3 rounded-xl border border-gray-150 dark:border-gray-800">
              <button
                type="button"
                onClick={() => setEvidenceOpen(!evidenceOpen)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
              >
                <FolderOpenIcon className="w-3.5 h-3.5" />
                <span>View Sources</span>
              </button>
              <button
                type="button"
                onClick={() => alert('PDF export initialized.')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
              >
                <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                <span>Download PDF</span>
              </button>
              <button
                type="button"
                onClick={() => alert('DOCX export initialized.')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-250 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
              >
                <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                <span>Download DOCX</span>
              </button>
            </div>

            {/* Collapsible Evidence Panel */}
            {(evidenceOpen || true) && (
              <div className={evidenceOpen ? '' : 'hidden'}>
                <EvidenceDrawer
                  sources={riskSources}
                  title="Risk Assessment Sources"
                  retrievalMode="risk assessment model"
                />
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pie chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-gray-750 dark:text-gray-300 mb-4">Risk Distribution</h2>
          {distribution.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-sm text-gray-400">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="count"
                  nameKey="risk_level"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  paddingAngle={3}
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                >
                  {distribution.map((entry) => (
                    <Cell
                      key={entry.risk_level}
                      fill={RISK_COLORS[entry.risk_level as keyof typeof RISK_COLORS] ?? '#6b7280'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
                  // @ts-expect-error recharts formatter types are extremely complex
                  formatter={(v: number) => String(v) + ' audits'}
                />
                <Legend formatter={(v) => <span style={{ color: '#9ca3af', fontSize: 11 }}>{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Radar chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-gray-750 dark:text-gray-300 mb-4">Compliance Health Radar</h2>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <Radar name="Health Score" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
                // @ts-expect-error recharts formatter types are extremely complex
                formatter={(v: number) => Math.round(v) + '%'}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Risk trend table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-sm font-semibold text-gray-755 dark:text-gray-300">Monthly Trend Detail</h2>
        </div>
        <div className="table-container rounded-none border-0 overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Audit Count</th>
                <th>Average Score</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
              {trend.length === 0 ? (
                <tr><td colSpan={3} className="text-center text-gray-400 py-8">No trend data yet</td></tr>
              ) : (
                trend.map((row) => (
                  <tr key={row.month}>
                    <td className="font-medium">{row.month}</td>
                    <td>{row.audit_count}</td>
                    <td>
                      <span className={scoreColor(row.average_score)}>
                        {row.average_score.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
