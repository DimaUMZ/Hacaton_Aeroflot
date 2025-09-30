#!/bin/bash

# start-project.sh - Скрипт запуска всего проекта

echo "🚀 Запуск Aeroflot Tool Management System..."

# Переменные путей
BACKEND_DIR="/data/vscode/HacatonAeroflot/Aeroflot-project/app/schemas"
FRONTEND_DIR="/data/vscode/HacatonAeroflot/Aeroflot-project/app/warehouse-frontend"

# Функция проверки порта
check_port() {
    nc -z localhost $1 >/dev/null 2>&1
}

# Останавливаем сервисы если уже запущены
echo "🛑 Остановка предыдущих процессов..."
pkill -f "python.*working_api" || true
pkill -f "HTTPS=true npm.*start" || true

# Ждем освобождения портов
sleep 2

# Запускаем бэкенд
echo "🔧 Запуск бэкенда на порту 8001..."
cd "$BACKEND_DIR"
python3 working_api.py &
BACKEND_PID=$!

# Ждем запуска бэкенда
echo "⏳ Ожидаем запуск бэкенда..."
for i in {1..10}; do
    if check_port 8001; then
        echo "✅ Бэкенд запущен!"
        break
    fi
    echo "⏱️  Попытка $i/10..."
    sleep 2
done

# Проверяем бэкенд
if check_port 8001; then
    echo "🔍 Проверяем API бэкенда..."
    curl -s http://localhost:8001/api/health && echo " ✅ API работает"
else
    echo "❌ Бэкенд не запустился за 20 секунд"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Запускаем фронтенд
echo "🎨 Запуск фронтенда..."
cd "$FRONTEND_DIR"
HTTPS=true npm start &
FRONTEND_PID=$!

echo ""
echo "🎉 Проект запущен!"
echo "📍 Бэкенд: http://localhost:8001"
echo "📍 Фронтенд: http://localhost:3000 (или 3001)"
echo "📚 Документация: http://localhost:8001/docs"
echo ""
echo "⏹️  Для остановки нажмите Ctrl+C"

# Обработка Ctrl+C
trap "echo ''; echo '🛑 Останавливаем сервисы...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT

# Бесконечное ожидание
wait