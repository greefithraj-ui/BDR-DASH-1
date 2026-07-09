import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import fs from 'fs';
import {execSync} from 'child_process';
import {defineConfig, loadEnv} from 'vite';

const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:8000';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [
      tailwindcss(),
      {
        name: 'minify-non-module-scripts',
        closeBundle: () => {
          const scripts = ['app.js', 'wake-lock.js'];
          scripts.forEach(file => {
            if (fs.existsSync(file)) {
              execSync(`npx esbuild ${file} --minify --outfile=dist/${file} --allow-overwrite`, { stdio: 'inherit' });
            }
          });
        },
      },
    ],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      host: '0.0.0.0',
      hmr: {
        host: process.env.VITE_HMR_HOST || undefined,
        protocol: 'ws',
      },
      configureServer(server) {
        server.middlewares.use('/favicon.ico', (_req, res) => {
          res.statusCode = 204;
          res.end();
        });
        server.middlewares.use('/api/rings_config', (_req, res) => {
          let ringsConfigPath = path.resolve(__dirname, 'rings_config.json');
          if (!fs.existsSync(ringsConfigPath)) {
            ringsConfigPath = path.resolve(__dirname, '..', 'NEW JSON', 'rings_config.json');
          }
          
          if (!fs.existsSync(ringsConfigPath)) {
            res.statusCode = 404;
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ error: 'rings_config.json not found' }));
            return;
          }

          try {
            const data = fs.readFileSync(ringsConfigPath, 'utf8');
            res.setHeader('Content-Type', 'application/json');
            res.end(data);
          } catch (e) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: 'Failed to read rings_config.json' }));
          }
        });
      },
      proxy: {
        '/api': {
          target: API_TARGET,
          changeOrigin: true,
        },

      },
    },
  };
});
