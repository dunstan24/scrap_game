import { api } from '../api'

const PRIORITY_COLS = [
  'title', 'employer_company_name', 'location', 'state', 'type',
  'salary_min', 'salary_max', 'salary_type', 'description',
  'employer_phone_number', 'sponsorship', 'source', 'scraping_timestamp'
]

function prioritizeColumns(cols) {
  const priority = PRIORITY_COLS.filter(c => cols.includes(c))
  const rest = cols.filter(c => !PRIORITY_COLS.includes(c))
  return [...priority, ...rest]
}

function formatHeader(col) {
  return col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function cellClass(col) {
  if (col === 'title') return 'td-title'
  if (col.includes('salary')) return 'td-salary'
  if (col === 'source') return 'td-link'
  return ''
}

function isValidUrl(str) {
  try {
    new URL(str)
    return true
  } catch {
    return false
  }
}

export default function ResultTable({ data = [], jobId, fileName, total, hideDownload = false }) {
  if (!data.length) {
    return (
      <div className="table-wrap">
        <div className="no-data">
          <svg width="56" height="56" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24" style={{ opacity: 0.3 }}>
            <path d="M3 3h18v4H3zM3 9h18v4H3zM3 15h18v4H3z"/>
          </svg>
          <p>Belum ada data. Jalankan scraping terlebih dahulu.</p>
        </div>
      </div>
    )
  }

  const allCols  = Object.keys(data[0])
  const cols     = prioritizeColumns(allCols)
  const downloadUrl = api.downloadUrl(jobId)

  return (
    <div className="table-wrap">
      <div className="table-toolbar">
        <p className="table-info">
          Menampilkan <span>{data.length}</span> dari <span>{total}</span> job
          {fileName && <> &nbsp;·&nbsp; <span>{fileName}</span></>}
        </p>
        {!hideDownload && (
          <a href={downloadUrl} download className="btn-download" target="_blank" rel="noreferrer">
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
            </svg>
            Download CSV
          </a>
        )}
      </div>

      <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid var(--border)' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 36 }}>#</th>
              {cols.map(c => <th key={c}>{formatHeader(c)}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.7rem' }}>{i + 1}</td>
                {cols.map(c => (
                  <td key={c} className={cellClass(c)} title={String(row[c] ?? '')}>
                    {row[c] === null || row[c] === undefined || row[c] === 'N/A' || row[c] === ''
                      ? <span style={{ color: 'var(--text-muted)' }}>—</span>
                      : c === 'source' && isValidUrl(String(row[c]))
                      ? <a 
                          href={String(row[c])} 
                          target="_blank" 
                          rel="noreferrer"
                          style={{
                            color: 'var(--accent, #3b82f6)',
                            textDecoration: 'none',
                            cursor: 'pointer',
                            borderBottom: '1px solid rgba(59,130,246,0.5)',
                            transition: 'all 0.2s'
                          }}
                          onMouseOver={e => {
                            e.target.style.color = 'var(--accent-bright, #60a5fa)'
                            e.target.style.borderBottomColor = 'rgba(59,130,246,1)'
                          }}
                          onMouseOut={e => {
                            e.target.style.color = 'var(--accent, #3b82f6)'
                            e.target.style.borderBottomColor = 'rgba(59,130,246,0.5)'
                          }}
                        >
                          {String(row[c]).length > 50 ? `${String(row[c]).substring(0, 47)}...` : String(row[c])}
                        </a>
                      : String(row[c])
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
