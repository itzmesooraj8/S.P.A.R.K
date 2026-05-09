import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export type HudTheme = 'blue' | 'red' | 'white' | 'amber';
export type AiMode = 'PASSIVE' | 'ACTIVE' | 'COMBAT';
export type HudExperienceMode = 'normal' | 'developer';

interface ThemeContextType {
  theme: HudTheme;
  setTheme: (t: HudTheme) => void;
  aiMode: AiMode;
  setAiMode: (m: AiMode) => void;
  hudMode: HudExperienceMode;
  setHudMode: (m: HudExperienceMode) => void;
  toggleHudMode: () => void;
  ambientMode: boolean;
  setAmbientMode: (v: boolean) => void;
  isBooted: boolean;
  setIsBooted: (v: boolean) => void;
  isShuttingDown: boolean;
  triggerShutdown: () => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<HudTheme>('blue');
  const [aiMode, setAiModeState] = useState<AiMode>('PASSIVE');
  const [hudMode, setHudModeState] = useState<HudExperienceMode>(() => {
    if (typeof window === 'undefined') return 'normal';
    const stored = window.localStorage.getItem('spark.hudMode');
    return stored === 'developer' ? 'developer' : 'normal';
  });
  const [ambientMode, setAmbientMode] = useState(false);
  const [isBooted, setIsBooted] = useState(false);
  const [isShuttingDown, setIsShuttingDown] = useState(false);

  const setTheme = useCallback((t: HudTheme) => {
    setThemeState(t);
    document.documentElement.classList.remove('theme-red', 'theme-white', 'theme-amber');
    if (t === 'red') document.documentElement.classList.add('theme-red');
    if (t === 'white') document.documentElement.classList.add('theme-white');
    if (t === 'amber') document.documentElement.classList.add('theme-amber');
  }, []);

  const setAiMode = useCallback((m: AiMode) => {
    setAiModeState(m);
    if (m === 'PASSIVE') setTheme('blue');
    if (m === 'ACTIVE') setTheme('amber');
    if (m === 'COMBAT') setTheme('red');
  }, [setTheme]);

  const setHudMode = useCallback((m: HudExperienceMode) => {
    setHudModeState(m);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('spark.hudMode', m);
      document.documentElement.dataset.hudMode = m;
    }
  }, []);

  const toggleHudMode = useCallback(() => {
    setHudMode(hudMode === 'developer' ? 'normal' : 'developer');
  }, [hudMode, setHudMode]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      document.documentElement.dataset.hudMode = hudMode;
    }
  }, [hudMode]);

  const triggerShutdown = useCallback(() => {
    setIsShuttingDown(true);
    setTimeout(() => {
      setIsBooted(false);
      setIsShuttingDown(false);
    }, 2000);
  }, []);

  return (
    <ThemeContext.Provider value={{
      theme, setTheme,
      aiMode, setAiMode,
      hudMode, setHudMode, toggleHudMode,
      ambientMode, setAmbientMode,
      isBooted, setIsBooted,
      isShuttingDown, triggerShutdown,
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useHudTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useHudTheme must be used within ThemeProvider');
  return ctx;
};
