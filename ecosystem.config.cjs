module.exports = {
  apps: [{
    name: 'bdr-api',
    script: 'D:\\BDR\\data\\main.py',
    interpreter: 'C:\\Users\\meshe\\AppData\\Local\\Programs\\Python\\Python312\\python.exe',
    args: '--bg-api --start-pg',
    restart_delay: 10000,
    kill_timeout: 10000,
    merge_logs: true,
    min_uptime: 30000,
    autorestart: true,
    env: {
      AQC_PASSWORD: '1234',
      NO_STARTUP_INDEX: '1'
    }
  }]
};
