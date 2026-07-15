@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\validate_local_flow.ps1" %*
