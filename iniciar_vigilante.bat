@echo off
title Vigilante Binance 24/7 - d:\trader
color 0A
cd /d "%~dp0"
echo =====================================================================
echo   INICIANDO VIGILANTE BINANCE 24/7 CON NOTIFICACIONES A TELEGRAM
echo =====================================================================
echo   Activos vigilados : MSTR, BTC, SOL
echo   Tope de riesgo    : -$15.00 USDT maximo por trade
echo   Capital de cuenta : $500.00 USDT
echo   Apalancamiento    : 3x
echo   Intervalo escaneo : Cada 30 segundos
echo   Notificaciones    : Directo a tu Telegram
echo =====================================================================
echo.

"C:\Users\javie\AppData\Local\Programs\Python\Python313\python.exe" vigilante_binance.py MSTR BTC SOL --max-risk 15 --capital 500 --lev 3 --intervalo 30

pause
