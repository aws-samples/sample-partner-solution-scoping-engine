import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 7001,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost'
      // -- CORS SETTING -- Place a comma at the end of the above line, uncomment the below line for a procution server (use your registered domain name)
      // 'your-domain.com'
    ],
    proxy: {
      '^/api/.*': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        ws: true,
        logLevel: 'silent',
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.debug('PROXY ERROR:', err);
          });
          // Only log in development mode
          if (process.env.NODE_ENV !== 'production') {
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.debug('PROXY REQUEST:', req.method, req.url, '->', proxyReq.path);
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.debug('PROXY RESPONSE:', proxyRes.statusCode, req.url);
            });
          }
        }
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    //minify: 'terser',
    //terserOptions: {
    //  compress: {
    //    drop_console: false,  // Keep console.error and console.warn
    //    pure_funcs: ['console.debug', 'console.log', 'console.info']  // Remove these functions
    //  }
    //},
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          cloudscape: ['@cloudscape-design/components']
        }
      }
    }
  },
  base: '/',  // This ensures assets are loaded from the root path
  define: {
    // -- CORS SETTING -- Uncomment the below line for local development, comment out for production
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'http://localhost:5001/api')
    // -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
    // 'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'https://your-domain.com/api')
  }
})
