import { useState, useEffect } from 'react'
import { api } from '../api'
import ResultModal from '../components/ResultModal'

const PLATFORMS  = ['all', 'pcgamingwiki']
const STATUSES   = ['all', 'done', 'running', 'error', 'queued']
const PAGE_SIZE  = 15

function PlatformBadge({ platform }) {
  return <span className={`job-history-platform platform-badge-${platform}`}>{platform}</span>
}
function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`}>{status}</span>
}
function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('id-ID', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}
function duration(start, end) {
  if (!start || !end) return '—'
  const ms = new Date(end) - new Date(start)
  const m  = Math.floor(ms / 60000)
  const s  = Math.floor((ms % 60000) / 1000)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export default function HistoryPage() {
  const [jobs, setJobs]             = useState([])
  const [loading, setLoading]       = useState(true)
  const [filterPlatform, setFP]     = useState('all')
  const [filterStatus, setFS]       = useState('all')
  const [search, setSearch]         = useState('')
  const [page, setPage]             = useState(1)
  const [sortCol, setSortCol]       = useState('id')
  const [sortDir, setSortDir]       = useState('desc')
  const [selectedJob, setSelected]  = useState(null)   // modal

  const refresh = async () => {
    setLoading(true)
    try {
      const list = await api.listJobs()
      setJobs(list || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  // Filter + sort
  const filtered = jobs
    .filter(j => filterPlatform === 'all' || j.platform === filterPlatform)
    .filter(j => filterStatus   === 'all' || j.status   === filterStatus)
    .filter(j => !search || (j.start_url || '').toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      let va = a[sortCol], vb = b[sortCol]
      if (typeof va === 'string') va = va.toLowerCase()
      if (typeof vb === 'string') vb = vb.toLowerCase()
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
  }

  // Stats
  const totalJobs    = jobs.length
  const totalRecords = jobs.reduce((s, j) => s + (j.total_found || 0), 0)
  const doneCount    = jobs.filter(j => j.status === 'done').length
  const errorCount   = jobs.filter(j => j.status === 'error').length

  const SortIcon = ({ col }) => {
    if (sortCol !== col) return <span style={{ opacity: 0.3, fontSize: '0.65rem' }}>↕</span>
    return <span style={{ color: 'var(--accent)', fontSize: '0.65rem' }}>{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── Stats Row ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Total Jobs',    value: totalJobs,    color: 'var(--accent)',   icon: '⚙' },
          { label: 'Total Records', value: totalRecords, color: 'var(--success)',  icon: '📄' },
          { label: 'Completed',     value: doneCount,    color: 'var(--success)',  icon: '✓' },
          { label: 'Failed',        value: errorCount,   color: 'var(--error)',    icon: '✗' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', padding: '14px 16px',
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6 }}>
              {stat.icon} {stat.label}
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: stat.color }}>
              {loading ? '—' : stat.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <input
          className="input-field"
          style={{ flex: 1, minWidth: 180, maxWidth: 280 }}
          placeholder="Search URL..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
        />

        <select
          className="input-field"
          style={{ width: 130 }}
          value={filterPlatform}
          onChange={e => { setFP(e.target.value); setPage(1) }}
        >
          {PLATFORMS.map(p => <option key={p} value={p}>{p === 'all' ? 'All Platforms' : p}</option>)}
        </select>

        <select
          className="input-field"
          style={{ width: 130 }}
          value={filterStatus}
          onChange={e => { setFS(e.target.value); setPage(1) }}
        >
          {STATUSES.map(s => <option key={s} value={s}>{s === 'all' ? 'All Status' : s}</option>)}
        </select>

        <button
          onClick={refresh}
          className="btn-download"
          style={{ padding: '8px 14px' }}
        >
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M1 4v6h6M23 20v-6h-6"/><path d="M3.51 9a9 9 0 0115..." />
            <path d="M20.49 15A9 9 0 115.64 5.64L1 10M23 14l-4.36 4.36A9 9 0 013.51 9"/>
          </svg>
          Refresh
        </button>

        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* ── Table ── */}
      <div style={{ flex: 1, overflow: 'auto', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--text-muted)', gap: 10 }}>
            <span className="spinner" style={{ borderTopColor: 'var(--accent)', borderColor: 'rgba(59,130,246,0.3)' }} />
            Loading...
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                {[
                  { col: 'id',          label: 'ID' },
                  { col: 'platform',    label: 'Platform' },
                  { col: 'start_url',   label: 'Starting URL' },
                  { col: 'status',      label: 'Status' },
                  { col: 'total_found', label: 'Records' },
                  { col: 'started_at',  label: 'Started' },
                  { col: 'finished_at', label: 'Duration' },
                  { col: 'file_name',   label: 'File' },
                ].map(({ col, label }) => (
                  <th key={col} onClick={() => handleSort(col)} style={{ cursor: 'pointer', userSelect: 'none' }}>
                    {label} <SortIcon col={col} />
                  </th>
                ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginated.length === 0 ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  No results found
                </td></tr>
              ) : paginated.map(job => (
                <tr key={job.id}>
                  <td style={{ color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.7rem' }}>
                    #{job.id}
                  </td>
                  <td><PlatformBadge platform={job.platform} /></td>
                  <td className="td-title" title={job.start_url}>{job.start_url ? job.start_url.split('/').pop() : '—'}</td>
                  <td><StatusBadge status={job.status} /></td>
                  <td style={{ color: job.total_found > 0 ? 'var(--success)' : 'var(--text-muted)', fontWeight: 600 }}>
                    {job.total_found > 0 ? job.total_found.toLocaleString() : '—'}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                    {formatDate(job.started_at)}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    {duration(job.started_at, job.finished_at)}
                  </td>
                  <td style={{ maxWidth: 160 }}>
                    {job.file_name
                      ? <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          {job.file_name.slice(0, 32)}{job.file_name.length > 32 ? '…' : ''}
                        </span>
                      : <span style={{ color: 'var(--text-muted)' }}>—</span>
                    }
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      {(job.status === 'done' || ((job.status === 'error' || job.status === 'cancelled') && job.output_file)) && (
                        <>
                          <button
                            onClick={() => setSelected(job)}
                            style={{
                              padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)',
                              background: 'var(--bg-input)', color: 'var(--text-secondary)',
                              fontSize: '0.72rem', cursor: 'pointer', transition: 'all 0.15s',
                              fontFamily: 'inherit'
                            }}
                            onMouseOver={e => { e.target.style.borderColor = 'var(--accent)'; e.target.style.color = '#93c5fd' }}
                            onMouseOut={e => { e.target.style.borderColor = 'var(--border)';  e.target.style.color = 'var(--text-secondary)' }}
                          >
                            View
                          </button>
                          <a
                            href={api.downloadUrl(job.id)}
                            download
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)',
                              background: 'var(--bg-input)', color: job.status === 'done' ? 'var(--success)' : 'var(--warning, #f59e0b)',
                              fontSize: '0.72rem', cursor: 'pointer', transition: 'all 0.15s',
                              textDecoration: 'none', display: 'inline-block'
                            }}
                          >
                            ↓ CSV
                          </a>
                          {job.status !== 'done' && (
                            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginLeft: 4 }}>
                              (partial)
                            </span>
                          )}
                        </>
                      )}
                      {job.status === 'error' && !job.output_file && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--error)' }}>Failed</span>
                      )}
                      {job.status === 'cancelled' && !job.output_file && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Cancelled</span>
                      )}
                      {job.status === 'running' && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--accent)' }}>Running…</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-download" style={{ padding: '6px 12px' }}>←</button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
            <button key={n} onClick={() => setPage(n)} style={{
              width: 32, height: 32, borderRadius: 6, border: '1px solid',
              borderColor: page === n ? 'var(--accent)' : 'var(--border)',
              background: page === n ? 'var(--accent-glow)' : 'var(--bg-input)',
              color: page === n ? '#93c5fd' : 'var(--text-muted)',
              fontSize: '0.8rem', cursor: 'pointer', fontFamily: 'inherit'
            }}>{n}</button>
          ))}
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-download" style={{ padding: '6px 12px' }}>→</button>
        </div>
      )}

      {/* ── Result Modal ── */}
      {selectedJob && (
        <ResultModal job={selectedJob} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
