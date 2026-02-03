# Celery Restart Guide - IMPORTANT!

## ⚠️ Critical: When to Restart Celery

Unlike Django's `runserver` which auto-reloads when code changes, **Celery workers DO NOT auto-reload**.

---

## When You MUST Restart Celery Workers

Restart Celery whenever you change:

✅ `.env` file (API keys, config variables)  
✅ `config/settings.py` (any settings)  
✅ `resumes/pipeline.py` (LLM functions)  
✅ `resumes/tasks.py` (Celery tasks)  
✅ `resumes/services.py` (service functions)  
✅ Any Python code used by Celery tasks  

**If you don't restart:** Workers will use OLD code/config, causing errors!

---

## How to Restart Celery (Windows 11)

### Option 1: Use Scripts (Recommended)

```powershell
# Stop all workers
.\scripts\stop-parsepro.ps1 -Force

# Start fresh worker with new config
.\scripts\start-parsepro.ps1
```

### Option 2: Manual Restart

```powershell
# 1. Find and kill all Celery processes
Get-Process | Where-Object { $_.ProcessName -like '*celery*' } | Stop-Process -Force

# 2. Start new worker
.\.venv\Scripts\Activate.ps1
celery -A config worker -l info -P eventlet -c 8 -Q resume_parse
```

---

## How to Check if Restart is Needed

### Check Worker Start Time

```powershell
Get-Process | Where-Object { $_.ProcessName -like '*celery*' } | Format-Table Id, StartTime
```

If the StartTime is **before** your last code change → **RESTART NEEDED!**

### Check Worker Count

```powershell
.\scripts\status-parsepro.ps1
```

If you see multiple workers with different start times → **Old workers running!**

---

## Common Symptoms of Stale Workers

| Symptom | Cause | Solution |
|---------|-------|----------|
| API key error (401) | Worker using old API key | Restart Celery |
| Import errors | Worker using old code | Restart Celery |
| Settings not applied | Worker loaded old settings | Restart Celery |
| Wrong model used | Worker using old config | Restart Celery |
| Tasks not processing | Worker queue mismatch | Restart Celery |

---

## Development Workflow

When developing, use this workflow:

```powershell
# 1. Make code changes to pipeline.py, tasks.py, settings.py, etc.

# 2. Restart Celery (Django auto-reloads, but Celery doesn't!)
.\scripts\stop-parsepro.ps1 -Force
.\scripts\start-parsepro.ps1

# 3. Test your changes
# Upload a resume and check results
```

---

## Production Deployment

For production, use a process manager that handles restarts:

### Option A: Systemd (Linux)
```bash
sudo systemctl restart celery
```

### Option B: Supervisor
```bash
supervisorctl restart parsepro-celery
```

### Option C: PM2
```bash
pm2 restart parsepro-celery
```

---

## Monitoring Worker Status

### Check if Workers are Healthy

```powershell
# Check process status
.\scripts\status-parsepro.ps1

# Check Celery logs
Get-Content logs\celery.log -Tail 50

# Monitor in real-time
Get-Content logs\celery.log -Tail 50 -Wait
```

### Verify Workers are Using New Code

After restart, check the Celery terminal output:
- Should show: "celery@worker1 ready"
- Should load: Latest Python modules
- Should show: Current API key being used (first few chars in logs)

---

## Auto-Reload for Development (Optional)

You can enable Celery auto-reload during development:

```powershell
# Start Celery with watchdog (auto-reloads on code changes)
celery -A config worker -l info -P eventlet -c 8 --autoreload
```

**Note:** This adds overhead and is only for development!

---

## Quick Reference

| Action | Command |
|--------|---------|
| Stop all workers | `.\scripts\stop-parsepro.ps1 -Force` |
| Start workers | `.\scripts\start-parsepro.ps1` |
| Check status | `.\scripts\status-parsepro.ps1` |
| View logs | `Get-Content logs\celery.log -Tail 50` |
| Restart (full) | Stop → Start |

---

## Summary

**KEY TAKEAWAY:** After changing `.env`, settings, or task code:

```powershell
.\scripts\stop-parsepro.ps1 -Force
.\scripts\start-parsepro.ps1
```

This ensures workers load the latest code and configuration! 🚀
