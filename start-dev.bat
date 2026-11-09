@echo off
echo ===================================================
echo Starting DocMind AI Assistant (Backend + Frontend)
echo ===================================================

echo Starting Django Backend on http://127.0.0.1:8000/api...
start "DocMind Backend" cmd /k "venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000"

echo Starting Vite Frontend on http://localhost:5173...
start "DocMind Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are launching in separate windows!
echo Open your browser at: http://localhost:5173/
echo ===================================================
