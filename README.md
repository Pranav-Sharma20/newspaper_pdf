# Newspaper PDF Web Application

Web interface for generating labeled newspaper PDFs from uploaded images.

## Features
- Upload multiple images from mobile/desktop
- Priority ordering with customizable list
- Optional label boxes (black background, yellow text)
- Adjustable font size
- Image scaling options
- Download generated PDF instantly

## Local Testing
```powershell
cd C:\Archana\web_app
python -m pip install -r requirements.txt
python app.py
```
Open http://localhost:5000 in your browser or mobile phone (same network).

## Deploy to Render.com (Free)
1. Create account at https://render.com
2. New > Web Service
3. Connect your GitHub repo or upload this folder
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app`
6. Click "Create Web Service"
7. Your app will be live at https://your-app-name.onrender.com

## Deploy to PythonAnywhere (Free)
1. Create account at https://www.pythonanywhere.com
2. Upload files to /home/yourusername/web_app
3. Web tab > Add new web app > Flask
4. Set source code path and virtualenv
5. Install requirements in Bash console:
   ```bash
   pip install -r requirements.txt
   ```
6. Reload web app

## Deploy to Railway.app
1. Create account at https://railway.app
2. New Project > Deploy from GitHub
3. Select repository
4. Railway auto-detects Flask app
5. Deploy automatically

## Usage from Mobile
1. Open the deployed URL on your Android phone
2. Tap "Click to upload" or drag images
3. Configure priority list and options
4. Tap "Generate PDF"
5. PDF downloads automatically

## Environment Variables (Optional)
- `MAX_CONTENT_LENGTH`: Max upload size in bytes (default 50MB)
- `FLASK_ENV`: Set to `production` for deployment

## Security Notes
- Add rate limiting for production (use Flask-Limiter)
- Implement file cleanup background task
- Add authentication if needed
- Consider using Redis for session management

## Troubleshooting
- If fonts don't render: Install `fonts-dejavu` package on server
- Large images timeout: Increase server timeout or add image compression
- Mobile upload issues: Check file size limits and browser compatibility

## Next Enhancements
- User accounts and saved preferences
- Batch processing queue
- Email PDF delivery
- OCR text extraction
- Cloud storage integration
