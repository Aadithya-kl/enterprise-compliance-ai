import type { IndexedFile } from '../types/audit'
import type { SourceItem } from '../components/common/SourceAttributionPanel'

export function simulateSourcesForReport(indexedFiles: IndexedFile[], reportId?: number): SourceItem[] {
  if (!indexedFiles || indexedFiles.length === 0) {
    return [
      {
        filename: 'GDPR Regulation Standard.pdf',
        document_type: 'regulation',
        chunks_used: 4,
        confidence: 91.2
      },
      {
        filename: 'Internal Data Security Policy.docx',
        document_type: 'policy',
        chunks_used: 3,
        confidence: 82.5
      },
      {
        filename: 'Access Control Guidelines.txt',
        document_type: 'general',
        chunks_used: 2,
        confidence: 64.7
      }
    ]
  }

  const seed = reportId || 42

  return indexedFiles.map((file, idx) => {
    // Generate a relevance score based on file name or type and reportId to add pseudo-realism
    const nameVal = file.filename.charCodeAt(0) + file.filename.charCodeAt(file.filename.length - 1)
    const rawConf = 5 + ((nameVal + seed * (idx + 1)) % 91) // between 5% and 95%
    const confidence = parseFloat(rawConf.toFixed(1))

    // Chunks used: between 1 and 6
    const chunksUsed = 1 + ((nameVal + seed + idx) % 6)

    return {
      filename: file.filename,
      document_type: file.document_type,
      chunks_used: chunksUsed,
      confidence: confidence
    }
  }).sort((a, b) => b.confidence - a.confidence)
}
