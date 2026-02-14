# Parse Pro AI - Quick Start Guide (Windows 11)

Get Parse Pro AI running on Windows 11 in under 5 minutes.

---

## Prerequisites

✅ Python 3.10+ installed  
✅ Redis/Memurai running on port 6379  
✅ OpenRouter API key (free tier works!)

---

## Step 1: Clone & Setup

```powershell
# Navigate to project directory
cd "d:\Projects\Academic Projects\Resume Parse Pro AI"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already done)
pip install eventlet
```

---

## Step 2: Configure Environment

Your `.env` file is already configured with:
- ✅ Free tier OpenRouter models (`gpt-oss-20b:free`, `qwen3-next-80b:free`)
- ✅ Eventlet worker pool for Windows 11
- ✅ 8 concurrent workers

**Verify your `.env` has:**
```env
OPENROUTER_API_KEY=your-key-here
CELERY_WORKER_POOL=eventlet
CELERY_WORKER_CONCURRENCY=8
```

---

## Step 3: Run Database Migrations (First Time Only)

```powershell
python manage.py migrate
python manage.py createsuperuser
```

---

## Step 4: Start the Application

### Option A: Use the Startup Script (Recommended)

```powershell
# Start Django + 1 Celery worker (8 concurrent tasks)
.\scripts\start-parsepro.ps1

# OR start with 2 workers for more throughput
.\scripts\start-parsepro.ps1 -Workers 2
```

This will open 2-3 PowerShell windows:
- Window 1: Django server (http://localhost:8000)
- Window 2: Celery worker

### Option B: Manual Start

```powershell
# Terminal 1: Django
.\.venv\Scripts\Activate.ps1
python manage.py runserver

# Terminal 2: Celery (eventlet pool)
.\.venv\Scripts\Activate.ps1
celery -A config worker -l info -P eventlet -c 8 -Q resume_parse
```

---

## Step 5: Access the Application

Open your browser:
- **Main App:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs/
- **Admin Panel:** http://localhost:8000/admin/

---

## Step 6: Upload Your First Resume

1. Navigate to **Upload** page
2. Click **Choose Files** and select one or more resumes (PDF/DOCX)
3. See the **file preview list** with all selected files
4. Optionally set filters (skills, experience, role, etc.)
5. Click **Upload and Parse**
6. Watch the **progress bar** and see real-time results!

---

## Managing the Application

### Check Status
```powershell
.\scripts\status-parsepro.ps1
```

### Stop Everything
```powershell
.\scripts\stop-parsepro.ps1
```

### Restart After Changes
```powershell
.\scripts\stop-parsepro.ps1 -Force
.\scripts\start-parsepro.ps1
```

---

## Free Tier Rate Limits

OpenRouter free tier (0 credits) has daily request limits:
- ✅ **Model fallbacks** automatically handle rate limits
- ✅ **Smart retry logic** waits and retries when rate limited
- ✅ **Status checking** prevents unnecessary API calls

**Monitor your usage:**
- Check logs: `Get-Content logs\app.log -Tail 50`
- Look for: "rate limited" or "fallback model used"

---

## Troubleshooting

### Celery won't start
```powershell
# Make sure Redis/Memurai is running
Get-Process | Where-Object { $_.ProcessName -like "*memurai*" }

# If eventlet has issues, fall back to solo pool
.\scripts\start-parsepro.ps1 -Pool solo -Workers 4
```

### Upload page doesn't show file preview
- Clear browser cache and reload
- Check browser console (F12) for errors
- Verify `static/js/pages.js` is loaded

### Rate limit errors
- Verify `.env` has valid `OPENROUTER_API_KEY`
- Check if fallback models are configured in `settings.py`
- Wait a few minutes if daily limit is exhausted

### Files stuck in "processing"
- Check Celery worker terminal for errors
- Verify Redis is running
- Check `logs/celery.log` for details

---

## What's New in This Version

✨ **File Preview List** - See all selected files before uploading  
✨ **Upload Progress Bar** - Real-time progress indicators  
✨ **User-Friendly Messages** - No more technical jargon  
✨ **8x Faster Processing** - Eventlet pool for Windows 11  
✨ **Free Tier Optimized** - Smart model fallbacks and rate limit handling  
✨ **Detailed Results** - Color-coded accepted/rejected/errors display  

---

## Need Help?

- **Logs:** Check `logs/app.log` and `logs/celery.log`
- **Status:** Run `.\scripts\status-parsepro.ps1`
- **Documentation:** See `docs/` folder
- **Architecture:** See `docs/IMPROVEMENTS.md`

---

## Next Steps

1. ✅ Upload some test resumes
2. ✅ Try the bulk upload feature (10+ files)
3. ✅ Test filters (skills, experience, role matching)
4. ✅ Explore the Candidates page
5. ✅ Export candidates to CSV
6. ✅ Edit candidate profiles (audit logging enabled!)

Enjoy using Parse Pro AI! 🚀
