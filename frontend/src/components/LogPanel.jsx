import { useEffect, useRef } from "react";

function classifyLog(msg) {
  const m = msg.toLowerCase();

  // Cloudflare detection (highest priority)
  if (m.includes("cloudflare") || m.includes("🔒")) return "cloudflare";
  if (m.includes("⏳") || m.includes("security verification"))
    return "cloudflare-wait";

  // Detailed operation logs with emojis
  if (
    m.includes("🎉") ||
    m.includes("complete") ||
    m.includes("selesai") ||
    m.includes("ok") ||
    m.includes("[ok]") ||
    m.includes("saved")
  )
    return "ok";

  if (
    m.includes("error") ||
    m.includes("❌") ||
    m.includes("[err]") ||
    m.includes("fail")
  )
    return "error";

  if (m.includes("warn") || m.includes("⚠") || m.includes("[warn]"))
    return "warn";

  if (
    m.includes("🔍") ||
    m.includes("🖱️") ||
    m.includes("⌨️") ||
    m.includes("✓") ||
    m.includes("✅") ||
    m.includes("📊") ||
    m.includes("→") ||
    m.includes("↗️") ||
    m.includes("🔄") ||
    m.includes("mulai") ||
    m.includes("start") ||
    m.includes("scraping") ||
    m.includes("->")
  )
    return "info";

  if (m.includes("page") && m.includes("/")) return "progress";

  return "";
}

export default function LogPanel({ logs = [], status }) {
  const bottomRef = useRef(null);
  const cloudflareDetected = logs.some(
    (log) => log.toLowerCase().includes("cloudflare") || log.includes("🔒"),
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) {
    return (
      <div className="log-panel">
        <div className="log-empty">
          <svg
            width="48"
            height="48"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
          >
            <path d="M9 12h6M9 16h6M7 8h10M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z" />
          </svg>
          <p>Log akan muncul saat scraping berjalan</p>
        </div>
      </div>
    );
  }

  return (
    <div className="log-panel">
      {cloudflareDetected && (
        <div className="cloudflare-alert">
          <span>🔒 Cloudflare challenge detected - adaptive delays active</span>
        </div>
      )}
      {logs.map((line, i) => {
        // Format: [HH:MM:SS] message
        const match = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)$/);
        const time = match ? match[1] : "";
        const msg = match ? match[2] : line;
        const cls = classifyLog(msg);

        return (
          <div key={i} className={`log-line ${cls}`}>
            {time && <span className="log-time">{time}</span>}
            <span className={`log-msg ${cls}`}>{msg}</span>
          </div>
        );
      })}
      {status === "running" && (
        <div className="log-line">
          <span className="log-time">···</span>
          <span
            className="log-msg info"
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <span
              className="spinner"
              style={{
                borderTopColor: "#60a5fa",
                borderColor: "rgba(96,165,250,0.3)",
              }}
            />
            sedang berjalan...
          </span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
