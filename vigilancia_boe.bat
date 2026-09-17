@echo off
REM vigilancia_boe.bat -- lanzador para la tarea programada de Windows
REM (PENDIENTE.md, punto 2.D). No hace nada nuevo: llama a
REM "python boe_normativa.py --comprobar" (que ya vigila las 25 citas y
REM anexos registrados) y deja constancia en un log local.
REM
REM No lleva ningun dato de cliente -- boe_normativa.py solo compara texto
REM legal PUBLICO contra el BOE. El log no necesita el marcador _LOCAL por
REM esa razon (no es un dato operativo de un cliente), pero sigue sin
REM versionarse por ser una salida generada, no codigo -- ver .gitignore.
REM
REM Registrar la tarea es cosa de Diego (ver el comando schtasks en el
REM commit que introduce este fichero, o EMPEZAR_AQUI.md / PENDIENTE.md):
REM crear/cambiar tareas programadas es una modificacion del sistema, y
REM Claude no la hace por su cuenta (.claude/rules/seguridad.md).

setlocal
cd /d "%~dp0"

echo ============================================================ >> vigilancia_boe.log
echo %date% %time% >> vigilancia_boe.log
python boe_normativa.py --comprobar >> vigilancia_boe.log 2>&1
set CODIGO=%errorlevel%
echo codigo de salida: %CODIGO% >> vigilancia_boe.log
echo. >> vigilancia_boe.log

exit /b %CODIGO%
