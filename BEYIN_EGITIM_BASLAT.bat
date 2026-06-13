@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0backend"

echo.
echo ==========================================
echo   BEYIN EGITIM V2 BASLIYOR
echo ==========================================
echo.
echo World model kurulacak.
echo Curriculum engine siradaki egitimi sececek.
echo Robot problem cozecek.
echo Verifier kontrol edecek.
echo API bagliysa AI mentor elestiri verecek.
echo.

py run_brain_training.py --cycles 12 --report "app\data\generated\brain_training_report.md"

echo.
echo ==========================================
echo   BEYIN EGITIM V2 TAMAMLANDI
echo ==========================================
echo.
echo Rapor aciliyor:
echo backend\app\data\generated\brain_training_report.md
echo.

start "" "%cd%\app\data\generated\brain_training_report.md"

echo Bu pencereyi kapatmak icin bir tusa bas.
pause > nul
