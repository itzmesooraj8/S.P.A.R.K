import { useState, useEffect, useRef, useCallback } from 'react';
import { Music, Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, RefreshCw, Search } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

interface Track {
  id: string;
  name: string;
  title: string;
  ext: string;
  size_mb: number;
}

export default function MusicModule() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [filtered, setFiltered] = useState<Track[]>([]);
  const [search, setSearch] = useState('');
  const [currentIdx, setCurrentIdx] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.75);
  const [muted, setMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchTracks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await fetch(`${API}/api/music/files`);
      const data = await r.json();
      const list: Track[] = data.files ?? [];
      setTracks(list);
      setFiltered(list);
    } catch {
      setError('Could not reach music API. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerScan = async () => {
    setScanning(true);
    try {
      const r = await fetch(`${API}/api/music/scan`, { method: 'POST' });
      const data = await r.json();
      const list: Track[] = data.files ?? [];
      setTracks(list);
      setFiltered(list.filter(t =>
        !search || t.title.toLowerCase().includes(search.toLowerCase())));
    } catch {
      setError('Scan failed.');
    } finally {
      setScanning(false);
    }
  };

  useEffect(() => { fetchTracks(); }, [fetchTracks]);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(tracks.filter(t => t.title.toLowerCase().includes(q)));
  }, [search, tracks]);

  const playTrack = (idx: number) => {
    const track = filtered[idx];
    if (!track) return;
    const url = `${API}/api/music/stream/${track.id}`;
    if (audioRef.current) {
      audioRef.current.src = url;
      audioRef.current.volume = muted ? 0 : volume;
      audioRef.current.play().catch(() => setError('Playback failed. Check browser autoplay settings.'));
    }
    setCurrentIdx(idx);
    setIsPlaying(true);
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else { audioRef.current.play(); setIsPlaying(true); }
  };

  const skipNext = () => {
    if (currentIdx === null) { playTrack(0); return; }
    playTrack((currentIdx + 1) % filtered.length);
  };

  const skipPrev = () => {
    if (currentIdx === null) { playTrack(0); return; }
    playTrack((currentIdx - 1 + filtered.length) % filtered.length);
  };

  const handleVolumeChange = (v: number) => {
    setVolume(v);
    if (audioRef.current) audioRef.current.volume = muted ? 0 : v;
  };

  const toggleMute = () => {
    setMuted(m => {
      if (audioRef.current) audioRef.current.volume = !m ? 0 : volume;
      return !m;
    });
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = pct * duration;
  };

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  const currentTrack = currentIdx !== null ? filtered[currentIdx] : null;

  return (
    <div className="flex flex-col h-full p-4 gap-3 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-hud-cyan/20">
        <div className="flex items-center gap-2">
          <Music size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-xs tracking-widest neon-text">MUSIC PLAYER</span>
        </div>
        <button
          onClick={triggerScan}
          disabled={scanning}
          className="flex items-center gap-1 text-[9px] font-orbitron text-hud-cyan/60 hover:text-hud-cyan px-2 py-0.5 border border-hud-cyan/20 hover:border-hud-cyan/60 rounded transition-colors"
        >
          <RefreshCw size={10} className={scanning ? 'animate-spin' : ''} />
          {scanning ? 'SCANNING...' : 'RESCAN'}
        </button>
      </div>

      {/* Now Playing */}
      <div className="hud-panel rounded p-3 shrink-0">
        <div className="text-[9px] font-orbitron text-hud-cyan/40 mb-1">NOW PLAYING</div>
        <div className="font-mono-tech text-[11px] text-hud-cyan truncate mb-2 min-h-[14px]">
          {currentTrack ? currentTrack.title : '— SELECT A TRACK —'}
        </div>

        {/* Progress bar */}
        <div
          className="h-1.5 bg-black/40 rounded-full cursor-pointer mb-2 border border-hud-cyan/10"
          onClick={seek}
        >
          <div
            className="h-full rounded-full bg-hud-cyan transition-all"
            style={{ width: duration ? `${(progress / duration) * 100}%` : '0%' }}
          />
        </div>
        <div className="flex justify-between text-[8px] text-hud-cyan/40 font-mono-tech mb-3">
          <span>{fmt(progress)}</span>
          <span>{fmt(duration)}</span>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-4 mb-3">
          <button onClick={skipPrev} className="text-hud-cyan/60 hover:text-hud-cyan transition-colors"><SkipBack size={16} /></button>
          <button
            onClick={currentIdx !== null ? togglePlay : () => filtered.length > 0 && playTrack(0)}
            className="w-8 h-8 rounded-full border border-hud-cyan/40 flex items-center justify-center text-hud-cyan hover:border-hud-cyan hover:shadow-[0_0_8px_#00f5ff60] transition-all"
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button onClick={skipNext} className="text-hud-cyan/60 hover:text-hud-cyan transition-colors"><SkipForward size={16} /></button>
        </div>

        {/* Volume */}
        <div className="flex items-center gap-2">
          <button onClick={toggleMute} className="text-hud-cyan/60 hover:text-hud-cyan transition-colors">
            {muted ? <VolumeX size={12} /> : <Volume2 size={12} />}
          </button>
          <input
            type="range" min={0} max={1} step={0.01} value={muted ? 0 : volume}
            onChange={e => handleVolumeChange(parseFloat(e.target.value))}
            className="flex-1 h-1 accent-cyan-400 cursor-pointer"
          />
          <span className="text-[8px] text-hud-cyan/40 font-mono-tech w-6">{Math.round((muted ? 0 : volume) * 100)}</span>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 hud-panel rounded px-2 py-1.5 shrink-0">
        <Search size={11} className="text-hud-cyan/50" />
        <input
          type="text"
          placeholder="Search tracks..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 bg-transparent text-[10px] font-mono-tech text-hud-cyan placeholder-hud-cyan/30 outline-none"
        />
        {search && (
          <button onClick={() => setSearch('')} className="text-hud-cyan/40 hover:text-hud-cyan text-[10px]">✕</button>
        )}
      </div>

      {/* Track list */}
      <div className="flex-1 overflow-y-auto scrollbar-hud min-h-0">
        {error && (
          <div className="text-center text-[10px] text-hud-red/80 font-mono-tech py-4">{error}</div>
        )}
        {loading && !error && (
          <div className="text-center text-[10px] text-hud-cyan/40 font-mono-tech py-4 animate-pulse">SCANNING LIBRARY...</div>
        )}
        {!loading && !error && filtered.length === 0 && (
          <div className="text-center text-[10px] text-hud-cyan/30 font-mono-tech py-8">
            {tracks.length === 0 ? 'No audio files found. Click RESCAN to search your drives.' : 'No tracks match your search.'}
          </div>
        )}
        {filtered.map((track, idx) => (
          <div
            key={track.id}
            onClick={() => playTrack(idx)}
            className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-all mb-0.5 ${
              currentIdx === idx
                ? 'bg-hud-cyan/10 border border-hud-cyan/30'
                : 'hover:bg-hud-cyan/5 border border-transparent'
            }`}
          >
            <div className="w-4 h-4 flex items-center justify-center shrink-0">
              {currentIdx === idx && isPlaying
                ? <div className="flex gap-0.5 items-end h-4">{[1,2,3].map(i => <div key={i} className="w-0.5 bg-hud-cyan animate-pulse rounded-full" style={{height: `${8 + i * 3}px`, animationDelay: `${i * 0.15}s`}} />)}</div>
                : <Music size={10} className="text-hud-cyan/40" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-mono-tech text-[10px] text-hud-cyan truncate">{track.title}</div>
              <div className="text-[8px] text-hud-cyan/30 uppercase">{track.ext} · {track.size_mb}MB</div>
            </div>
          </div>
        ))}
      </div>

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        onTimeUpdate={() => setProgress(audioRef.current?.currentTime ?? 0)}
        onDurationChange={() => setDuration(audioRef.current?.duration ?? 0)}
        onEnded={skipNext}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />
    </div>
  );
}
