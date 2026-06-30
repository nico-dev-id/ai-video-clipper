"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";

interface Clip {
  clip_number: number;
  start: number;
  end: number;
  reason: string;
  url: string;
}

interface GenerateResponse {
  video_title: string;
  channel: string;
  duration: number;
  clips: Clip[];
  status?: string;
  error?: string;
}

interface StatusResponse {
  state: string;
  status?: string;
  percent?: number;
  result?: GenerateResponse;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [numClips, setNumClips] = useState(5);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [percent, setPercent] = useState(0);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState("");
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  const pollStatus = (taskId: string) => {
    pollingRef.current = setInterval(async () => {
      try {
        const res = await axios.get<StatusResponse>(
          `http://localhost:8000/api/status/${taskId}`
        );
        const data = res.data;

        if (data.state === "PROGRESS") {
          setStatusText(data.status || "");
          setPercent(data.percent || 0);
        } else if (data.state === "SUCCESS") {
          stopPolling();
          if (data.result?.status === "error") {
            setError(data.result.error || "Terjadi kesalahan.");
          } else {
            setResult(data.result!);
          }
          setLoading(false);
          setPercent(100);
        } else if (data.state === "FAILURE") {
          stopPolling();
          setError("Proses gagal: " + data.status);
          setLoading(false);
        }
      } catch {
        stopPolling();
        setError("Gagal mengecek status task.");
        setLoading(false);
      }
    }, 2000);
  };

  const handleGenerate = async () => {
    if (!url) return;
    setLoading(true);
    setError("");
    setResult(null);
    setStatusText("Mengirim task ke queue...");
    setPercent(0);

    try {
      const response = await axios.post<{ task_id: string }>(
        "http://localhost:8000/api/generate-clips",
        { url, num_clips: numClips }
      );
      pollStatus(response.data.task_id);
    } catch {
      setError("Gagal mengirim request. Pastikan server berjalan.");
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
  };

  const steps = [
    { label: "Download", threshold: 20 },
    { label: "Transkripsi", threshold: 50 },
    { label: "Analisis AI", threshold: 65 },
    { label: "Render Clips", threshold: 100 },
  ];

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white">
      <div className="fixed inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:48px_48px] pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-6 py-16">

        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-indigo-400 text-sm font-medium mb-6">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
            Powered by Whisper + Groq AI
          </div>
          <h1 className="text-6xl font-black tracking-tight mb-4">
            <span className="text-white">AI </span>
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Video Clipper
            </span>
          </h1>
          <p className="text-gray-500 text-lg max-w-xl mx-auto">
            Paste URL YouTube manapun. AI transkripsi, analisis, dan potong clip terbaik secara otomatis.
          </p>
        </div>

        {/* Input Card */}
        <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-6 mb-8 backdrop-blur-sm">
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
            YouTube URL
          </label>
          <div className="flex gap-3 mb-4">
            <div className="flex-1 relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 text-lg">🔗</span>
              <input
                type="text"
                placeholder="https://www.youtube.com/watch?v=..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
                className="w-full bg-black/40 border border-white/10 rounded-xl pl-11 pr-4 py-3.5 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30 transition-all"
              />
            </div>
            <button
              onClick={handleGenerate}
              disabled={loading || !url}
              className="relative bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed px-8 py-3.5 rounded-xl font-semibold transition-all duration-200 whitespace-nowrap"
            >
              {loading ? "Memproses..." : "Generate Clips"}
            </button>
          </div>

          {/* Num Clips Selector */}
          <div className="flex items-center gap-4">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-widest whitespace-nowrap">
              Jumlah Clip
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5, 7, 10].map((n) => (
                <button
                  key={n}
                  onClick={() => setNumClips(n)}
                  disabled={loading}
                  className={`w-9 h-9 rounded-lg text-sm font-semibold transition-all ${
                    numClips === n
                      ? "bg-indigo-600 text-white"
                      : "bg-white/5 text-gray-500 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Loading + Progress */}
        {loading && (
          <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-8 mb-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="relative w-10 h-10 flex-shrink-0">
                <div className="w-10 h-10 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
              </div>
              <div className="flex-1">
                <p className="text-white font-semibold">{statusText}</p>
                <p className="text-gray-600 text-sm">Jangan tutup halaman ini</p>
              </div>
              <div className="text-indigo-400 font-bold text-2xl">
                {percent}%
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-white/10 rounded-full h-2 mb-4">
              <div
                className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all duration-700"
                style={{ width: `${percent}%` }}
              />
            </div>

            {/* Step labels */}
            <div className="flex justify-between">
              {steps.map((s) => (
                <div key={s.label} className="flex flex-col items-center gap-1">
                  <div className={`w-2 h-2 rounded-full transition-all duration-500 ${
                    percent >= s.threshold ? "bg-indigo-500" : "bg-white/20"
                  }`} />
                  <span className={`text-xs transition-all duration-500 ${
                    percent >= s.threshold ? "text-indigo-400" : "text-gray-600"
                  }`}>
                    {s.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 text-red-400">
            <span className="text-lg mt-0.5">⚠️</span>
            <div>
              <p className="font-semibold mb-1">Terjadi Kesalahan</p>
              <p className="text-sm text-red-300">{error}</p>
              {error.includes("rate limit") || error.includes("quota") || error.includes("429") ? (
                <p className="text-sm text-yellow-400 mt-2">
                  💡 AI sedang kena rate limit. Tunggu beberapa menit lalu coba lagi.
                </p>
              ) : null}
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div>
            <div className="flex items-center gap-4 bg-white/[0.03] border border-white/[0.08] rounded-2xl p-5 mb-8">
              <div className="w-10 h-10 bg-red-500/20 rounded-xl flex items-center justify-center text-xl flex-shrink-0">
                ▶️
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="font-semibold text-white truncate">{result.video_title}</h2>
                <p className="text-gray-500 text-sm">{result.channel} • {formatDuration(result.duration)}</p>
              </div>
              <div className="bg-green-500/10 border border-green-500/20 rounded-full px-3 py-1 text-green-400 text-xs font-semibold whitespace-nowrap">
                {result.clips.length} clips ready
              </div>
            </div>

            <div className="grid grid-cols-1 gap-5">
              {result.clips.map((clip) => (
                <div
                  key={clip.clip_number}
                  className="bg-white/[0.03] border border-white/[0.08] rounded-2xl overflow-hidden hover:border-indigo-500/30 transition-all duration-300"
                >
                  <video
                    controls
                    className="w-full max-h-[480px] bg-black"
                    src={`http://localhost:8000${clip.url}`}
                  />
                  <div className="p-5">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs px-3 py-1 rounded-full font-bold">
                        CLIP #{clip.clip_number}
                      </span>
                      <span className="text-gray-600 text-xs font-mono">
                        {clip.start}s → {clip.end}s
                      </span>
                    </div>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      <span className="text-indigo-400 font-medium">AI insight: </span>
                      {clip.reason}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </main>
  );
}