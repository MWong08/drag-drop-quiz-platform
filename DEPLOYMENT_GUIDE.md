# Deployment Guide: Firebase Hosting + Google Cloud Run

This guide explains how to deploy your Drag & Drop Quiz application using Firebase Hosting for the frontend and Google Cloud Run for the backend.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Firebase Hosting (Frontend)                │
│         - HTML, CSS, JS files                          │
│         - Automatic HTTPS                              │
│         - CDN distribution                             │
└─────────────────────────────────────────────────────────┘
                          ↓
                   (API calls to)
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Google Cloud Run (Backend - Flask)             │
│         - Docker containerized app                      │
│         - Auto-scaling                                 │
│         - Pay per use (Free tier available)            │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Google Cloud Account** (Free tier: $300 credit)
   - Sign up at: https://cloud.google.com/free

2. **Firebase Project** (Already created: drag-drop-live-quiz)
   - Already set up with your Firebase credentials

3. **Install Required Tools:**
   ```bash
   # Node.js and npm (for Firebase CLI)
   # Download from: https://nodejs.org/
   
   # Install Firebase CLI
   npm install -g firebase-tools
   
   # Google Cloud SDK
   # Download from: https://cloud.google.com/sdk/docs/install
   ```

---

## Step 1: Set Up Google Cloud Project

### 1.1 Create a Google Cloud Project
```bash
# Login to Google Cloud
gcloud auth login

# Create a new project
gcloud projects create drag-drop-quiz --name="Drag Drop Quiz"

# Set as default project
gcloud config set project drag-drop-quiz

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

**⚠️ Security Note:** Do NOT create service account keys (key.json). Cloud Run authentication via `gcloud` is secure and sufficient. Downloaded service account keys are a security risk and unnecessary.

---

## Step 2: Deploy Backend to Google Cloud Run

### 2.1 Prepare Your Flask App

Ensure `app.py` has the correct Socket.IO configuration for Cloud Run:

```python
# Socket.IO configuration (in your app initialization)
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://drag-drop-live-quiz.web.app"  # Your Firebase Hosting domain
    ],
    async_mode="eventlet"  # CRITICAL: Required for Cloud Run WebSocket support
)

# Port configuration (at the end of app.py)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
```

⚠️ **Important:** The `async_mode="eventlet"` is CRITICAL. Without it, Socket.IO connections will randomly disconnect on Cloud Run.

### 2.2 Build and Deploy

```bash
# Navigate to your project directory
cd "c:\Users\wongm\OneDrive\Desktop\Troffee\Drag Drop Question"

# Deploy to Cloud Run using asia-southeast1 region (closer to Malaysia, lower latency)
gcloud run deploy drag-drop-quiz \
  --source . \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated
```

**Note:** asia-southeast1 (Singapore) is recommended for better latency. If you prefer a different region, use --region flag with other options like us-central1, europe-west1, etc.

After deployment, you'll get a URL like:
```
https://drag-drop-quiz-xxxxx.a.run.app
```

**Save this URL** - you'll need it for the frontend.

---

## Step 3: Update Frontend to Call Backend

### 3.1 Create a Config File for API Endpoint

Your `static/config.js` is already created:

```javascript
// API Configuration
// Update this with your Cloud Run backend URL
const API_BASE_URL = 'https://drag-drop-quiz-xxxxx.a.run.app';

// Use this for all your fetch calls:
// fetch(`${API_BASE_URL}/api/endpoint`, {...})
```

### 3.2 Update HTML Files

In your HTML templates, reference the config:

```html
<script src="/config.js"></script>

<script>
  // Now use API_BASE_URL in your fetch calls
  fetch(`${API_BASE_URL}/api/quizzes`)
    .then(response => response.json())
    .then(data => console.log(data));
</script>
```

---

## Step 4: Deploy Frontend to Firebase Hosting

### 4.1 Initialize Firebase CLI

```bash
# Login to Firebase
firebase login

# Initialize Firebase in your project
firebase init hosting

# When prompted:
# - Select your project: drag-drop-live-quiz
# - What do you want to use as your public directory? static
# - Configure as single-page app (SPA)? No (your index.html is the landing page, not a SPA router)
```

**Note:** firebase.json is already configured in your project root with proper routing settings.

### 4.2 Deploy to Firebase Hosting

```bash
# Deploy your static files
firebase deploy --only hosting
```

You'll get a hosting URL like:
```
https://drag-drop-live-quiz.web.app
```

---

## Step 5: Configure CORS for Backend

Both Flask and Socket.IO need CORS configuration. Your `app.py` is already updated with:

```python
from flask_cors import CORS

# Configure Flask-CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://drag-drop-live-quiz.web.app"]
    }
})

# Configure Socket.IO CORS (with eventlet)
socketio = SocketIO(
    app,
    cors_allowed_origins=["https://drag-drop-live-quiz.web.app"],
    async_mode="eventlet"  # CRITICAL
)
```

⚠️ **Note:** Flask-CORS alone is NOT sufficient for Socket.IO. Socket.IO requires its own CORS configuration as shown above.

---

## Deployment Checklist

- [ ] Google Cloud Project created
- [ ] APIs enabled (Cloud Run, Cloud Build, Artifact Registry)
- [ ] Socket.IO configured with async_mode="eventlet" ✅ (Done)
- [ ] Flask CORS and Socket.IO CORS configured ✅ (Done)
- [ ] Dockerfile present and working ✅ (Done)
- [ ] Backend deployed to Cloud Run (asia-southeast1)
- [ ] Firebase config added to static/firebaseConfig.js ✅ (Done)
- [ ] Frontend config.js created with Cloud Run URL ✅ (Done)
- [ ] requirements.txt includes eventlet==0.33.3+ ✅ (Done)
- [ ] firebase.json configured in project root ✅ (Done)
- [ ] Frontend deployed to Firebase Hosting
- [ ] Test API calls from frontend to backend
- [ ] Test Socket.IO connections (real-time features)

---

## Useful Commands

### Monitor Cloud Run Logs
```bash
gcloud run logs read drag-drop-quiz --limit 50
```

### Redeploy Backend
```bash
gcloud run deploy drag-drop-quiz --source .
```

### Redeploy Frontend
```bash
firebase deploy --only hosting
```

### View Deployment Status
```bash
# Firebase
firebase hosting:sites:list

# Cloud Run
gcloud run services list
```

---

## Troubleshooting

### CORS Issues
- Ensure Flask has `flask-cors` installed ✅
- Update CORS origins to match your Firebase Hosting URL
- Check browser console for specific CORS errors

### Cloud Run Deployment Fails
```bash
# Check logs
gcloud run logs read drag-drop-quiz

# Redeploy with more verbose output
gcloud run deploy drag-drop-quiz --source . --allow-unauthenticated --quiet
```

### Firebase Hosting Issues
```bash
# Check if .firebaserc is correct
cat .firebaserc

# Clear cache and redeploy
firebase deploy --force
```

### Socket.IO Connection Issues

**Problem:** Socket.IO connections disconnect randomly or fail

**Solutions:**
1. Ensure `async_mode="eventlet"` is set in SocketIO initialization ✅
2. Verify eventlet version: `pip show eventlet` (should be 0.33.3 or higher) ✅
3. Configure CORS properly ✅
4. Check Cloud Run logs: `gcloud run logs read drag-drop-quiz --limit 50`

---

## Cost Estimate (Free Tier)

| Service | Free Tier | Your Project |
|---------|-----------|--------------|
| Firebase Hosting | 1GB storage, 10GB/month bandwidth | ✅ Included |
| Cloud Run | 2M requests/month, 360k GB-seconds/month | ✅ Included |
| Cloud Build | 120 free build minutes/month | ✅ Included |

**Your project should fit comfortably in the free tier!**

---

## Final Recommended Deployment Flow

```bash
# 1. Authenticate
gcloud auth login
firebase login

# 2. Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 3. Deploy backend to Cloud Run
gcloud run deploy drag-drop-quiz \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated

# 4. Note the Cloud Run URL output (e.g., https://drag-drop-quiz-xxxxx.a.run.app)

# 5. Update static/config.js with your Cloud Run URL
# Replace 'https://drag-drop-quiz-xxxxx.a.run.app' with your actual URL

# 6. Deploy frontend to Firebase Hosting
firebase deploy --only hosting

# 7. Test your application at:
# https://drag-drop-live-quiz.web.app
```

---

## Next Steps

1. Follow the Final Deployment Flow above
2. Test API calls and Socket.IO connections thoroughly
3. Monitor your Cloud Run logs regularly
4. Set up alerts if you approach free tier limits

For detailed documentation:
- [Firebase Hosting Docs](https://firebase.google.com/docs/hosting)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Flask Deployment Docs](https://flask.palletsprojects.com/en/2.3.x/deploying/)
