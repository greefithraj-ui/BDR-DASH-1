require('dotenv').config();

module.exports = {
  apps: [{
    name: 'bdr-api',
    script: 'data/main.py',
    args: '--bg-api',
    interpreter: 'C:\\Users\\meshe\\AppData\\Local\\Programs\\Python\\Python312\\python.exe',
    cwd: __dirname,
    max_restarts: 0,
    min_uptime: '30s',
    restart_delay: 10000,
    watch: false,
    windows_hide_console: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    merge_logs: true,
    kill_timeout: 10000,
    env: {
      AQC_PASSWORD: process.env.AQC_PASSWORD || '1234',
      NO_STARTUP_INDEX: '0'
    }
  }]
};
