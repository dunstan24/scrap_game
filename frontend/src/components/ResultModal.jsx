import { useEffect, useState } from 'react'
import { api } from '../api'
import ResultTable from './ResultTable'

export default function ResultModal({ job, onClose }) {
  const [loading, setLoading]   = useState(true)
  const [resultData, setResult] = useState(null)
  const [error, setError]       = useState(null)

  useEffect(() => {
    if (!job) return
    setLoading(true)
    setError(null)
    api.getResult(job.id)
      .then(res => setResult({ data: res.data, total: res.total }))
      .catch(err => setError('Gagal memuat data: ' + err.message))
      .finally(() => setLoading(false))
  }, [job])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (!job) return null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.7)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        animation: 'fadeIn 0.15s ease',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 1100,
          maxHeight: '85vh',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 24px 80px rgba(0,0,0,0.7)',
          animation: 'slideUp 0.2s ease',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className={`job-history-platform platform-badge-${job.platform}`}>{job.platform}</span>
            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
              {job.keyword || '—'}
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              #{job.id} · {resultData ? `${resultData.total} records` : ''}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {resultData && (
              <a
                href={api.downloadUrl(job.id)}
                download target="_blank" rel="noreferrer"
                className="btn-download"
                style={{ padding: '6px 14px', fontSize: '0.8rem' }}
              >
                <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                </svg>
                Download CSV
              </a>
            )}
            <button
              onClick={onClose}
              style={{
                width: 32, height: 32,
                borderRadius: 6,
                border: '1px solid var(--border)',
                background: 'var(--bg-input)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '1rem',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.15s',
                fontFamily: 'inherit',
              }}
              title="Close (Esc)"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, gap: 12, color: 'var(--text-muted)' }}>
              <span className="spinner" style={{ borderTopColor: 'var(--accent)', borderColor: 'rgba(59,130,246,0.3)' }} />
              Memuat data...
            </div>
          ) : error ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--error)' }}>
              {error}
            </div>
          ) : (
            <ResultTable
              data={resultData?.data || []}
              total={resultData?.total || 0}
              jobId={job.id}
              fileName={job.file_name}
              hideDownload
            />
          )}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
        @keyframes slideUp { from { transform: translateY(16px); opacity: 0 } to { transform: translateY(0); opacity: 1 } }
      `}</style>
    </div>
  )
}
