@echo off
echo Starting BDR API via PM2...
cd /d "%~dp0.."
pm2 start ecosystem.config.cjs --only bdr-api
echo.
echo API started. Run "pm2 logs bdr-api" to see output.
