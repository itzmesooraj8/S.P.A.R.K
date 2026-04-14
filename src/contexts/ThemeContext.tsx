import React, { createContext, useContext, useState, useCallback } from 'react';

export type HudTheme = 'blue' | 'red' | 'white' | 'amber';
export type AiMode = 'PASSIVE' | 'ACTIVE' | 'COMBAT';

interface ThemeContextType {
  theme: HudTheme;
  setTheme: (t: HudTheme) => void;
  aiMode: AiMode;
  setAiMode: (m: AiMode) => void;
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
