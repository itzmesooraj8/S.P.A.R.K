/**
 * SPARK Command Bar
 * ────────────────────────────────────────────────────────────────────────────────
 * Floating command palette: Ctrl+Space or Cmd+Space to open
 * Type queries or slash commands; Enter submits; Escape closes
 * Integrates with Intent Router for smart dispatch
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Search, X, ChevronRight } from 'lucide-react';
import { useCommandBarStore } from '../store/commandBarStore';
import { useContextStore } from '../store/useContextStore';
import { useVoiceEngine } from '../hooks/useVoiceEngine';

interface SlashCommand {
  command: string;
  description: string;
  placeholder: string;
  icon: string;
}

interface Suggestion {
  type: 'command' | 'history';
  text: string;
  icon: string;
  description?: string;
}

// Slash command definitions
const SLASH_COMMANDS: SlashCommand[] = [
  {
    command: '/play',
    description: 'Play music',
    placeholder: '/play [song or artist]',
    icon: '🎵',
  },
  {
    command: '/scan',
    description: 'Security scan',
    placeholder: '/scan',
    icon: '🔒',
  },
  {
    command: '/search',
    description: 'Search knowledge base',
    placeholder: '/search [topic]',
    icon: '🔍',
  },
  {
    command: '/remind',
    description: 'Set reminder',
    placeholder: '/remind [text] at [time]',
    icon: '⏰',
  },
  {
    command: '/browse',
    description: 'Open website',
    placeholder: '/browse [url]',
    icon: '🌐',
  },
  {
    command: '/globe',
    description: 'Globe monitor',
    placeholder: '/globe [region/event]',
    icon: '🌍',
  },
  {
    command: '/mode',
    description: 'Activate mode',
    placeholder: '/mode [dev/monitor/focus]',
    icon: '⚙️',
  },
  {
    command: '/analyze',
    description: 'LLM analysis',
    placeholder: '/analyze [topic]',
    icon: '🧠',
  },
];

export const CommandBar: React.FC = () => {
  const { isOpen, setOpen, context, history } = useCommandBarStore();
  const { selectedItem } = useContextStore();
  const { speakText } = useVoiceEngine();

  // Merge: selectedItem from context store takes priority over commandBarStore.context
  const activeContext = selectedItem
    ? { module: selectedItem.module, item_type: selectedItem.type, label: selectedItem.label, data: selectedItem.data }
    : context
      ? { module: context.module, item_type: context.item_type, label: context.label, data: context.data }
      : null;
  
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-focus input when command bar opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Generate typeahead suggestions
  useEffect(() => {
    if (!input.trim()) {
      setSuggestions([]);
      setSelectedIndex(-1);
      return;
    }

    const inputLower = input.toLowerCase();
    const newSuggestions: Suggestion[] = [];

    // Slash command suggestions
    if (input.startsWith('/')) {
      const commandMatches = SLASH_COMMANDS.filter((cmd) =>
        cmd.command.toLowerCase().startsWith(inputLower)
      );
      newSuggestions.push(
        ...commandMatches.map((cmd) => ({
          type: 'command' as const,
          text: cmd.command,
          icon: cmd.icon,
          description: cmd.description,
        }))
      );
    } else {
      // History suggestions (non-slash commands)
      const historyMatches = history.filter((item) =>
        item.toLowerCase().includes(inputLower) && !item.startsWith('/')
      );
      newSuggestions.push(
        ...historyMatches.slice(0, 5).map((item) => ({
          type: 'history' as const,
          text: item,
          icon: '⏱️',
          description: 'From your history',
        }))
      );
    }

    setSuggestions(newSuggestions);
    setSelectedIndex(-1);
  }, [input, history]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    switch (e.key) {
      case 'Escape':
        setOpen(false);
        setInput('');
        break;
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        handleSubmit(
          selectedIndex >= 0 ? suggestions[selectedIndex].text : input
        );
        break;
      case 'Tab':
        e.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          setInput(suggestions[selectedIndex].text);
          setSuggestions([]);
        }
        break;
    }
  };

  // Submit query to Intent Router
  const handleSubmit = async (query: string) => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setIsLoading(true);
    setError(null);

    try {
      // Call Intent Router
      const response = await fetch('/api/command/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmedQuery,
          context: activeContext,
        }),
      });

      if (!response.ok) {
        throw new Error(`Router error: ${response.statusText}`);
      }

      const decision = await response.json();

      // Add to history
      useCommandBarStore.getState().addToHistory(trimmedQuery);

      // Execute the routing decision
      await executeRoutingDecision(decision);

      // Close command bar and reset
      setOpen(false);
      setInput('');
      setSuggestions([]);

      // Provide audio feedback
      const confirmText =
        decision.action === 'analyze'
          ? 'Processing...'
          : `Executing: ${decision.action}`;
      speakText(confirmText, { rate: 1.2 });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Command submission error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Execute routing decision by activating the appropriate frontend module
  const executeRoutingDecision = async (decision: any) => {
    const { target_module, action, parameters } = decision;

    // Dispatch frontend module activation based on target
    switch (target_module) {
      case 'music':
        // Emit event to activate music module and play query
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'music', action, params: parameters },
          })
        );
        break;

      case 'security':
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'security', action, params: parameters },
          })
        );
        break;

      case 'neural_search':
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'neural_search', action, params: parameters },
          })
        );
        break;

      case 'scheduler':
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'scheduler', action, params: parameters },
          })
        );
        break;

      case 'browser':
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'browser', action, params: parameters },
          })
        );
        break;

      case 'globe':
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'globe', action, params: parameters },
          })
        );
        break;

      case 'mode':
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'mode', action, params: parameters },
          })
        );
        break;

      case 'llm':
        // Direct LLM conversation — likely shown in a chat panel
        window.dispatchEvent(
          new CustomEvent('module-activate', {
            detail: { module: 'llm', action, params: parameters },
          })
        );
        break;

      default:
        console.warn(`Unknown target module: ${target_module}`);
    }
  };

  // Close on outside click
  const handleClickOutside = (e: MouseEvent) => {
    if (
      containerRef.current &&
      !containerRef.current.contains(e.target as Node)
    ) {
      setOpen(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () =>
        document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Command bar container */}
      <div
        ref={containerRef}
        className="relative w-full max-w-2xl mx-4 rounded-lg overflow-hidden"
      >
        {/* Glassmorphism background */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-950/20 via-blue-950/20 to-purple-950/20 border border-cyan-500/30 rounded-lg backdrop-blur-xl" />

        {/* Content */}
        <div className="relative p-4 space-y-4">
          {/* Input section */}
          <div className="space-y-2">
            {/* Active context chip — shows what item is in focus for pronoun resolution */}
            {activeContext && (
              <div className="flex items-center gap-2 px-3 py-1 bg-cyan-500/20 border border-cyan-500/40 rounded-full w-fit text-xs text-cyan-300">
                <span className="font-mono uppercase tracking-wider">
                  {activeContext.module}
                </span>
                <ChevronRight size={12} />
                <span className="font-mono font-semibold">
                  {activeContext.label.length > 30
                    ? activeContext.label.substring(0, 27) + '...'
                    : activeContext.label}
                </span>
              </div>
            )}

            {/* Main input */}
            <div className="relative">
              <Search
                size={18}
                className="absolute left-3 top-3 text-cyan-400/70"
              />
              <input
                ref={inputRef}
                type="text"
                placeholder="Your command (or try /play, /search, /remind...)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                className="w-full pl-10 pr-10 py-3 bg-slate-900/60 border-2 border-cyan-500/50 rounded-lg text-cyan-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400 focus:shadow-lg focus:shadow-cyan-500/50 disabled:opacity-60 transition"
              />
              {input && (
                <button
                  onClick={() => {
                    setInput('');
                    inputRef.current?.focus();
                  }}
                  className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 transition"
                >
                  <X size={18} />
                </button>
              )}
            </div>

            {/* Error message */}
            {error && (
              <p className="text-red-400 text-xs px-3">
                ❌ {error}
              </p>
            )}

            {/* Loading indicator */}
            {isLoading && (
              <p className="text-cyan-300 text-xs px-3">
                ⏳ Routing your command...
              </p>
            )}
          </div>

          {/* Suggestions dropdown */}
          {suggestions.length > 0 && (
            <div className="max-h-64 overflow-y-auto border-t border-slate-700/50 pt-2 space-y-1">
              {suggestions.map((suggestion, index) => (
                <button
                  key={`${suggestion.type}-${suggestion.text}`}
                  onClick={() => handleSubmit(suggestion.text)}
                  className={`w-full px-3 py-2 rounded text-left transition ${
                    index === selectedIndex
                      ? 'bg-cyan-600/40 border border-cyan-500/50 text-cyan-100'
                      : 'hover:bg-slate-800/40 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{suggestion.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-sm truncate">
                        {suggestion.text}
                      </p>
                      {suggestion.description && (
                        <p className="text-xs text-slate-500">
                          {suggestion.description}
                        </p>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Tip text */}
          {!input && !suggestions.length && (
            <div className="text-xs text-slate-500 px-3 py-2 space-y-1">
              <p>✨ Start typing or use a slash command</p>
              <p className="text-slate-600">
                Press <kbd className="px-2 py-0.5 bg-slate-800 rounded">
                  Esc
                </kbd>{' '}
                to close
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CommandBar;
