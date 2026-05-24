import { useState, useEffect } from 'react'
import { api } from './api'
import iconImg from './assets/icon.png'
import ScrapeForm from './components/ScrapeForm'
import LogPanel from './components/LogPanel'
import ResultTable from './components/ResultTable'
import HistoryPage from './pages/HistoryPage'
import './index.css'

const POLL_INTERVAL = 2500

function StatusDot({ status }) {
  const cls = status === 'done'      ? ''
            : status === 'running'   ? 'running'
            : status === 'paused'    ? 'paused'
            : status === 'error'     ? 'error'
            : status === 'cancelled' ? 'error'
            : 'idle'
  return <span className={`status-dot ${cls}`} />
}


function PlatformBadge({ platform }) {
  return <span className={`job-history-platform platform-badge-${platform}`}>{platform}</span>
}
function StatusBadge({ status }) {
  const label = status === 'cancelled' ? 'cancelled' : status
  return <span className={`status-badge status-${status}`}>{label}</span>
}


export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [activeJob, setActiveJob]     = useState(null)
  const [jobs, setJobs]               = useState([])
  const [resultData, setResultData]   = useState(null)
  const [tab, setTab]                 = useState('logs')
  const [scraping, setScraping]       = useState(false)
  const [theme, setTheme]             = useState(
    () => localStorage.getItem('theme') || 'dark'
  )
  const [cancelling, setCancelling] = useState(false)
  const [pausing, setPausing]       = useState(false)

  // Apply theme to <html>
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  useEffect(() => {
    api.listJobs().then(list => setJobs(list || [])).catch(() => {})
  }, [])

  // Polling
  useEffect(() => {
    if (!activeJob) return
    if (['done', 'error', 'cancelled'].includes(activeJob.status)) return
    // Tetap poll saat paused agar log update terlihat
    const timer = setInterval(async () => {
      try {
        const status = await api.getStatus(activeJob.job_id)
        setActiveJob(prev => prev ? { ...prev, ...status } : status)
        if (status.status === 'done') {
          setScraping(false)
          setPausing(false)
          fetchResult(activeJob.job_id)
          refreshHistory()
        }
        if (status.status === 'error') {
          setScraping(false)
          setPausing(false)
          // Fetch result jika ada partial file
          if (status.output_file) {
            fetchResult(activeJob.job_id)
          }
          refreshHistory()
        }
        if (status.status === 'cancelled') {
          setScraping(false)
          setPausing(false)
          // Fetch result jika ada partial file
          if (status.output_file) {
            fetchResult(activeJob.job_id)
          }
          refreshHistory()
        }
      } catch { /* ignore */ }
    }, POLL_INTERVAL)

    return () => clearInterval(timer)
  }, [activeJob])

  const fetchResult = async (jobId) => {
    try {
      const res = await api.getResult(jobId)
      setResultData({ data: res.data, total: res.total })
      setTab('results')
    } catch { /* ignore */ }
  }

  const refreshHistory = async () => {
    try {
      const list = await api.listJobs()
      setJobs(list || [])
    } catch { /* ignore */ }
  }

  const handlePause = async () => {
    if (!activeJob) return
    setPausing(true)
    try {
      await api.pauseJob(activeJob.job_id)
      setActiveJob(prev => prev ? { ...prev, status: 'paused' } : prev)
    } catch (err) {
      alert('Gagal menjeda: ' + err.message)
    } finally {
      setPausing(false)
    }
  }

  const handleResume = async () => {
    if (!activeJob) return
    setPausing(true)
    try {
      await api.resumeJob(activeJob.job_id)
      setActiveJob(prev => prev ? { ...prev, status: 'running' } : prev)
    } catch (err) {
      alert('Gagal melanjutkan: ' + err.message)
    } finally {
      setPausing(false)
    }
  }

  const handleSubmit = async (payload) => {
    setScraping(true)
    setResultData(null)
    setTab('logs')
    setCurrentPage('dashboard')
    try {
      const res = await api.startScrape(payload)
      setActiveJob({
        job_id:      res.job_id,
        platform:    payload.platform,
        start_url:   payload.start_url,
        status:      'queued',
        progress:    0,
        total_found: 0,
        logs:        [],
        error:       null,
      })
      refreshHistory()
    } catch (err) {
      setScraping(false)
      alert('Gagal memulai scraping: ' + err.message)
    }
  }

  const handleSelectJob = async (job) => {
    const jobId = job.id ?? job.job_id
    setActiveJob({
      job_id:      jobId,
      platform:    job.platform,
      start_url:   job.start_url,
      status:      job.status,
      progress:    job.progress || 0,
      total_found: job.total_found,
      logs:        [],
      error:       null,
      output_file: job.output_file,
      file_name:   job.file_name,
    })
    setResultData(null)
    setTab('logs')
    setCurrentPage('dashboard')
    if (job.status === 'done') {
      await fetchResult(jobId)
    }
  }

  const handleCancel = async () => {
    if (!activeJob || !activeJob.job_id) return
    if (!window.confirm('Batalkan scraping job ini?')) return

    setCancelling(true)
    try {
      await api.cancelScrape(activeJob.job_id)
      setActiveJob(prev => ({ ...prev, status: 'cancelled' }))
      setScraping(false)
      setPausing(false)
      refreshHistory()
    } catch (err) {
      alert('Gagal cancel: ' + err.message)
    } finally {
      setCancelling(false)
    }
  }


  const currentStatus = activeJob?.status || 'idle'
  const logs          = activeJob?.logs || []
  const progress      = activeJob?.total_found
    ? (activeJob.progress / activeJob.total_found) * 100
    : (['running', 'paused'].includes(currentStatus) ? 30 : 0)

  return (
    <div className="app-wrapper">
      {/* ── Topbar ── */}
      <header className="topbar">
        <div className="topbar-brand">
          <img src={iconImg} alt="icon" style={{ width: 28, height: 28, objectFit: 'contain' }} />
          <h1>PCGamingWiki Scraper</h1>
        </div>

        {/* Navigation */}
        <nav style={{ display: 'flex', gap: 4 }}>
          {[
            { id: 'dashboard', label: 'Dashboard', icon: '⊞' },
            { id: 'history',   label: 'History',   icon: '⏱' },
          ].map(p => (
            <button
              key={p.id}
              onClick={() => setCurrentPage(p.id)}
              style={{
                padding: '6px 14px', borderRadius: 6, border: 'none',
                background: currentPage === p.id ? 'var(--accent-glow)' : 'transparent',
                color: currentPage === p.id ? 'var(--accent)' : 'var(--text-muted)',
                fontSize: '0.82rem', fontWeight: 500, cursor: 'pointer',
                fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 6,
                borderBottom: currentPage === p.id ? '2px solid var(--accent)' : '2px solid transparent',
                transition: 'all 0.15s'
              }}
            >
              <span>{p.icon}</span> {p.label}
            </button>
          ))}
        </nav>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          style={{
            width: 36, height: 36,
            borderRadius: 8,
            border: '1px solid var(--border)',
            background: 'var(--bg-input)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1rem',
            transition: 'all 0.2s',
            flexShrink: 0,
          }}
          onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--text-primary)' }}
          onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border)';  e.currentTarget.style.color = 'var(--text-secondary)' }}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </header>

      {/* ── HISTORY PAGE ── */}
      {currentPage === 'history' ? (
        <div style={{ gridColumn: '1 / -1', display: 'flex', overflow: 'hidden' }}>
          <HistoryPage />
        </div>
      ) : (
        <>
          {/* ── Sidebar ── */}
          <aside className="sidebar">
            <ScrapeForm onSubmit={handleSubmit} disabled={scraping} />

            {jobs.length > 0 && (
              <div className="sidebar-section" style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <label>Recent</label>
                  <button
                    onClick={() => setCurrentPage('history')}
                    style={{
                      background: 'none', border: 'none', color: 'var(--accent)',
                      fontSize: '0.72rem', cursor: 'pointer', fontFamily: 'inherit'
                    }}
                  >
                    View all →
                  </button>
                </div>
                <div className="job-history">
                  {jobs.slice(0, 9).map(job => (
                    <div
                      key={job.id}
                      className={`job-history-item ${activeJob?.job_id === job.id ? 'active' : ''}`}
                      onClick={() => handleSelectJob(job)}
                    >
                      <div className="job-history-row">
                        <PlatformBadge platform={job.platform} />
                        <span className="job-history-keyword" title={job.start_url}>{job.start_url ? job.start_url.split('/').pop() : '—'}</span>
                        <StatusBadge status={job.status} />
                      </div>
                      <div className="job-history-row">
                        <span className="job-history-count">
                          {job.total_found > 0 ? `${job.total_found} jobs · ` : ''}
                          {job.finished_at
                            ? new Date(job.finished_at).toLocaleString('id-ID', { hour: '2-digit', minute: '2-digit' })
                            : 'running...'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>

          {/* ── Main Content ── */}
          <main className="main-content">
            {(['running', 'queued', 'paused'].includes(currentStatus)) && (
              <div className="progress-bar-wrap">
                <div className="progress-info">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                      {activeJob?.start_url ? `"${activeJob.start_url.split('/').pop()}"` : 'Scraping'} · PCGamingWiki
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {currentStatus === 'queued'  ? 'Waiting in queue...' :
                       currentStatus === 'paused'  ? '⏸ Dijeda — klik Resume untuk melanjutkan' :
                       `${activeJob?.progress || 0} jobs scraped`}
                    </span>
                  </div>

                  {/* Pause / Resume / Cancel buttons */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {currentStatus === 'running' && (
                      <button
                        onClick={handlePause}
                        disabled={pausing}
                        style={{
                          padding: '6px 14px', borderRadius: 6, border: '1px solid var(--warn)',
                          background: 'rgba(245,158,11,0.1)', color: 'var(--warn)',
                          fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                          fontFamily: 'inherit', transition: 'all 0.15s',
                          display: 'flex', alignItems: 'center', gap: 6,
                          opacity: pausing ? 0.6 : 1,
                        }}
                      >
                        ⏸ {pausing ? 'Pausing...' : 'Pause'}
                      </button>
                    )}
                    {currentStatus === 'paused' && (
                      <button
                        onClick={handleResume}
                        disabled={pausing}
                        style={{
                          padding: '6px 14px', borderRadius: 6, border: '1px solid var(--success)',
                          background: 'rgba(16,185,129,0.1)', color: 'var(--success)',
                          fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                          fontFamily: 'inherit', transition: 'all 0.15s',
                          display: 'flex', alignItems: 'center', gap: 6,
                          opacity: pausing ? 0.6 : 1,
                        }}
                      >
                        ▶ {pausing ? 'Resuming...' : 'Resume'}
                      </button>
                    )}
                    {currentStatus !== 'cancelled' && (
                      <button
                        className="cancel-btn"
                        onClick={handleCancel}
                        disabled={cancelling}
                      >
                        {cancelling ? 'Cancelling...' : '✕ Cancel'}
                      </button>
                    )}
                  </div>
                </div>
                <div className="progress-track" style={{ marginTop: 8 }}>
                  <div
                    className="progress-fill"
                    style={{
                      width: `${Math.min(progress, 100)}%`,
                      background: currentStatus === 'paused'
                        ? 'linear-gradient(90deg, #f59e0b, #d97706)'
                        : undefined,
                    }}
                  />
                </div>
              </div>
            )}

            <div className="main-tabs">
              {/* Status — ujung kiri tab bar */}
              {currentStatus !== 'idle' && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 7,
                  paddingRight: 16, marginRight: 4,
                  borderRight: '1px solid var(--border)',
                  fontSize: '0.78rem',
                }}>
                  <StatusDot status={currentStatus} />
                  <span style={{
                    color: currentStatus === 'running' ? '#93c5fd'
                         : currentStatus === 'paused'  ? 'var(--warn)'
                         : currentStatus === 'done'    ? 'var(--success)'
                         : currentStatus === 'error'   ? 'var(--error)'
                         : currentStatus === 'cancelled' ? 'var(--text-muted)'
                         : 'var(--text-secondary)',
                    fontWeight: 500,
                    whiteSpace: 'nowrap',
                  }}>
                    {currentStatus === 'running'
                      ? `Scraping ${activeJob?.platform} · ${activeJob?.progress} jobs`
                      : currentStatus === 'paused'
                      ? `⏸ Paused · ${activeJob?.progress} jobs`
                      : currentStatus === 'done'
                      ? `Done · ${activeJob?.total_found} jobs`
                      : currentStatus === 'error' && activeJob?.output_file
                      ? `Error · ${activeJob?.total_found || 0} partial jobs`
                      : currentStatus === 'error'
                      ? 'Error'
                      : currentStatus === 'cancelled' && activeJob?.output_file
                      ? `Cancelled · ${activeJob?.total_found || 0} partial jobs`
                      : currentStatus === 'cancelled'
                      ? 'Cancelled'
                      : 'Error'}
                  </span>
                </div>
              )}

              <button className={`tab-btn ${tab === 'logs' ? 'active' : ''}`} onClick={() => setTab('logs')}>
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M9 12h6M9 16h6M7 8h10M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z"/>
                </svg>
                Logs
                {logs.length > 0 && <span className="tab-badge">{logs.length}</span>}
              </button>
              <button className={`tab-btn ${tab === 'results' ? 'active' : ''}`} onClick={() => setTab('results')}>
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M3 3h18v4H3zM3 9h18v4H3zM3 15h18v4H3z"/>
                </svg>
                Results
                {resultData && <span className="tab-badge">{resultData.total}</span>}
              </button>
            </div>

            {tab === 'logs'
              ? <LogPanel logs={logs} status={currentStatus} />
              : <ResultTable
                  data={resultData?.data || []}
                  total={resultData?.total || 0}
                  jobId={activeJob?.job_id}
                  fileName={activeJob?.file_name}
                />
            }
          </main>
        </>
      )}
    </div>
  )
}
