# Quick Setup with SQLite (No PostgreSQL Required!)

This guide shows you how to set up the referral system using **SQLite** instead of PostgreSQL.

**Why SQLite?**
- ✅ No database server to install
- ✅ No configuration needed
- ✅ Just a single file on your computer
- ✅ Perfect for development and small teams
- ✅ Works immediately

---

## Prerequisites

Only need these (much simpler!):
- ✅ **Node.js 20+** - [Download here](https://nodejs.org/)
- ✅ **Google Cloud account** - For Drive integration

That's it! No PostgreSQL, no Redis needed for basic setup.

---

## Step 1: Use SQLite Schema

**Replace the Prisma schema file:**

```cmd
cd C:\Claude\claude-code\referral-system
copy schema-sqlite.prisma schema.prisma
```

Or manually: Open `schema.prisma` and change line 9 from:
```prisma
provider = "postgresql"
```
to:
```prisma
provider = "sqlite"
```

---

## Step 2: Configure Environment Variables

**Create `.env` file in the backend folder:**

```cmd
cd backend
copy .env.example .env
notepad .env
```

**Edit the .env file with these settings:**

```env
# SQLite Database (just a file path!)
DATABASE_URL="file:./dev.db"

# JWT Secrets (generate random strings)
JWT_SECRET="your-super-secret-jwt-key-minimum-32-characters-change-this"
JWT_REFRESH_SECRET="your-refresh-secret-key-minimum-32-characters-change-this"

# Google Drive (get from Google Cloud Console)
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type":"service_account","project_id":"your-project",...}'
GOOGLE_DRIVE_ROOT_FOLDER_ID="your-drive-folder-id-here"

# File Upload
UPLOAD_DIR="./uploads"

# Email (use Gmail for simplicity)
EMAIL_PROVIDER="smtp"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_SECURE="false"
SMTP_USER="your-email@gmail.com"
SMTP_PASS="your-gmail-app-password"
EMAIL_FROM="your-email@gmail.com"

# Application
PORT=3000
NODE_ENV="development"
APP_URL="http://localhost:5173"
CORS_ORIGIN="http://localhost:5173"

# Optional - Skip these for basic setup
# REDIS_URL="redis://localhost:6379"
# ENABLE_VIRUS_SCANNING="false"
```

### Generate JWT Secrets (Strong Random Strings)

**Option 1 - Use Node.js:**
```cmd
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```
Copy the outputs to `JWT_SECRET` and `JWT_REFRESH_SECRET`

**Option 2 - Use online generator:**
Go to: https://generate-secret.vercel.app/32
Generate 2 secrets and paste them

---

## Step 3: Google Cloud Setup (Required for Drive Backup)

### 3.1 Create Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Click "New Project"
3. Name: `referral-system`
4. Click "Create"

### 3.2 Enable Google Drive API

1. Go to **APIs & Services** → **Library**
2. Search: **"Google Drive API"**
3. Click **Enable**

### 3.3 Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Name: `referral-drive-service`
4. Click **Create and Continue**
5. Role: **Service Account User**
6. Click **Done**

### 3.4 Download Service Account Key

1. Click on the service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON**
5. Click **Create**
6. **Save the downloaded JSON file** to: `C:\Claude\google-key.json`

⚠️ **IMPORTANT**: Keep this file safe! Don't share it or commit to Git!

### 3.5 Set Up Google Drive Folder

1. Open Google Drive: https://drive.google.com/
2. Create a folder called **"Referrals"**
3. Right-click → **Share**
4. Add the service account email (from JSON file: look for `"client_email"`)
5. Set permission to **Editor**
6. Uncheck "Notify people"
7. Click **Share**
8. **Copy the folder ID** from URL:
   - URL looks like: `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j`
   - Copy: `1a2b3c4d5e6f7g8h9i0j`

### 3.6 Add Credentials to .env

1. Open the JSON file you downloaded
2. Copy the **entire contents** (all the JSON)
3. In your `.env` file, paste it on one line:
   ```env
   GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type":"service_account","project_id":"..."}'
   ```
4. Add the folder ID:
   ```env
   GOOGLE_DRIVE_ROOT_FOLDER_ID="1a2b3c4d5e6f7g8h9i0j"
   ```

---

## Step 4: Gmail Setup (For Email Notifications)

### Option 1: Use Gmail (Easiest)

1. Go to: https://myaccount.google.com/security
2. Enable **2-Step Verification** (if not already on)
3. Go to: https://myaccount.google.com/apppasswords
4. Select **Mail** and your device
5. Click **Generate**
6. Copy the 16-character password
7. In `.env`:
   ```env
   SMTP_USER="your-email@gmail.com"
   SMTP_PASS="xxxx xxxx xxxx xxxx"  # paste the app password
   EMAIL_FROM="your-email@gmail.com"
   ```

### Option 2: Skip Email (For Testing)

Set in `.env`:
```env
ENABLE_EMAIL_NOTIFICATIONS="false"
```

---

## Step 5: Install Dependencies & Set Up Database

**In the backend folder:**

```cmd
cd C:\Claude\claude-code\referral-system\backend

# Install dependencies
npm install

# Generate Prisma client
npx prisma generate

# Create SQLite database and tables
npx prisma migrate dev --name init
```

You should see:
```
✔ Your database is now in sync with your schema.
```

**A file `dev.db` will be created** - this is your entire database!

---

## Step 6: Start the Backend

```cmd
npm run dev
```

You should see:
```
🚀 Server running on port 3000
📝 Environment: development
```

**Test it:**
Open browser: http://localhost:3000/health

You should see JSON with `"status": "healthy"`

---

## Step 7: Set Up Frontend

**Open a NEW terminal (keep backend running!):**

```cmd
cd C:\Claude\claude-code\referral-system\frontend

# Install dependencies
npm install

# Start frontend
npm run dev
```

You should see:
```
➜ Local: http://localhost:5173/
```

**Open browser:** http://localhost:5173

---

## Step 8: Create First Admin User

**Option 1: Use Prisma Studio (Visual Tool)**

In a new terminal:
```cmd
cd backend
npx prisma studio
```

This opens a web UI at http://localhost:5555

1. Click **User** table
2. Click **Add record**
3. Fill in:
   - **email**: `admin@example.com`
   - **name**: `Admin User`
   - **role**: `ADMIN`
   - **isActive**: `true`
   - **emailVerified**: `true`
   - **hashedPassword**: Leave blank for now (we'll set it via API)
4. Click **Save**

**Option 2: Use API (Temporarily enable registration)**

Create a file `backend/create-admin.js`:
```javascript
const bcrypt = require('bcrypt');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function createAdmin() {
  const hashedPassword = await bcrypt.hash('Admin123!@#', 12);

  const admin = await prisma.user.create({
    data: {
      email: 'admin@example.com',
      hashedPassword,
      name: 'Admin User',
      role: 'ADMIN',
      isActive: true,
      emailVerified: true
    }
  });

  console.log('Admin created:', admin.email);
  await prisma.$disconnect();
}

createAdmin();
```

Run it:
```cmd
node create-admin.js
```

**Login credentials:**
- Email: `admin@example.com`
- Password: `Admin123!@#`

---

## Step 9: Test the System

1. **Open frontend:** http://localhost:5173
2. **Login** with admin credentials
3. **Create a test submission:**
   - Click "New Submission"
   - Title: "Test Referral"
   - Description: "Testing the system"
   - Upload a test file (PDF or Word doc)
   - Submit
4. **Check Google Drive:**
   - Open your "Referrals" folder
   - You should see: `2025/October/REF-000001/`
   - The folder should contain your uploaded file!
5. **Check your email** for confirmation

✅ **If all this works, your system is fully operational!**

---

## Where is Everything Stored?

```
backend/
├── dev.db              ← Your entire database (SQLite file)
├── dev.db-journal      ← Temporary SQLite file
├── uploads/            ← Uploaded files (before Drive sync)
└── logs/               ← Application logs
```

**To backup your data:**
Just copy `dev.db` to a safe location!

---

## Troubleshooting

### "Cannot find module 'bcrypt'"
```cmd
cd backend
npm install bcrypt
```

### "Database connection error"
Check that `DATABASE_URL` in `.env` is:
```env
DATABASE_URL="file:./dev.db"
```

### "Google Drive sync failed"
1. Verify service account email is shared on Drive folder
2. Check folder ID is correct
3. Check JSON credentials are valid (no line breaks)

### "Email not sending"
1. Verify Gmail app password is correct (16 characters, no spaces)
2. Check 2FA is enabled on Google account
3. Or set `ENABLE_EMAIL_NOTIFICATIONS="false"` to skip emails

### Frontend won't start
```cmd
cd frontend
rm -rf node_modules
npm install
npm run dev
```

---

## Next Steps

Once everything works:

1. **Read RECOMMENDATIONS.md** for production improvements
2. **Customize email templates** in `notifications/notification.service.ts`
3. **Add more users** via Prisma Studio
4. **Set up automated backups** of `dev.db`

---

## Switching to PostgreSQL Later

When you're ready for production:

1. Install PostgreSQL
2. Replace `schema.prisma` with original version
3. Update `DATABASE_URL` to PostgreSQL connection string
4. Run `npx prisma migrate dev`

All your data structure will remain the same!

---

## Summary

✅ **With SQLite you avoid:**
- Complex PostgreSQL installation
- Database server configuration
- User/password management
- Connection issues

✅ **You get:**
- Simple file-based database
- Instant setup
- Full functionality
- Easy backups

**Perfect for development, testing, and small teams!**

For questions, see `SETUP_GUIDE.md` or `README.md`.
