import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import React from "react";
import Index from "./pages/Index";
import GlobeMonitor from "./pages/GlobeMonitor";
import CognitiveDashboard from "./pages/CognitiveDashboard";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import { AuthProvider, useAuth } from "./contexts/AuthContext";

const queryClient = new QueryClient();

// ── Global error boundary — catches runtime crashes and shows a message ───────
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          position: 'fixed', inset: 0, background: '#010812',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', fontFamily: 'monospace', color: '#00f5ff',
          padding: '2rem', gap: '1rem',
        }}>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, letterSpacing: '0.2em' }}>
            ⚠ SPARK RUNTIME ERROR
          </div>
          <div style={{ color: '#f87171', fontSize: '0.85rem', maxWidth: '700px', textAlign: 'center', wordBreak: 'break-word' }}>
            {this.state.error.message}
          </div>
          <button
            onClick={() => { this.setState({ error: null }); window.location.href = '/'; }}
            style={{ marginTop: '1rem', padding: '0.5rem 1.5rem', border: '1px solid #00f5ff44',
              background: '#00f5ff12', color: '#00f5ff', cursor: 'pointer',
              borderRadius: '6px', letterSpacing: '0.15em', fontSize: '0.75rem' }}
          >
            RELOAD SPARK
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Route guard ───────────────────────────────────────────────────────────────
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{
        position: 'fixed', inset: 0, background: '#010812',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: '1rem',
      }}>
        <div style={{
          width: '40px', height: '40px', border: '2px solid #00f5ff30',
          borderTop: '2px solid #00f5ff', borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }} />
        <div style={{ fontFamily: 'monospace', color: '#00f5ff60', fontSize: '0.7rem',
          letterSpacing: '0.2em' }}>
          AUTHENTICATING…
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <BrowserRouter>
        <ErrorBoundary>
          <AuthProvider>
            <Routes>
              {/* Public */}
              <Route path="/login" element={<Login />} />

              {/* Protected */}
              <Route path="/" element={<ProtectedRoute><Index /></ProtectedRoute>} />
              <Route path="/globe" element={<ProtectedRoute><GlobeMonitor /></ProtectedRoute>} />
              <Route path="/globe-monitor" element={<ProtectedRoute><GlobeMonitor /></ProtectedRoute>} />
              <Route path="/cognitive" element={<ProtectedRoute><CognitiveDashboard /></ProtectedRoute>} />
              <Route path="/os" element={<ProtectedRoute><CognitiveDashboard /></ProtectedRoute>} />

              {/* Catch-all */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </AuthProvider>
        </ErrorBoundary>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

