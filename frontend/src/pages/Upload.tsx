import { useRef, useState } from 'react'
import { documentsApi } from '../api/documents'
import type { UploadResponse } from '../types/audit'

const DOCUMENT_TYPES = [
  { value: 'policy',     label: 'Company Policy' },
  { value: 'regulation', label: 'Regulation / Standard' },
  { value: 'general',    label: 'General Document' },
]

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [docType, setDocType] = useState('policy')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (dropped?.name.toLowerCase().endsWith('.pdf')) {
      setFile(dropped)
      setError('')
    } else {
      setError('Only PDF files are accepted.')
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
      setError('')
    }
  }

  const handleUpload = async () => {
    if (!file) { setError('Please select a file.'); return }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await documentsApi.upload(file, docType)
      setResult(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Upload failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-5">
      <div>
        <h1 className="page-heading">Upload Documents</h1>
        <p className="page-subheading mt-1">
          Upload PDF policy or regulation documents for AI-powered compliance analysis.
        </p>
      </div>

      {/* Document type selector */}
      <div className="card p-5">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Document Type
        </label>
        <div className="flex gap-3">
          {DOCUMENT_TYPES.map((dt) => (
            <button
              key={dt.value}
              onClick={() => setDocType(dt.value)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                docType === dt.value
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {dt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={`card p-8 border-2 border-dashed transition-colors cursor-pointer ${
          file
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/10'
            : 'border-gray-300 dark:border-gray-700 hover:border-brand-400'
        }`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />
        <div className="text-center">
          <svg className="mx-auto w-10 h-10 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {file ? (
            <div>
              <p className="font-medium text-brand-600 dark:text-brand-400">{file.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Drop a PDF here, or click to browse
              </p>
              <p className="text-xs text-gray-400 mt-1">Maximum file size: 50 MB</p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="btn-primary"
      >
        {loading ? 'Processing...' : 'Upload and Ingest'}
      </button>

      {/* Result */}
      {result && (
        <div className="card p-5 border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10">
          <p className="text-sm font-semibold text-green-800 dark:text-green-400 mb-3">
            Document ingested successfully
          </p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Filename</span>
              <p className="font-medium text-gray-900 dark:text-white">{result.filename}</p>
            </div>
            <div>
              <span className="text-gray-500">Document Type</span>
              <p className="font-medium text-gray-900 dark:text-white">{result.document_type}</p>
            </div>
            <div>
              <span className="text-gray-500">Characters Extracted</span>
              <p className="font-medium text-gray-900 dark:text-white">{result.characters.toLocaleString()}</p>
            </div>
            <div>
              <span className="text-gray-500">Chunks Stored</span>
              <p className="font-medium text-gray-900 dark:text-white">{result.chunks}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
