import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { spawn, type ChildProcess } from "child_process";
import { resolve } from "path";

/**
 * Vite plugin that auto-starts the WorldMonitor dev server (port 3000)
 * whenever SPARK's `npm run dev` is running, so a single npm command
 * drives everything. The child process is killed on SIGINT/SIGTERM.
 */
function spawnWorldMonitorPlugin(): Plugin {
  let wmProcess: ChildProcess | null = null;
  const wmDir = resolve(__dirname, "external/worldmonitor");

  function kill() {
    if (wmProcess) {
      wmProcess.kill("SIGTERM");
      wmProcess = null;
    }
  }

  return {
    name: "spawn-worldmonitor",
    // Only active in dev mode
    apply: "serve",
    configureServer() {
      // Start WorldMonitor on its default port 3000
      wmProcess = spawn("npm", ["run", "dev"], {
        cwd: wmDir,
        stdio: "inherit",
        shell: true,          // required on Windows for npm.cmd resolution
        env: { ...process.env, FORCE_COLOR: "1" },
      });

      wmProcess.on("error", (err) => {
        console.warn(`[spark] WorldMonitor spawn error: ${err.message}`);
      });

      wmProcess.on("exit", (code) => {
        if (code !== null && code !== 0) {
          console.warn(`[spark] WorldMonitor exited with code ${code}`);
        }
        wmProcess = null;
      });

      process.on("exit", kill);
      process.on("SIGINT", () => { kill(); process.exit(0); });
      process.on("SIGTERM", () => { kill(); process.exit(0); });
    },

    closeBundle: kill,
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
    proxy: {
      // WorldMonitor-specific API routes → WorldMonitor dev server (port 3000).
      // Must be declared BEFORE the generic /api catchall so they take precedence.
      // The spawnWorldMonitorPlugin() starts this server automatically.
      '^/api/(rss-proxy|opensky|ais-snapshot|polymarket|intelligence|military|economic|market|conflict|research|unrest|climate|wildfire|displacement|infrastructure|supply-chain|trade|giving|prediction|aviation|maritime|cyber|seismology|positive-events|news|security)(/|$)': {
        target: `http://localhost:${process.env.WORLDMONITOR_PORT || '3000'}`,
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (_err, _req, res) => {
            if (!res.headersSent) {
              (res as any).writeHead(503, { 'Content-Type': 'application/json' });
              (res as any).end(JSON.stringify({ error: 'WorldMonitor server starting up, please wait a moment and retry.' }));
            }
          });
        },
      },
      // SPARK backend routes
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    }
  },
  define: {
    __APP_VERSION__: JSON.stringify('1.0.0'),
    'process.env': {}
  },
  plugins: [react(), spawnWorldMonitorPlugin()].filter(Boolean),
  resolve: {
    alias: {
      "@worldmonitor": path.resolve(__dirname, "./external/worldmonitor/dist-lib/worldmonitor.es.js"),
      "@worldmonitor-css": path.resolve(__dirname, "./external/worldmonitor/dist-lib/world-monitor.css"),
      "@": path.resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom"],
    exclude: ["@worldmonitor"] // Exclude from optimization to rely on pre-built file
  }
}));
