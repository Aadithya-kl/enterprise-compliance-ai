import client from './client'

export interface MCPStatsResponse {
  sources_connected: number
  total_documents: number
  total_chunks: number
  last_sync: string
}

export interface HealthResponse {
  database: string
  qdrant: string
  supabase: string
  llm: string
  google_drive: string
  notion: string
  backend: string
}

export interface VerifyResponse {
  connected: boolean
  message: string
  [key: string]: unknown
}

export interface SyncResponse {
  job_id: string
  status: string
}

export interface SyncStatus {
  job_id: string
  status: string
  documents_processed: number
  total_documents: number
  chunks_generated: number
  started_at: string
  completed_at: string | null
}

export const integrationsApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const res = await client.get<HealthResponse>('/health')
    return res.data
  },

  getMcpStats: async (): Promise<Record<string, MCPStatsResponse>> => {
    const res = await client.get<Record<string, MCPStatsResponse>>('/mcp/stats')
    return res.data
  },

  verifyGoogleDrive: async (): Promise<VerifyResponse> => {
    const res = await client.get<VerifyResponse>('/mcp/google-drive/verify')
    return res.data
  },

  syncGoogleDrive: async (): Promise<SyncResponse> => {
    const res = await client.post<SyncResponse>('/mcp/google-drive/sync')
    return res.data
  },

  verifyNotion: async (): Promise<VerifyResponse> => {
    const res = await client.get<VerifyResponse>('/mcp/notion/verify')
    return res.data
  },

  syncNotion: async (): Promise<SyncResponse> => {
    const res = await client.post<SyncResponse>('/mcp/notion/sync')
    return res.data
  },

  getSyncStatus: async (jobId: string): Promise<SyncStatus> => {
    const res = await client.get<SyncStatus>(`/mcp/sync/status/${jobId}`)
    return res.data
  },

  getIntegrations: async (): Promise<Record<string, boolean>> => {
    const res = await client.get<Record<string, boolean>>('/mcp/integrations')
    return res.data
  },

  toggleIntegration: async (sourceName: string, isEnabled: boolean): Promise<{ status: string, source: string, is_enabled: boolean }> => {
    const res = await client.patch<{ status: string, source: string, is_enabled: boolean }>(`/mcp/integrations/${sourceName}`, { is_enabled: isEnabled })
    return res.data
  },

  exportReportPdf: async (id: number) => {
    const res = await client.get(`/reports/${id}/export/pdf`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Compliance_Report_${id}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.parentNode?.removeChild(link)
  },
  
  exportReportDocx: async (id: number) => {
    const res = await client.get(`/reports/${id}/export/docx`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Compliance_Report_${id}.docx`)
    document.body.appendChild(link)
    link.click()
    link.parentNode?.removeChild(link)
  }
}
