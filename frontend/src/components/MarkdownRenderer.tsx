import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none 
                    prose-headings:font-bold prose-h1:text-lg prose-h1:text-brand-700 dark:prose-h1:text-brand-400 prose-h1:uppercase prose-h1:tracking-wider prose-h1:border-b prose-h1:border-gray-200 dark:prose-h1:border-gray-800 prose-h1:pb-2
                    prose-table:w-full prose-table:border-collapse prose-table:my-4
                    prose-th:bg-gray-100 dark:prose-th:bg-gray-800 prose-th:p-3 prose-th:text-left prose-th:font-semibold prose-th:border prose-th:border-gray-200 dark:prose-th:border-gray-700
                    prose-td:p-3 prose-td:border prose-td:border-gray-200 dark:prose-td:border-gray-800 prose-td:align-top
                    prose-li:my-0.5">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || ''}
      </ReactMarkdown>
    </div>
  )
}
