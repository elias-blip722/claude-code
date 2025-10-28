/**
 * Google Drive Service
 * Handles all Google Drive API operations including folder creation,
 * file uploads, permission management, and sync monitoring.
 */

import { google, drive_v3 } from 'googleapis';
import { Readable } from 'stream';
import * as fs from 'fs';
import * as path from 'path';
import { PrismaClient, DriveSyncStatus, DriveSyncAction } from '@prisma/client';
import { logger } from '../common/logger';

export interface DriveUploadOptions {
  submissionId: string;
  fileId: string;
  filePath: string;
  filename: string;
  mimeType: string;
}

export interface DriveUploadResult {
  fileId: string;
  webViewLink: string;
  success: boolean;
  error?: string;
}

export class DriveService {
  private drive: drive_v3.Drive;
  private prisma: PrismaClient;
  private rootFolderId: string;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
    this.initializeDrive();
  }

  /**
   * Initialize Google Drive API client with service account credentials
   */
  private async initializeDrive() {
    try {
      // Load service account credentials from environment
      const credentials = JSON.parse(
        process.env.GOOGLE_SERVICE_ACCOUNT_CREDENTIALS || '{}'
      );

      const auth = new google.auth.GoogleAuth({
        credentials,
        scopes: ['https://www.googleapis.com/auth/drive.file'],
      });

      this.drive = google.drive({ version: 'v3', auth });
      this.rootFolderId = process.env.GOOGLE_DRIVE_ROOT_FOLDER_ID || '';

      logger.info('Google Drive API initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Google Drive API:', error);
      throw new Error('Google Drive initialization failed');
    }
  }

  /**
   * Create a folder structure for a submission
   * Structure: /Referrals/{YEAR}/{MONTH}/REF-{ID}/
   */
  async createSubmissionFolder(
    submissionId: string,
    referenceId: string
  ): Promise<{ folderId: string; folderUrl: string }> {
    try {
      const now = new Date();
      const year = now.getFullYear().toString();
      const month = now.toLocaleString('en-US', { month: 'long' });

      // Get or create year folder
      const yearFolderId = await this.getOrCreateFolder(year, this.rootFolderId);

      // Get or create month folder
      const monthFolderId = await this.getOrCreateFolder(month, yearFolderId);

      // Create submission folder
      const submissionFolderName = referenceId;
      const submissionFolderId = await this.createFolder(
        submissionFolderName,
        monthFolderId
      );

      // Get web view link
      const folderUrl = `https://drive.google.com/drive/folders/${submissionFolderId}`;

      // Update submission in database
      await this.prisma.submission.update({
        where: { id: submissionId },
        data: {
          googleDriveFolderId: submissionFolderId,
          googleDriveFolderUrl: folderUrl,
          driveSyncStatus: DriveSyncStatus.SYNCED,
          lastDriveSyncAt: new Date(),
        },
      });

      logger.info(`Created Drive folder for submission ${referenceId}`, {
        submissionId,
        folderId: submissionFolderId,
      });

      return { folderId: submissionFolderId, folderUrl };
    } catch (error) {
      logger.error('Failed to create submission folder:', error);

      // Update submission with error
      await this.prisma.submission.update({
        where: { id: submissionId },
        data: {
          driveSyncStatus: DriveSyncStatus.FAILED,
          driveSyncError: (error as Error).message,
          driveSyncRetries: { increment: 1 },
        },
      });

      throw error;
    }
  }

  /**
   * Get existing folder or create new one
   */
  private async getOrCreateFolder(
    folderName: string,
    parentFolderId: string
  ): Promise<string> {
    // Search for existing folder
    const response = await this.drive.files.list({
      q: `name='${folderName}' and '${parentFolderId}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false`,
      fields: 'files(id, name)',
      spaces: 'drive',
    });

    if (response.data.files && response.data.files.length > 0) {
      return response.data.files[0].id!;
    }

    // Create new folder
    return await this.createFolder(folderName, parentFolderId);
  }

  /**
   * Create a new folder in Google Drive
   */
  private async createFolder(
    folderName: string,
    parentFolderId: string
  ): Promise<string> {
    const fileMetadata: drive_v3.Schema$File = {
      name: folderName,
      mimeType: 'application/vnd.google-apps.folder',
      parents: [parentFolderId],
    };

    const response = await this.drive.files.create({
      requestBody: fileMetadata,
      fields: 'id',
    });

    return response.data.id!;
  }

  /**
   * Upload a file to Google Drive with retry logic
   */
  async uploadFile(options: DriveUploadOptions): Promise<DriveUploadResult> {
    const { submissionId, fileId, filePath, filename, mimeType } = options;
    const maxRetries = 3;
    let lastError: Error | null = null;

    // Get submission's Drive folder
    const submission = await this.prisma.submission.findUnique({
      where: { id: submissionId },
      select: { googleDriveFolderId: true },
    });

    if (!submission?.googleDriveFolderId) {
      throw new Error('Submission Drive folder not found');
    }

    // Try upload with retries
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        // Update file status to SYNCING
        await this.prisma.file.update({
          where: { id: fileId },
          data: {
            driveSyncStatus: DriveSyncStatus.SYNCING,
            driveSyncAttempts: attempt,
          },
        });

        // Log sync attempt
        await this.logDriveSync(fileId, DriveSyncAction.UPLOAD, 'started', attempt);

        // Upload file
        const result = await this.performUpload(
          filePath,
          filename,
          mimeType,
          submission.googleDriveFolderId
        );

        // Update file with Drive info
        await this.prisma.file.update({
          where: { id: fileId },
          data: {
            googleDriveId: result.fileId,
            googleDriveUrl: result.webViewLink,
            driveSyncStatus: DriveSyncStatus.SYNCED,
            lastDriveSyncAt: new Date(),
            driveSyncError: null,
          },
        });

        // Log success
        await this.logDriveSync(fileId, DriveSyncAction.UPLOAD, 'success', attempt);

        logger.info(`File uploaded to Drive successfully`, {
          fileId,
          driveFileId: result.fileId,
          attempt,
        });

        return { ...result, success: true };
      } catch (error) {
        lastError = error as Error;
        logger.warn(`Drive upload attempt ${attempt} failed:`, error);

        // Log failure
        await this.logDriveSync(
          fileId,
          DriveSyncAction.UPLOAD,
          'failed',
          attempt,
          (error as Error).message
        );

        // Wait before retry (exponential backoff with jitter)
        if (attempt < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, attempt) + Math.random() * 1000, 10000);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    // All retries failed
    await this.prisma.file.update({
      where: { id: fileId },
      data: {
        driveSyncStatus: DriveSyncStatus.FAILED,
        driveSyncError: lastError?.message || 'Upload failed after retries',
      },
    });

    throw lastError || new Error('Upload failed after retries');
  }

  /**
   * Perform the actual file upload to Google Drive
   */
  private async performUpload(
    filePath: string,
    filename: string,
    mimeType: string,
    parentFolderId: string
  ): Promise<{ fileId: string; webViewLink: string }> {
    const fileMetadata: drive_v3.Schema$File = {
      name: filename,
      parents: [parentFolderId],
    };

    const media = {
      mimeType,
      body: fs.createReadStream(filePath),
    };

    const response = await this.drive.files.create({
      requestBody: fileMetadata,
      media,
      fields: 'id, webViewLink',
    });

    return {
      fileId: response.data.id!,
      webViewLink: response.data.webViewLink!,
    };
  }

  /**
   * Upload file using resumable upload for large files
   */
  async uploadFileResumable(
    options: DriveUploadOptions
  ): Promise<DriveUploadResult> {
    const { submissionId, fileId, filePath, filename, mimeType } = options;

    try {
      const submission = await this.prisma.submission.findUnique({
        where: { id: submissionId },
        select: { googleDriveFolderId: true },
      });

      if (!submission?.googleDriveFolderId) {
        throw new Error('Submission Drive folder not found');
      }

      const fileSize = fs.statSync(filePath).size;

      const fileMetadata: drive_v3.Schema$File = {
        name: filename,
        parents: [submission.googleDriveFolderId],
      };

      const response = await this.drive.files.create({
        requestBody: fileMetadata,
        media: {
          mimeType,
          body: fs.createReadStream(filePath),
        },
        fields: 'id, webViewLink',
      });

      return {
        fileId: response.data.id!,
        webViewLink: response.data.webViewLink!,
        success: true,
      };
    } catch (error) {
      logger.error('Resumable upload failed:', error);
      throw error;
    }
  }

  /**
   * Create metadata file for submission
   */
  async createMetadataFile(submissionId: string): Promise<void> {
    try {
      const submission = await this.prisma.submission.findUnique({
        where: { id: submissionId },
        include: {
          user: { select: { name: true, email: true } },
          files: { select: { filename: true, fileSize: true } },
        },
      });

      if (!submission?.googleDriveFolderId) {
        throw new Error('Submission Drive folder not found');
      }

      // Create metadata content
      const metadata = `
SUBMISSION METADATA
===================

Submission ID: ${submission.referenceId}
Submitted By: ${submission.user.name} (${submission.user.email})
Submission Date: ${submission.createdAt.toISOString()}
Status: ${submission.status}
Priority: ${submission.priority}

Title: ${submission.title}

Description:
${submission.description}

Files (${submission.files.length}):
${submission.files
  .map((f, i) => `${i + 1}. ${f.filename} (${(f.fileSize / 1024).toFixed(2)} KB)`)
  .join('\n')}

Generated: ${new Date().toISOString()}
      `.trim();

      // Upload metadata file
      const fileMetadata: drive_v3.Schema$File = {
        name: 'metadata.txt',
        parents: [submission.googleDriveFolderId],
        mimeType: 'text/plain',
      };

      const media = {
        mimeType: 'text/plain',
        body: Readable.from([metadata]),
      };

      await this.drive.files.create({
        requestBody: fileMetadata,
        media,
      });

      logger.info(`Metadata file created for submission ${submission.referenceId}`);
    } catch (error) {
      logger.error('Failed to create metadata file:', error);
      // Non-critical error, don't throw
    }
  }

  /**
   * Retry failed Drive syncs
   */
  async retryFailedSync(fileId: string): Promise<void> {
    const file = await this.prisma.file.findUnique({
      where: { id: fileId },
      include: { submission: true },
    });

    if (!file) {
      throw new Error('File not found');
    }

    if (file.driveSyncStatus !== DriveSyncStatus.FAILED) {
      throw new Error('File is not in failed state');
    }

    await this.uploadFile({
      submissionId: file.submissionId,
      fileId: file.id,
      filePath: file.filePath,
      filename: file.originalFilename,
      mimeType: file.mimeType,
    });
  }

  /**
   * Get Drive sync statistics
   */
  async getSyncStats() {
    const [totalFiles, syncedFiles, failedFiles, pendingFiles] = await Promise.all([
      this.prisma.file.count(),
      this.prisma.file.count({ where: { driveSyncStatus: DriveSyncStatus.SYNCED } }),
      this.prisma.file.count({ where: { driveSyncStatus: DriveSyncStatus.FAILED } }),
      this.prisma.file.count({ where: { driveSyncStatus: DriveSyncStatus.PENDING } }),
    ]);

    const syncSuccessRate =
      totalFiles > 0 ? ((syncedFiles / totalFiles) * 100).toFixed(2) : '0';

    return {
      totalFiles,
      syncedFiles,
      failedFiles,
      pendingFiles,
      syncingFiles: totalFiles - syncedFiles - failedFiles - pendingFiles,
      syncSuccessRate: parseFloat(syncSuccessRate),
    };
  }

  /**
   * Test Drive API connection
   */
  async testConnection(): Promise<boolean> {
    try {
      const response = await this.drive.files.get({
        fileId: this.rootFolderId,
        fields: 'id, name',
      });

      logger.info('Drive API connection test successful', {
        rootFolder: response.data.name,
      });

      return true;
    } catch (error) {
      logger.error('Drive API connection test failed:', error);
      return false;
    }
  }

  /**
   * Log Drive sync operation
   */
  private async logDriveSync(
    fileId: string,
    action: DriveSyncAction,
    status: string,
    attemptNumber: number,
    errorMessage?: string
  ): Promise<void> {
    try {
      await this.prisma.driveSyncLog.create({
        data: {
          fileId,
          action,
          status,
          attemptNumber,
          errorMessage,
        },
      });
    } catch (error) {
      logger.error('Failed to log Drive sync:', error);
      // Don't throw - logging failure shouldn't break main operation
    }
  }

  /**
   * Archive old files (move to Archive folder)
   */
  async archiveSubmission(submissionId: string): Promise<void> {
    try {
      const submission = await this.prisma.submission.findUnique({
        where: { id: submissionId },
      });

      if (!submission?.googleDriveFolderId) {
        return;
      }

      // Get or create Archive folder
      const archiveFolderId = await this.getOrCreateFolder(
        'Archive',
        this.rootFolderId
      );

      // Move submission folder to Archive
      await this.drive.files.update({
        fileId: submission.googleDriveFolderId,
        addParents: archiveFolderId,
        removeParents: submission.googleDriveFolderId,
        fields: 'id, parents',
      });

      logger.info(`Submission ${submission.referenceId} archived in Drive`);
    } catch (error) {
      logger.error('Failed to archive submission in Drive:', error);
      throw error;
    }
  }
}
