/**
 * Main Server File
 * Express server setup with all routes and middleware
 */

import express, { Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import 'express-async-errors';
import dotenv from 'dotenv';
import { PrismaClient } from '@prisma/client';
import { logger } from './common/logger';
import { errorHandler, requestLogger } from './common/middleware';
import { AuthService } from './auth/auth.service';
import { DriveService } from './drive/drive.service';
import { FileService } from './files/file.service';
import { SubmissionService } from './submissions/submission.service';
import { NotificationService } from './notifications/notification.service';

// Load environment variables
dotenv.config();

const app: Application = express();
const PORT = process.env.PORT || 3000;
const prisma = new PrismaClient();

// Initialize services
const authService = new AuthService(prisma);
const driveService = new DriveService(prisma);
const notificationService = new NotificationService(prisma);
const fileService = new FileService(prisma, driveService);
const submissionService = new SubmissionService(
  prisma,
  driveService,
  notificationService
);

// ============================================
// MIDDLEWARE
// ============================================

// Security middleware
app.use(helmet());

// CORS
app.use(
  cors({
    origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
    credentials: true,
  })
);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Compression
app.use(compression());

// Request logging
app.use(requestLogger);

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per window
  message: 'Too many requests from this IP, please try again later.',
});

app.use('/api', limiter);

// ============================================
// HEALTH CHECK
// ============================================

app.get('/health', async (req, res) => {
  try {
    // Test database connection
    await prisma.$queryRaw`SELECT 1`;

    // Test Drive API
    const driveHealthy = await driveService.testConnection();

    // Get Drive sync stats
    const syncStats = await driveService.getSyncStats();

    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      services: {
        database: 'up',
        driveApi: driveHealthy ? 'up' : 'down',
      },
      metrics: {
        uptime: process.uptime(),
        memoryUsage: process.memoryUsage(),
        driveSyncStats: syncStats,
      },
    });
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      error: (error as Error).message,
    });
  }
});

// ============================================
// API ROUTES
// ============================================

// Import route files would go here
// Example:
// import authRoutes from './auth/auth.routes';
// import submissionRoutes from './submissions/submission.routes';
// app.use('/api/auth', authRoutes);
// app.use('/api/submissions', submissionRoutes);

// Simple example routes
app.get('/api', (req, res) => {
  res.json({
    name: 'Referral Management System API',
    version: '1.0.0',
    documentation: '/api/docs',
  });
});

// ============================================
// ERROR HANDLING
// ============================================

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Global error handler
app.use(errorHandler);

// ============================================
// START SERVER
// ============================================

const server = app.listen(PORT, () => {
  logger.info(`🚀 Server running on port ${PORT}`);
  logger.info(`📝 Environment: ${process.env.NODE_ENV || 'development'}`);
  logger.info(`🔒 CORS origin: ${process.env.CORS_ORIGIN || 'http://localhost:5173'}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  server.close(async () => {
    await prisma.$disconnect();
    logger.info('HTTP server closed');
    process.exit(0);
  });
});

process.on('SIGINT', async () => {
  logger.info('SIGINT signal received: closing HTTP server');
  server.close(async () => {
    await prisma.$disconnect();
    logger.info('HTTP server closed');
    process.exit(0);
  });
});

export default app;
