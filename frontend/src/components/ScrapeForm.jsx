import { useState } from "react";

export default function ScrapeForm({ onSubmit, disabled }) {
  const [scrapeMode, setScrapeMode] = useState("all");
  const [targetAlphabet, setTargetAlphabet] = useState("A");
  const [skipExisting, setSkipExisting] = useState(true);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      start_url: "https://www.pcgamingwiki.com/wiki/Category:Games",
      platform: "pcgamingwiki",
      pages: 9999, // default to large number to scrape everything
      scrape_mode: scrapeMode,
      target_alphabet: scrapeMode === "alphabet" ? targetAlphabet : null,
      skip_existing: skipExisting,
    });
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "contents" }}>
      {/* Platform Fixed */}
      <div className="sidebar-section">
        <label>Platform</label>
        <div className="platform-grid" style={{ gridTemplateColumns: "1fr" }}>
          <button
            type="button"
            className={`platform-pill active-pcgamingwiki`}
            disabled
            style={{ 
              background: 'var(--accent)', 
              color: '#fff', 
              borderColor: 'transparent',
              opacity: 1
            }}
          >
            <span>🎮</span>
            <span>PCGamingWiki</span>
          </button>
        </div>
      </div>

      {/* Scrape Mode */}
      <div className="sidebar-section">
        <label>Scrape Mode</label>
        <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontWeight: 'normal', color: 'var(--text-secondary)' }}>
            <input 
              type="radio" 
              name="scrapeMode" 
              value="all" 
              checked={scrapeMode === "all"} 
              onChange={(e) => setScrapeMode(e.target.value)} 
              disabled={disabled}
            />
            All
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontWeight: 'normal', color: 'var(--text-secondary)' }}>
            <input 
              type="radio" 
              name="scrapeMode" 
              value="alphabet" 
              checked={scrapeMode === "alphabet"} 
              onChange={(e) => setScrapeMode(e.target.value)} 
              disabled={disabled}
            />
            By Alphabet
          </label>
        </div>
      </div>

      {/* Target Alphabet */}
      {scrapeMode === "alphabet" && (
        <div className="sidebar-section">
          <label>Target Alphabet</label>
          <select
            className="input-field"
            value={targetAlphabet}
            onChange={(e) => setTargetAlphabet(e.target.value)}
            disabled={disabled}
            style={{ padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-input)', color: 'var(--text-primary)', marginTop: '4px' }}
          >
            <option value="0-9">0-9</option>
            {"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map(letter => (
              <option key={letter} value={letter}>{letter}</option>
            ))}
            <option value="Other">Other</option>
          </select>
        </div>
      )}

      {/* Skip Existing Checkbox */}
      <div className="sidebar-section" style={{ marginTop: '10px', marginBottom: '10px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 'normal', color: 'var(--text-primary)' }}>
          <input
            type="checkbox"
            checked={skipExisting}
            onChange={(e) => setSkipExisting(e.target.checked)}
            disabled={disabled}
            style={{ cursor: 'pointer' }}
          />
          Skip Existing Games
        </label>
      </div>

      {/* Submit */}
      <button
        className="btn-start"
        type="submit"
        disabled={disabled}
      >
        {disabled ? (
          <>
            <span className="spinner" />
            <span>Scraping...</span>
          </>
        ) : (
          <>
            <span>▶</span>
            <span>Start Scraping</span>
          </>
        )}
      </button>
    </form>
  );
}
