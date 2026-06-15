import client from './client'
import type { QuestionResponse, UploadResponse, IndexedFile } from '../types/audit'

export const documentsApi = {
  upload: async (file: File, document_type: string, replace: boolean = false): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await client.post<UploadResponse>(
      `/documents/upload?document_type=${encodeURIComponent(document_type)}&replace=${replace}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return res.data
  },

  getCount: async (document_type: string): Promise<number> => {
    const res = await client.get(`/documents/${document_type}/count`)
    return res.data.documents_found
  },

  ask: async (question: string, selectedFiles?: string[]): Promise<QuestionResponse> => {
    const res = await client.post<QuestionResponse>('/documents/ask', {
      question,
      selected_files: selectedFiles || null,
    })
    return res.data
  },

  getIndexedFiles: async (): Promise<IndexedFile[]> => {
    const res = await client.get<{ files: IndexedFile[]; total: number }>('/documents/indexed-files')
    return res.data.files
  },

  analyze: async (): Promise<{ analysis: string }> => {
    const res = await client.post<{ analysis: string }>('/documents/analyze')
    return res.data
  },
}
