# HH Parser Bot

Бот для мониторинга вакансий с hh.ru с отправкой в Telegram.

## 🚀 Быстрый старт
```
pip install -r requirements.txt
python src/builder.py
python src/main.py
```

## 📁 Структура проекта

    src/main.py - основной скрипт мониторинга

    src/builder.py - настройка параметров поиска

    src/parser.py - парсинг вакансий и работа с БД

    tests/ - тесты

    config.json - файл конфигурации

## 🔧 Функции

    ✅ Автопарсинг вакансий с hh.ru

    ✅ Проверка релевантности (fuzzy matching)

    ✅ Отправка в Telegram

    ✅ История отправок (MySQL)

    ✅ Периодическая проверка

    ✅ Защита от дубликатов
