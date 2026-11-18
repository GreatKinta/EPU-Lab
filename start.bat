@echo off
title Quan ly thiet bi
cd /d "%~dp0"

if not exist node_modules (
  echo Dang cai thu vien...
  call npm install
)

if not exist .env (
  echo Chua co file .env. Hay sao chep .env.example thanh .env va dien gia tri.
  pause
  exit /b
)

echo Dang khoi dong may chu tai http://localhost:3000
start "" http://localhost:3000
node server.js
pause