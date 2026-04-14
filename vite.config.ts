import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    watch: {
      ignored: ["**/.venv/**", "**/venv/**", "**/node_modules/**"],
    },
    hmr: {
      overlay: false,
    },
    proxy: {
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
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@deck.gl/core": path.resolve(__dirname, "node_modules/@deck.gl/core/dist/index.js"),
      "@deck.gl/layers": path.resolve(__dirname, "node_modules/@deck.gl/layers/dist/index.js"),
      "@deck.gl/react": path.resolve(__dirname, "node_modules/@deck.gl/react/dist/index.js")
    },
  },
  optimizeDeps: {
    entries: ["index.html"],
    include: ["react", "react-dom"]
  }
}));
