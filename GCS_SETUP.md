# Google Cloud Storage Setup Guide

Your Flask app has been updated to use Google Cloud Storage for persistent image uploads. Follow these steps to complete the setup.

## Step 1: Enable Cloud Storage API

Run this command in your terminal:

```bash
gcloud services enable storage.googleapis.com
```

Expected output: `Operation "operations/..." finished successfully.`

## Step 2: Create GCS Bucket

Create a bucket in the same region as your Cloud Run service (asia-southeast1):

```bash
gcloud storage buckets create gs://drag-drop-quiz-uploads --location=asia-southeast1
```

Expected output: `Creating gs://drag-drop-quiz-uploads/...`

## Step 3: Configure Bucket Permissions

The Cloud Run service account needs read/write access to the bucket. Run:

```bash
gcloud storage buckets add-iam-policy-binding gs://drag-drop-quiz-uploads \
  --member=serviceAccount:drag-drop-quiz@appspot.gserviceaccount.com \
  --role=roles/storage.objectCreator
```

## Step 4: Make Bucket Publicly Readable (Optional - for direct image access)

If you want images to be directly accessible via their GCS URLs:

```bash
gcloud storage buckets add-iam-policy-binding gs://drag-drop-quiz-uploads \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

⚠️ Only do this if you want public read access to all images in the bucket.

## Step 5: Redeploy to Cloud Run

Once GCS is configured, redeploy your application:

```bash
gcloud run deploy drag-drop-quiz --source . --region asia-southeast1 --allow-unauthenticated
```

The deployment will:
1. Build and push the Docker image
2. Deploy the updated app with GCS support
3. Keep your existing Cloud Run configuration

## Step 6: Test Image Uploads

1. Open your admin dashboard: https://drag-drop-quiz-90751091622.asia-southeast1.run.app/admin/login
2. Create or edit a quiz
3. Upload a new image
4. Images should now persist across container restarts ✅

## How It Works

- **Fallback System**: If GCS is unavailable, the app automatically falls back to local storage
- **Auto-public URLs**: Uploaded images are automatically made public in GCS
- **Unique Filenames**: Files are saved with timestamp prefixes to avoid conflicts
- **File Format**: Images are stored as-is (preserving original format)

## Troubleshooting

### "Permission denied" during upload
- Verify the Cloud Run service account has `roles/storage.objectCreator` role
- Check bucket exists: `gcloud storage buckets list`

### "Bucket does not exist" error
- Ensure bucket name is `gs://drag-drop-quiz-uploads`
- Check region matches Cloud Run: `gcloud run services describe drag-drop-quiz --region asia-southeast1`

### Images still return 404
- Check Cloud Run logs: `gcloud run services logs read drag-drop-quiz --limit 50`
- Ensure `google-cloud-storage==2.14.0` is in requirements.txt

## Verify Configuration

To verify GCS setup is working:

```bash
# List objects in bucket
gcloud storage ls gs://drag-drop-quiz-uploads/

# Check bucket permissions
gcloud storage buckets describe gs://drag-drop-quiz-uploads --format=json | jq '.iamConfiguration'
```

## Next Steps

After confirming images persist:
1. Clean up old local upload files if needed: `rm -rf static/uploads/*`
2. Monitor Cloud Run logs for any GCS errors
3. Consider setting up bucket lifecycle policies to auto-delete old images (optional)
