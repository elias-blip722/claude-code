# Two-Way Referral Management System

A comprehensive, secure referral management platform with automatic Google Drive integration, enabling stakeholders to submit referrals while providing administrators with full oversight and automated backup capabilities.

## 🌟 Key Features

### Core Functionality
- **Two-Way Communication**: Stakeholders submit referrals, admins review and respond
- **RAG Status System**: Visual traffic-light status (RED → AMBER → GREEN)
- **Role-Based Access Control**: Separate permissions for admins and stakeholders
- **Real-Time Notifications**: Email and in-app notifications for all events
- **Comprehensive Dashboard**: Live statistics, charts, and activity feeds

### Google Drive Integration (★ Unique Feature)
- **Automatic Backup**: Every uploaded file automatically synced to Google Drive
- **Organized Structure**: `/Referrals/{Year}/{Month}/REF-{ID}/` hierarchy
- **Admin-Only Access**: Drive folders restricted to administrators only
- **Sync Monitoring**: Real-time sync status with retry capability
- **Metadata Files**: Automatic generation of submission metadata
- **Direct Access**: One-click Drive folder opening from dashboard

### Security
- **Multi-Layer Authentication**: Email/password + OAuth (Google/Microsoft)
- **JWT Tokens**: Secure session management with refresh tokens
- **Account Protection**: Login attempt limiting, account lockout
- **Virus Scanning**: ClamAV integration for all uploads
- **File Validation**: MIME type checking, size limits, path traversal prevention
- **Encryption**: HTTPS, database encryption, secure file storage

### File Management
- **Supported Formats**: Office documents (.docx, .pptx, .xlsx), PDF, images
- **Size Limits**: 50MB per file, 200MB per submission
- **Upload Validation**: Real-time virus scanning before Drive sync
- **Retry Logic**: Automatic retry with exponential backoff
- **Dual Storage**: Primary storage (S3) + Google Drive backup

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │  React + TypeScript + Material-UI
│   (Port 5173)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend API   │  Node.js + Express + Prisma
│   (Port 3000)   │
└────────┬────────┘
         │
         ├──────────► PostgreSQL (Primary Database)
         ├──────────► Redis (Cache + Queue)
         ├──────────► AWS S3 (File Storage)
         └──────────► Google Drive API (Backup)
```

## 📋 Prerequisites

- **Node.js**: 20.x or higher
- **PostgreSQL**: 14.x or higher
- **Redis**: 6.x or higher (optional but recommended)
- **ClamAV**: For virus scanning (optional in development)
- **Google Cloud Account**: For Drive API access

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd referral-system
```

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Drive API**
4. Create a **Service Account**:
   - Go to **IAM & Admin** → **Service Accounts**
   - Click **Create Service Account**
   - Name: `referral-system-drive`
   - Grant role: **Service Account User**
   - Click **Done**
5. Generate JSON key:
   - Click on the service account
   - Go to **Keys** tab
   - Click **Add Key** → **Create new key**
   - Select **JSON** format
   - Download the key file (keep it secure!)
6. Create Drive folder:
   - Open Google Drive
   - Create a folder called **Referrals**
   - Right-click → **Share**
   - Add service account email (from JSON key)
   - Give **Editor** permissions
   - Copy the folder ID from URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`

### 3. Backend Setup

```bash
cd backend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Configure `.env`**:

```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/referral_db"

# JWT Secrets
JWT_SECRET="your-super-secret-key-change-this"
JWT_REFRESH_SECRET="your-refresh-secret-key-change-this"

# Google Drive
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type":"service_account","project_id":"your-project",...}'
GOOGLE_DRIVE_ROOT_FOLDER_ID="your-drive-folder-id"

# File Upload
UPLOAD_DIR="./uploads"
MAX_FILE_SIZE=52428800  # 50MB in bytes

# Email (SendGrid example)
EMAIL_PROVIDER="sendgrid"
SENDGRID_API_KEY="your-sendgrid-api-key"
EMAIL_FROM="noreply@yourdomain.com"

# Application
PORT=3000
NODE_ENV="development"
APP_URL="http://localhost:5173"
CORS_ORIGIN="http://localhost:5173"

# Redis (optional)
REDIS_URL="redis://localhost:6379"
```

**Setup Database**:

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# (Optional) Seed database
npm run prisma:seed
```

**Start Backend**:

```bash
# Development mode (with hot reload)
npm run dev

# Production mode
npm run build
npm start
```

### 4. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env
nano .env
```

**Configure `.env`**:

```env
VITE_API_URL=http://localhost:3000/api
VITE_APP_NAME="Referral Management System"
```

**Start Frontend**:

```bash
# Development mode
npm run dev

# Production build
npm run build
npm run preview
```

### 5. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:3000
- **Health Check**: http://localhost:3000/health

**Default Admin Account** (if seeded):
- Email: `admin@example.com`
- Password: `Admin123!@#`

## 📁 Project Structure

```
referral-system/
├── backend/
│   ├── src/
│   │   ├── auth/              # Authentication service
│   │   ├── submissions/       # Submission management
│   │   ├── files/             # File upload & virus scanning
│   │   ├── drive/             # Google Drive integration ★
│   │   ├── notifications/     # Email & in-app notifications
│   │   ├── common/            # Shared utilities, middleware
│   │   └── server.ts          # Main server file
│   ├── uploads/               # Uploaded files (gitignored)
│   ├── logs/                  # Application logs
│   ├── prisma/                # Database schema
│   └── package.json
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable React components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API clients
│   │   ├── hooks/             # Custom React hooks
│   │   ├── types/             # TypeScript types
│   │   └── utils/             # Helper functions
│   └── package.json
│
├── schema.prisma              # Database schema
├── RECOMMENDATIONS.md         # Technical recommendations ★
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables

#### Backend

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ |
| `JWT_SECRET` | Secret for access tokens | - | ✅ |
| `JWT_REFRESH_SECRET` | Secret for refresh tokens | - | ✅ |
| `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` | JSON key from Google Cloud | - | ✅ |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | Drive folder ID for uploads | - | ✅ |
| `SENDGRID_API_KEY` | SendGrid API key for emails | - | ✅ |
| `PORT` | Server port | 3000 | ❌ |
| `NODE_ENV` | Environment | development | ❌ |
| `UPLOAD_DIR` | File upload directory | ./uploads | ❌ |
| `REDIS_URL` | Redis connection string | - | ❌ |

#### Frontend

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VITE_API_URL` | Backend API URL | - | ✅ |
| `VITE_APP_NAME` | Application name | Referral System | ❌ |

### Google Drive Permissions

The service account must have **Editor** access to the root Referrals folder. Permissions are automatically inherited by subfolders.

**Recommended Setup**:
1. Create a Google Shared Drive (Team Drive) for better management
2. Add service account to Shared Drive with **Content Manager** role
3. Set folder retention policies in Shared Drive settings
4. Enable version history for all files

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with UI
npm run test:ui

# Coverage
npm run test:coverage
```

## 📊 Database Schema

The system uses PostgreSQL with Prisma ORM. Key tables:

- **users**: User accounts with RBAC
- **submissions**: Referral submissions with RAG status
- **files**: Uploaded files with Drive sync status ★
- **drive_sync_logs**: Complete Drive operation history ★
- **comments**: Communication between users and admins
- **status_history**: Audit trail of status changes
- **notifications**: In-app notifications
- **email_queue**: Asynchronous email delivery

See `schema.prisma` for complete schema definition.

## 🔐 Security Features

### Authentication
- **JWT Tokens**: Short-lived access tokens (15 min), long-lived refresh tokens (7 days)
- **Password Requirements**: Min 12 chars, uppercase, lowercase, numbers, symbols
- **Account Lockout**: 5 failed attempts = 15 minute lock
- **Session Management**: Device fingerprinting, IP tracking

### File Upload Security
1. **MIME Type Validation**: Only allowed file types
2. **Size Validation**: Individual + total size limits
3. **Filename Sanitization**: Prevent path traversal attacks
4. **Virus Scanning**: ClamAV integration before Drive sync
5. **Async Processing**: Non-blocking upload workflow

### API Security
- **Rate Limiting**: 100 requests per 15 minutes per IP
- **CORS**: Restricted to configured origin
- **Helmet.js**: Security headers
- **Input Validation**: Zod schema validation
- **SQL Injection Prevention**: Prisma ORM with parameterized queries

## 📈 Monitoring & Logging

### Health Checks

```bash
curl http://localhost:3000/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-28T12:00:00.000Z",
  "services": {
    "database": "up",
    "driveApi": "up"
  },
  "metrics": {
    "uptime": 86400,
    "memoryUsage": {...},
    "driveSyncStats": {
      "totalFiles": 1000,
      "syncedFiles": 995,
      "failedFiles": 3,
      "syncSuccessRate": 99.5
    }
  }
}
```

### Logging

Logs are stored in `backend/logs/`:
- `combined.log`: All logs
- `error.log`: Error-level logs only

**Log Levels**: ERROR, WARN, INFO, DEBUG

### Monitoring Dashboard

The admin dashboard shows:
- Total submissions by status
- Drive sync success rate
- Average processing time
- Recent activity feed
- Failed syncs requiring attention

## 🚢 Deployment

### Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Deployment

**Backend**:
```bash
cd backend
npm run build
NODE_ENV=production npm start
```

**Frontend**:
```bash
cd frontend
npm run build
# Serve dist/ folder with Nginx or similar
```

### Environment Checklist

Before deploying to production:
- [ ] Change all default secrets
- [ ] Use production database
- [ ] Configure proper CORS origin
- [ ] Set up SSL/TLS certificates
- [ ] Enable production logging
- [ ] Configure email service (SendGrid/SES)
- [ ] Set up backup strategy
- [ ] Configure monitoring (Sentry, DataDog)
- [ ] Review Google Drive quotas
- [ ] Test disaster recovery

## 🐛 Troubleshooting

### Common Issues

**1. Google Drive Sync Failing**

```bash
# Check service account permissions
# Verify folder ID is correct
# Test connection:
curl http://localhost:3000/api/drive/test-connection
```

**2. Database Connection Errors**

```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection string
npm run prisma:studio
```

**3. Email Not Sending**

```bash
# Check email queue
SELECT * FROM email_queue WHERE status = 'FAILED';

# Process queue manually
npm run process:email-queue
```

**4. Virus Scanner Not Working**

```bash
# Install ClamAV (Ubuntu/Debian)
sudo apt-get install clamav clamav-daemon

# Update virus definitions
sudo freshclam

# Test scanner
clamscan --version
```

## 📖 API Documentation

### Authentication

**POST** `/api/auth/register`
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe"
}
```

**POST** `/api/auth/login`
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

### Submissions

**POST** `/api/submissions`
```json
{
  "title": "Referral Title",
  "description": "Detailed description...",
  "priority": "HIGH"
}
```

**GET** `/api/submissions` - List all submissions

**GET** `/api/submissions/:id` - Get submission details

**PATCH** `/api/submissions/:id/status` - Change status
```json
{
  "newStatus": "AMBER",
  "reason": "Under review by team"
}
```

### Files

**POST** `/api/submissions/:id/files` - Upload file (multipart/form-data)

**GET** `/api/files/:id/download` - Download file

**POST** `/api/files/:id/retry-sync` - Retry Drive sync (admin only)

### Dashboard

**GET** `/api/dashboard/stats` - Get dashboard statistics

**GET** `/api/dashboard/drive-sync-status` - Get Drive sync details

For complete API documentation, see `/api/docs` (Swagger) when server is running.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **Google Drive API**: For seamless cloud storage integration
- **Prisma**: For excellent TypeScript ORM
- **Material-UI**: For beautiful React components
- **ClamAV**: For open-source virus scanning

## 📞 Support

For issues, questions, or feature requests:
- **GitHub Issues**: [Create an issue](https://github.com/your-repo/issues)
- **Email**: support@yourdomain.com
- **Documentation**: See `RECOMMENDATIONS.md` for technical deep-dive

---

**Built with ❤️ for efficient referral management**

**⭐ Star this repo if you find it useful!**
