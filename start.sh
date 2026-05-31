#!/bin/bash

# Запуск API сервера и бота одновременно
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} &
python bot/bot.py
