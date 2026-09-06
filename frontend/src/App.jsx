import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";
import { getTrack, uploadTrack } from "./api";

const POLL_INTERVAL_MS = 400;

const STATUS_LABELS = {
  queued: "Queued",
  running: "Analysing",
};

function MetricCard({ label, value, icon }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div className="metric-body">
        <div className="label">{label}</div>
        <div className="value">{value}</div>
      </div>
    </div>
  );
}

function MonoIndicator({ score, worstBand }) {
  // Thresholds are a display choice, not a claim from mono_compatibility()
  // itself -- the function returns a continuous 0-100 score; drawing a
  // line at "good enough" vs "worth investigating" is a UI judgment call.
  const level = score >= 80 ? "ok" : score >= 50 ? "warn" : "bad";
  const levelLabel = level === "ok" ? "Good" : level === "warn" ? "Check it" : "Problem";
  return (
    <div className="mono-indicator">
      <div className={`mono-badge ${level}`}>
        <span className="score numeric">{score.toFixed(1)}</span>
        <span className="badge-label">{levelLabel}</span>
      </div>
      <div className="mono-detail">
        <span className="worst-band-label">Worst band</span>
        <span className="worst-band-value numeric">{worstBand}</span>
      </div>
    </div>
  );
}

const BAND_LABELS = { sub: "Sub", bass: "Bass", low_mid: "Low-mid", mid: "Mid", high: "High" };

function FrequencyBalanceChart({ balance }) {
  const data = ["sub", "bass", "low_mid", "mid", "high"].map((band) => ({
    band: BAND_LABELS[band],
    db: balance[band],
  }));
  // Explicit domain with headroom above 0dB -- otherwise a band close to
  // 0 (holding most of the track's energy) renders flush against the
  // chart's top edge, since recharts' auto domain fits the data exactly.
  const minValue = Math.min(...data.map((d) => d.db));
  const yMin = Math.floor(minValue / 10) * 10 - 5;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="band" stroke="var(--text-dim)" fontSize={12} tickLine={false} />
        <YAxis
          domain={[yMin, 5]}
          stroke="var(--text-dim)"
          fontSize={12}
          tickLine={false}
          width={48}
          unit="dB"
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 13,
          }}
          labelStyle={{ color: "var(--text-dim)" }}
          formatter={(value) => [`${value.toFixed(1)} dB`, "Energy"]}
        />
        <Bar dataKey="db" fill="var(--accent)" radius={[4, 4, 0, 0]} maxBarSize={64} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export default function App() {
  const [file, setFile] = useState(null);
  const [track, setTrack] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    // Stop polling on unmount or whenever a new track supersedes it --
    // without this, a stale interval would keep calling getTrack() for
    // a track the user has moved on from.
    return () => clearInterval(pollRef.current);
  }, []);

  function pollUntilDone(trackId) {
    clearInterval(pollRef.current);

    async function checkOnce() {
      try {
        const result = await getTrack(trackId);
        setTrack(result);
        if (result.status === "complete" || result.status === "failed") {
          clearInterval(pollRef.current);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(pollRef.current);
      }
    }

    // Check immediately rather than waiting for the first interval tick --
    // analysis on a typical track finishes in a few seconds, so an
    // interval-only poll wastes up to POLL_INTERVAL_MS of real analysis
    // time just sitting idle before the first status check happens.
    checkOnce();
    pollRef.current = setInterval(checkOnce, POLL_INTERVAL_MS);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setTrack(null);
    try {
      const result = await uploadTrack(file);
      setTrack(result);
      if (result.status !== "complete" && result.status !== "failed") {
        pollUntilDone(result.id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  const features = track?.features;
  const isProcessing = track && !features && track.status !== "failed";

  return (
    <div className="app">
      <header className="app-header">
        <h1>tracklab</h1>
        <p className="tagline">Measured numbers, not guesswork.</p>
        <p className="description">
          For music producers who want to know whether a mix will hold up
          off the studio monitors — on a phone speaker, earbuds, or a club
          system — before it's too late to fix cheaply.
        </p>
      </header>

      <div className="upload-panel">
        <label className="file-picker">
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files[0] ?? null)}
          />
          <span className="file-picker-button">Choose file</span>
          <span className="file-picker-name">{file ? file.name : "No file selected"}</span>
        </label>
        <button className="analyse-button" onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? <Spinner /> : "Analyse"}
        </button>
      </div>

      {isProcessing && (
        <div className="status-banner">
          <Spinner />
          <span>{STATUS_LABELS[track.status] ?? track.status}…</span>
        </div>
      )}

      {(error || track?.status === "failed") && (
        <div className="error-banner">
          {error || `Analysis failed: ${track.error}`}
        </div>
      )}

      {features && (
        <div className="results">
          <div className="metric-grid">
            <MetricCard label="Tempo" value={`${features.bpm.toFixed(1)} BPM`} icon="♩" />
            <MetricCard label="Key" value={`${features.key} ${features.mode}`} icon="♪" />
            <MetricCard label="Loudness" value={`${features.lufs.toFixed(1)} LUFS`} icon="◑" />
          </div>

          <div className="panel">
            <h2>Mono compatibility</h2>
            <MonoIndicator score={features.mono_score} worstBand={features.mono_worst_band} />
          </div>

          <div className="panel">
            <h2>Frequency balance</h2>
            <p className="panel-subtitle">dB relative to this track's total energy</p>
            <FrequencyBalanceChart balance={features.frequency_balance} />
          </div>
        </div>
      )}
    </div>
  );
}
