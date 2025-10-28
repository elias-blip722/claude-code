# Complete Setup Guide

This guide walks you through setting up the Referral Management System from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Local Development Setup](#local-development-setup)
4. [Production Deployment](#production-deployment)
5. [Post-Deployment Tasks](#post-deployment-tasks)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

Install the following on your machine:

1. **Node.js 20.x or higher**
   ```bash
   # Check version
   node --version

   # Install using nvm (recommended)
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install 20
   nvm use 20
   ```

2. **PostgreSQL 14.x or higher**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib

   # macOS
   brew install postgresql@14

   # Start service
   sudo systemctl start postgresql  # Linux
   brew services start postgresql@14  # macOS
   ```

3. **Redis** (optional but recommended)
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server

   # macOS
   brew install redis

   # Start service
   sudo systemctl start redis  # Linux
   brew services start redis  # macOS
   ```

4. **Git**
   ```bash
   git --version
   # If not installed: sudo apt install git (Linux) or brew install git (macOS)
   ```

5. **ClamAV** (optional, for virus scanning)
   ```bash
   # Ubuntu/Debian
   sudo apt install clamav clamav-daemon
   sudo systemctl start clamav-daemon
   sudo freshclam  # Update virus definitions

   # macOS
   brew install clamav
   ```

---

## Google Cloud Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Project name: `referral-management-system`
4. Click **Create**

### Step 2: Enable Google Drive API

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Google Drive API"
3. Click on **Google Drive API**
4. Click **Enable**

### Step 3: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Fill in details:
   - **Service account name**: `referral-drive-service`
   - **Service account ID**: (auto-generated)
   - **Description**: "Service account for Referral System Drive integration"
4. Click **Create and Continue**
5. **Grant this service account access to project**:
   - Role: **Service Account User**
   - Click **Continue**
6. Click **Done**

### Step 4: Generate Service Account Key

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** format
5. Click **Create**
6. **Important**: Save this JSON file securely! You'll need it later
7. ⚠️ **Never commit this file to Git!**

### Step 5: Create Google Drive Folder

1. Open [Google Drive](https://drive.google.com/)
2. Click **New** → **Folder**
3. Name it: **Referrals**
4. Right-click on the folder → **Share**
5. Click **Share** button
6. Add the service account email (from the JSON key file):
   - Example: `referral-drive-service@project-name.iam.gserviceaccount.com`
7. Set permission to **Editor**
8. Uncheck "Notify people"
9. Click **Share**
10. **Copy the Folder ID**:
    - Open the folder
    - Look at the URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`
    - Copy everything after `/folders/`

### Step 6: (Optional) Set Up Shared Drive

For better organization and retention policies:

1. Create a **Shared Drive** (requires Google Workspace)
2. Name it: **Referral System**
3. Add service account as **Content Manager**
4. Create **Referrals** folder inside Shared Drive
5. Use Shared Drive folder ID in configuration

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd referral-system
```

### Step 2: Database Setup

```bash
# Create database
sudo -u postgres psql

CREATE DATABASE referral_system;
CREATE USER referral_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE referral_system TO referral_user;
\\q
```

### Step 3: Backend Setup

```bash
cd backend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Configure .env**:

1. **Database**:
   ```env
   DATABASE_URL="postgresql://referral_user:your_password@localhost:5432/referral_system"
   ```

2. **JWT Secrets** (generate strong random strings):
   ```bash
   # Generate secrets (run these commands)
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   ```

   Copy output to:
   ```env
   JWT_SECRET="<first-output>"
   JWT_REFRESH_SECRET="<second-output>"
   ```

3. **Google Drive**:
   - Open your downloaded service account JSON file
   - Copy the entire content
   - Paste it as a single line (escape quotes if needed):
   ```env
   GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type":"service_account",...}'
   GOOGLE_DRIVE_ROOT_FOLDER_ID="your-folder-id"
   ```

4. **Email** (choose one):

   **Option A: SendGrid** (easiest)
   - Sign up at [SendGrid](https://sendgrid.com/)
   - Create API key
   ```env
   EMAIL_PROVIDER="sendgrid"
   SENDGRID_API_KEY="SG.xxxxx"
   EMAIL_FROM="noreply@yourdomain.com"
   ```

   **Option B: Gmail SMTP**
   - Enable 2FA on Gmail
   - Generate App Password
   ```env
   EMAIL_PROVIDER="smtp"
   SMTP_HOST="smtp.gmail.com"
   SMTP_PORT="587"
   SMTP_SECURE="false"
   SMTP_USER="your-email@gmail.com"
   SMTP_PASS="your-app-password"
   EMAIL_FROM="your-email@gmail.com"
   ```

**Initialize Database**:

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# (Optional) Open Prisma Studio to view database
npm run prisma:studio
```

**Start Backend**:

```bash
# Development mode (with hot reload)
npm run dev

# You should see:
# 🚀 Server running on port 3000
# 📝 Environment: development
```

**Test Backend**:

```bash
# In another terminal
curl http://localhost:3000/health

# Should return:
# {"status":"healthy","timestamp":"...","services":{...}}
```

### Step 4: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env
nano .env
```

**Configure .env**:

```env
VITE_API_URL=http://localhost:3000/api
VITE_APP_NAME="Referral Management System"
```

**Start Frontend**:

```bash
npm run dev

# You should see:
# ➜  Local:   http://localhost:5173/
```

### Step 5: Create First Admin User

```bash
# In backend directory
cd backend

# Option 1: Using Prisma Studio
npm run prisma:studio
# Navigate to Users table
# Click "Add record"
# Fill in:
#   email: admin@example.com
#   hashedPassword: (use bcrypt to hash "Admin123!@#")
#   name: Admin User
#   role: ADMIN
#   isActive: true

# Option 2: Create seed script
npm run prisma:seed
```

Or create a registration endpoint (temporarily enable it):

```bash
curl -X POST http://localhost:3000/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!@#",
    "name": "Admin User",
    "role": "ADMIN"
  }'
```

### Step 6: Test the System

1. **Open Frontend**: http://localhost:5173
2. **Login** with admin credentials
3. **Create a Test Submission**:
   - Click "New Submission"
   - Fill in title and description
   - Upload a test file
   - Submit
4. **Check Google Drive**:
   - Open your Referrals folder
   - You should see: `2025/October/REF-000001/`
   - Folder should contain uploaded file + metadata.txt
5. **Check Email**:
   - Verify confirmation email was sent
6. **Test Dashboard**:
   - View submission statistics
   - Check Drive sync status (should be green)

---

## Production Deployment

### Option 1: Docker Deployment

**Prerequisites**:
- Docker installed
- Docker Compose installed

```bash
# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit both .env files with production values

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:3000/health
```

**Access**:
- Frontend: http://localhost:5173
- Backend: http://localhost:3000
- Database: localhost:5432

### Option 2: AWS/Cloud Deployment

**AWS Setup**:

1. **Database**: AWS RDS PostgreSQL
   - Create RDS instance
   - Copy connection string to `DATABASE_URL`

2. **File Storage**: AWS S3
   - Create S3 bucket
   - Configure IAM user with S3 permissions
   - Update file service to use S3

3. **Backend**: AWS ECS or EC2
   ```bash
   # Build
   cd backend
   npm run build

   # Start
   NODE_ENV=production npm start
   ```

4. **Frontend**: AWS S3 + CloudFront
   ```bash
   cd frontend
   npm run build

   # Upload dist/ folder to S3
   aws s3 sync dist/ s3://your-bucket-name
   ```

5. **Email**: AWS SES
   - Verify domain
   - Create SMTP credentials
   - Update email configuration

**Environment Variables**:

```env
# Production .env
NODE_ENV=production
DATABASE_URL=<RDS connection string>
AWS_S3_BUCKET=<bucket name>
APP_URL=https://yourdomain.com
CORS_ORIGIN=https://yourdomain.com
```

### Option 3: DigitalOcean/Heroku

Similar to AWS but using platform-specific services.

---

## Post-Deployment Tasks

### 1. Security Checklist

- [ ] All default passwords changed
- [ ] JWT secrets are strong random strings
- [ ] CORS configured for production domain only
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Database backups configured
- [ ] Service account JSON key stored securely (not in code)
- [ ] Rate limiting enabled
- [ ] Virus scanning operational
- [ ] Security headers configured (Helmet.js)

### 2. Monitoring Setup

- [ ] Configure error tracking (Sentry)
- [ ] Set up uptime monitoring
- [ ] Configure log aggregation
- [ ] Set up alerts for:
  - Drive sync failures
  - High error rates
  - Database issues
  - Disk space warnings

### 3. Backup Strategy

```bash
# Database backup (daily cron job)
pg_dump referral_system > backup-$(date +%Y%m%d).sql

# Backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump referral_system | gzip > $BACKUP_DIR/db_$DATE.sql.gz
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete  # Keep 30 days
```

### 4. User Training

- Create admin user accounts
- Conduct training sessions
- Provide user documentation
- Set up support channel

### 5. Performance Tuning

```sql
-- Add database indexes (if not auto-created)
CREATE INDEX idx_submissions_status ON submissions(status);
CREATE INDEX idx_submissions_user_id ON submissions(user_id);
CREATE INDEX idx_files_drive_sync_status ON files(drive_sync_status);
```

---

## Troubleshooting

### Issue: Google Drive Sync Failing

**Error**: "Failed to create Drive folder"

**Solutions**:

1. **Check service account permissions**:
   ```bash
   # Verify service account has access to folder
   # Go to Drive folder → Right-click → Share
   # Confirm service account email is listed with Editor access
   ```

2. **Test Drive API connection**:
   ```bash
   curl http://localhost:3000/api/drive/test-connection
   ```

3. **Check API quotas**:
   - Go to Google Cloud Console
   - APIs & Services → Dashboard
   - Check Drive API usage
   - Request quota increase if needed

4. **Verify credentials**:
   ```bash
   # Check .env file
   echo $GOOGLE_SERVICE_ACCOUNT_CREDENTIALS | python -m json.tool
   # Should output valid JSON
   ```

### Issue: Database Connection Failed

**Error**: "Can't connect to database"

**Solutions**:

```bash
# 1. Check PostgreSQL is running
sudo systemctl status postgresql
# or
pg_isready -h localhost -p 5432

# 2. Test connection manually
psql -h localhost -U referral_user -d referral_system

# 3. Check connection string format
# Should be: postgresql://user:password@host:port/database

# 4. Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Issue: Emails Not Sending

**Error**: "Email delivery failed"

**Solutions**:

1. **Check email queue**:
   ```sql
   SELECT * FROM email_queue WHERE status = 'FAILED';
   ```

2. **Test SMTP connection**:
   ```bash
   telnet smtp.gmail.com 587
   ```

3. **Verify SendGrid API key**:
   ```bash
   curl -X POST https://api.sendgrid.com/v3/mail/send \\
     -H "Authorization: Bearer $SENDGRID_API_KEY" \\
     -H "Content-Type: application/json" \\
     -d '{"personalizations":[{"to":[{"email":"test@example.com"}]}],"from":{"email":"noreply@yourdomain.com"},"subject":"Test","content":[{"type":"text/plain","value":"Test"}]}'
   ```

### Issue: File Upload Failing

**Error**: "File upload validation failed"

**Solutions**:

1. **Check file size limits**:
   - Individual: 50MB
   - Total per submission: 200MB

2. **Verify MIME type**:
   - Only allowed types can be uploaded
   - Check `ALLOWED_MIMETYPES` in FileService

3. **Check disk space**:
   ```bash
   df -h
   # Ensure sufficient space in upload directory
   ```

4. **Check permissions**:
   ```bash
   ls -la backend/uploads/
   # Should be writable by Node process
   chmod 755 backend/uploads/
   ```

### Issue: Virus Scanner Not Working

**Error**: "ClamAV not found"

**Solutions**:

```bash
# 1. Install ClamAV
sudo apt install clamav clamav-daemon  # Ubuntu
brew install clamav  # macOS

# 2. Update virus definitions
sudo freshclam

# 3. Start daemon
sudo systemctl start clamav-daemon

# 4. Test scanner
clamscan --version
clamscan /path/to/test/file

# 5. For development: Disable scanning
# In .env:
ENABLE_VIRUS_SCANNING=false
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**:
   ```bash
   tail -f backend/logs/error.log
   ```

2. **Check health endpoint**:
   ```bash
   curl http://localhost:3000/health | python -m json.tool
   ```

3. **Enable debug logging**:
   ```env
   LOG_LEVEL=debug
   ```

4. **Review RECOMMENDATIONS.md** for best practices

5. **Create GitHub issue** with:
   - Error message
   - Steps to reproduce
   - Log excerpts
   - Environment details

---

## Next Steps

After successful setup:

1. Read **RECOMMENDATIONS.md** for optimization tips
2. Review **README.md** for API documentation
3. Customize email templates in `notifications/notification.service.ts`
4. Set up monitoring dashboards
5. Create user documentation
6. Plan regular maintenance windows

---

**Congratulations!** Your Referral Management System is now set up and running. 🎉
