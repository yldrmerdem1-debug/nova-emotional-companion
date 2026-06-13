@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0backend"

echo.
echo ==========================================
echo   ROBOT SELF-TRAINING BASLIYOR
echo ==========================================
echo.
echo Once hazirlik seviyesi kontrol edilecek.
echo Hazir degilse self-training baslamayacak,
echo raporda hangi alanlar eksik gosterilecek.
echo.

py run_self_training.py --cycles 10 --domains cpp python java math physics algorithms --require-ready --report "app\data\generated\self_training_report.md"

echo.
echo ==========================================
echo   SELF-TRAINING TAMAMLANDI
echo ==========================================
echo.
echo Rapor aciliyor:
echo backend\app\data\generated\self_training_report.md
echo.

start "" "%cd%\app\data\generated\self_training_report.md"

echo Bu pencereyi kapatmak icin bir tusa bas.
pause > nul
