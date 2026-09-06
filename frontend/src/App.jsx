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

const POLL_INTERVAL_MS = 1500;

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

function MonoIndicator({ score, worstBand }) {
  // Thresholds are a display choice, not a claim from mono_compatibility()
  // itself -- the function returns a continuous 0-100 score; drawing a
  // line at "good enough" vs "worth investigating" is a UI judgment call.
  const level = score >= 80 ? "ok" : score >= 50 ? "warn" : "bad";
  return (
    <div className="mono-indicator">
      <span className={`dot ${level}`} />
      <span className="score numeric">{score.toFixed(1)}</span>
      <span className="worst-band">worst band: {worstBand}</span>
    </div>
  );
}

function FrequencyBalanceChart({ balance }) {
  const data = ["sub", "bass", "low_mid", "mid", "high"].map((band) => ({
    band,
    db: balance[band],
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2c2f3a" />
        <XAxis dataKey="band" stroke="#9095a3" fontSize={12} />
        <YAxis stroke="#9095a3" fontSize={12} unit="dB" />
        <Tooltip
          contentStyle={{ background: "#1c1e26", border: "1px solid #2c2f3a" }}
          formatter={(value) => `${value.toFixed(1)} dB`}
        />
        <Bar dataKey="db" fill="#60a5fa" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
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
    pollRef.current = setInterval(async () => {
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
    }, POLL_INTERVAL_MS);
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

  return (
    <div className="app">
      <h1>tracklab</h1>

      <div className="upload-panel">
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => setFile(e.target.files[0] ?? null)}
        />
        <button onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? "Uploading…" : "Analyse"}
        </button>
        {track && !features && (
          <span className="status-line">status: {track.status}</span>
        )}
      </div>

      {error && <p className="error-line">{error}</p>}

      {track?.status === "failed" && (
        <p className="error-line">Analysis failed: {track.error}</p>
      )}

      {features && (
        <>
          <div className="metric-grid">
            <MetricCard label="BPM" value={features.bpm.toFixed(1)} />
            <MetricCard label="Key" value={`${features.key} ${features.mode}`} />
            <MetricCard label="Loudness" value={`${features.lufs.toFixed(1)} LUFS`} />
          </div>

          <div className="panel">
            <h2>Mono compatibility</h2>
            <MonoIndicator score={features.mono_score} worstBand={features.mono_worst_band} />
          </div>

          <div className="panel">
            <h2>Frequency balance (dB relative to total energy)</h2>
            <FrequencyBalanceChart balance={features.frequency_balance} />
          </div>
        </>
      )}
    </div>
  );
}
