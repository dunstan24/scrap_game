const BASE = 'http://localhost:8000/api'

export const api = {
  startScrape: (payload) =>
    fetch(`${BASE}/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(r => r.json()),

  getStatus: (jobId) =>
    fetch(`${BASE}/status/${jobId}`).then(r => r.json()),

  getResult: (jobId) =>
    fetch(`${BASE}/result/${jobId}`).then(r => r.json()),

  listJobs: () =>
    fetch(`${BASE}/jobs`).then(r => r.json()),

  cancelScrape: (jobId) =>
    fetch(`${BASE}/cancel/${jobId}`, { method: 'POST' }).then(r => r.json()),

  pauseJob: (jobId) =>
    fetch(`${BASE}/pause/${jobId}`, { method: 'POST' }).then(r => r.json()),

  resumeJob: (jobId) =>
    fetch(`${BASE}/resume/${jobId}`, { method: 'POST' }).then(r => r.json()),

  downloadUrl: (jobId) => `${BASE}/download/${jobId}`,
}


export const AUSTRALIAN_STATES = [
  'New South Wales', 'Victoria', 'Queensland',
  'Western Australia', 'South Australia', 'Tasmania',
  'Australian Capital Territory', 'Northern Territory',
]

export const STATE_ABBR = {
  'New South Wales': 'NSW', 'Victoria': 'VIC', 'Queensland': 'QLD',
  'Western Australia': 'WA', 'South Australia': 'SA', 'Tasmania': 'TAS',
  'Australian Capital Territory': 'ACT', 'Northern Territory': 'NT',
}
