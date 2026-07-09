import express from 'express';
import path from 'path';
import fs from 'fs';
import http from 'http';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.PORT || '3001', 10);
const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:8000';
const DIST_DIR = path.resolve(__dirname, 'dist');

const app = express();

app.use(express.raw({ type: '*/*', limit: '10mb' }));

const apiUrl = new URL(API_TARGET);

function proxyToApi(req, res) {
  const options = {
    hostname: apiUrl.hostname,
    port: parseInt(apiUrl.port, 10) || 80,
    path: req.originalUrl,
    method: req.method,
    headers: { ...req.headers, host: apiUrl.hostname },
  };
  if (req.body && Buffer.isBuffer(req.body) && req.body.length > 0) {
    options.headers['content-length'] = req.body.length;
  }
  delete options.headers['transfer-encoding'];

  const proxyReq = http.request(options, (proxyRes) => {
    const chunks = [];
    proxyRes.on('data', (c) => chunks.push(c));
    proxyRes.on('end', () => {
      const body = Buffer.concat(chunks);
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      res.end(body);
    });
  });
  proxyReq.on('error', (err) => {
    res.statusCode = 502;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Bad Gateway', detail: err.message }));
  });
  if (req.body && Buffer.isBuffer(req.body) && req.body.length > 0) {
    proxyReq.end(req.body);
  } else {
    proxyReq.end();
  }
}

app.get('/api/rings_config', (req, res) => {
  let configPath = path.resolve(__dirname, 'rings_config.json');
  if (!fs.existsSync(configPath)) {
    configPath = path.resolve(__dirname, '..', 'NEW JSON', 'rings_config.json');
  }
  if (!fs.existsSync(configPath)) {
    res.statusCode = 404;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'rings_config.json not found' }));
    return;
  }
  res.setHeader('Content-Type', 'application/json');
  res.sendFile(configPath);
});

app.use('/api', proxyToApi);

app.use(express.static(DIST_DIR, { index: 'index.html' }));

app.get('*', (req, res) => {
  res.sendFile(path.join(DIST_DIR, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[serve-dist] Serving ${DIST_DIR}`);
  console.log(`[serve-dist] Proxy /api/* -> ${API_TARGET}`);
  console.log(`[serve-dist] http://localhost:${PORT}`);
});
