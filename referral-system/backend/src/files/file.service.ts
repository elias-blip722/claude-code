/**
 * File Service
 * Handles file uploads, virus scanning, storage, and Google Drive sync
 */

import { PrismaClient, File, DriveSyncStatus } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';
import { promisify } from 'util';
import { exec } from 'child_process';
import { logger } from '../common/logger';
import { DriveService } from '../drive/drive.service';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);
const unlinkAsync = promisify(fs.unlink);
const statAsync = promisify(fs.stat);

export interface UploadFileDto {
  submissionId: string;
  originalFilename: string;
  mimeType: string;
  buffer: Buffer;
}

export class FileService {
  private prisma: PrismaClient;
  private driveService: DriveService;
  private uploadDir: string;
  private readonly MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
  private readonly MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB
  private readonly MAX_FILES_PER_SUBMISSION = 10;
  private readonly ALLOWED_MIMETYPES = [
    // Microsoft Office
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
    'application/msword', // .doc
    'application/vnd.openxmlformats-officedocument.presentationml.presentation', // .pptx
    'application/vnd.ms-powerpoint', // .ppt
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    'application/vnd.ms-excel', // .xls
    // PDF
    'application/pdf',
    // Images
    'image/jpeg',
    'image/png',
    'image/gif',
    // Plain text
    'text/plain',
  ];

  constructor(prisma: PrismaClient, driveService: DriveService) {
    this.prisma = prisma;
    this.driveService = driveService;
    this.uploadDir = process.env.UPLOAD_DIR || path.join(__dirname, '../../uploads');

    // Ensure upload directory exists
    if (!fs.existsSync(this.uploadDir)) {
      fs.mkdirSync(this.uploadDir, { recursive: true });
    }
  }

  /**
   * Upload file with validation and virus scanning
   */
  async uploadFile(dto: UploadFileDto): Promise<File> {
    try {
      // Validate file count
      await this.validateFileCount(dto.submissionId);

      // Validate file size
      this.validateFileSize(dto.buffer.length);

      // Validate MIME type
      this.validateMimeType(dto.mimeType);

      // Validate filename (prevent path traversal)
      const sanitizedFilename = this.sanitizeFilename(dto.originalFilename);

      // Generate unique filename
      const fileExtension = path.extname(sanitizedFilename);
      const uniqueFilename = `${uuidv4()}${fileExtension}`;
      const filePath = path.join(this.uploadDir, uniqueFilename);

      // Save file to disk
      await fs.promises.writeFile(filePath, dto.buffer);

      logger.info(`File saved to disk: ${uniqueFilename}`);

      // Create file record
      const file = await this.prisma.file.create({
        data: {
          submissionId: dto.submissionId,
          filename: uniqueFilename,
          originalFilename: sanitizedFilename,
          filePath,
          fileSize: dto.buffer.length,
          mimeType: dto.mimeType,
          virusScanStatus: 'pending',
          driveSyncStatus: DriveSyncStatus.PENDING,
        },
      });

      // Queue virus scan (async)
      this.scanFileAsync(file.id, filePath);

      // Queue Drive upload (async)
      this.uploadToDriveAsync(file.id);

      return file;
    } catch (error) {
      logger.error('File upload failed:', error);
      throw error;
    }
  }

  /**
   * Validate file count per submission
   */
  private async validateFileCount(submissionId: string): Promise<void> {
    const count = await this.prisma.file.count({
      where: { submissionId, deletedAt: null },
    });

    if (count >= this.MAX_FILES_PER_SUBMISSION) {
      throw new Error(
        `Maximum ${this.MAX_FILES_PER_SUBMISSION} files allowed per submission`
      );
    }
  }

  /**
   * Validate total file size per submission
   */
  async validateTotalSize(submissionId: string, newFileSize: number): Promise<void> {
    const files = await this.prisma.file.findMany({
      where: { submissionId, deletedAt: null },
      select: { fileSize: true },
    });

    const totalSize = files.reduce((sum, f) => sum + f.fileSize, 0) + newFileSize;

    if (totalSize > this.MAX_TOTAL_SIZE) {
      throw new Error(
        `Total file size exceeds maximum of ${this.MAX_TOTAL_SIZE / (1024 * 1024)}MB`
      );
    }
  }

  /**
   * Validate individual file size
   */
  private validateFileSize(size: number): void {
    if (size > this.MAX_FILE_SIZE) {
      throw new Error(
        `File size exceeds maximum of ${this.MAX_FILE_SIZE / (1024 * 1024)}MB`
      );
    }
  }

  /**
   * Validate MIME type
   */
  private validateMimeType(mimeType: string): void {
    if (!this.ALLOWED_MIMETYPES.includes(mimeType)) {
      throw new Error(`File type ${mimeType} is not allowed`);
    }
  }

  /**
   * Sanitize filename to prevent path traversal attacks
   */
  private sanitizeFilename(filename: string): string {
    // Remove path separators and null bytes
    let sanitized = filename.replace(/[/\\\\0]/g, '');

    // Remove any leading dots (hidden files)
    sanitized = sanitized.replace(/^\\.+/, '');

    // Limit length
    const maxLength = 255;
    if (sanitized.length > maxLength) {
      const ext = path.extname(sanitized);
      const name = path.basename(sanitized, ext);
      sanitized = name.substring(0, maxLength - ext.length) + ext;
    }

    return sanitized || 'file';
  }

  /**
   * Scan file for viruses using ClamAV
   */
  private async scanFileAsync(fileId: string, filePath: string): Promise<void> {
    try {
      await this.prisma.file.update({
        where: { id: fileId },
        data: { virusScanStatus: 'scanning' },
      });

      const result = await this.scanWithClamAV(filePath);

      if (result.infected) {
        // File is infected
        await this.prisma.file.update({
          where: { id: fileId },
          data: {
            virusScanStatus: 'infected',
            virusScanResult: result.virus || 'Malware detected',
            virusScanAt: new Date(),
          },
        });

        // Delete infected file
        await unlinkAsync(filePath);

        logger.warn(`Infected file detected and deleted: ${fileId}`);
      } else {
        // File is clean
        await this.prisma.file.update({
          where: { id: fileId },
          data: {
            virusScanStatus: 'clean',
            virusScanResult: 'No threats detected',
            virusScanAt: new Date(),
          },
        });

        logger.info(`File scanned and clean: ${fileId}`);
      }
    } catch (error) {
      logger.error('Virus scan failed:', error);

      await this.prisma.file.update({
        where: { id: fileId },
        data: {
          virusScanStatus: 'error',
          virusScanResult: (error as Error).message,
          virusScanAt: new Date(),
        },
      });
    }
  }

  /**
   * Scan file with ClamAV
   */
  private async scanWithClamAV(
    filePath: string
  ): Promise<{ infected: boolean; virus?: string }> {
    try {
      // Check if ClamAV is installed
      const { stdout } = await execPromise(`clamscan --version`);

      if (!stdout) {
        logger.warn('ClamAV not installed, skipping virus scan');
        return { infected: false };
      }

      // Scan file
      const { stdout: scanResult } = await execPromise(
        `clamscan --no-summary "${filePath}"`
      );

      if (scanResult.includes('FOUND')) {
        const virusMatch = scanResult.match(/: (.+) FOUND/);
        return {
          infected: true,
          virus: virusMatch ? virusMatch[1] : 'Unknown',
        };
      }

      return { infected: false };
    } catch (error: any) {
      // ClamAV returns exit code 1 if virus found
      if (error.code === 1) {
        return { infected: true, virus: 'Malware detected' };
      }

      // For development: if ClamAV not available, skip scanning
      if (process.env.NODE_ENV === 'development') {
        logger.warn('Virus scanning skipped in development mode');
        return { infected: false };
      }

      throw error;
    }
  }

  /**
   * Upload file to Google Drive asynchronously
   */
  private async uploadToDriveAsync(fileId: string): Promise<void> {
    try {
      const file = await this.prisma.file.findUnique({
        where: { id: fileId },
      });

      if (!file) {
        throw new Error('File not found');
      }

      // Wait for virus scan to complete
      if (file.virusScanStatus === 'pending' || file.virusScanStatus === 'scanning') {
        // Wait up to 30 seconds for scan to complete
        for (let i = 0; i < 30; i++) {
          await new Promise((resolve) => setTimeout(resolve, 1000));

          const updatedFile = await this.prisma.file.findUnique({
            where: { id: fileId },
          });

          if (
            updatedFile?.virusScanStatus === 'clean' ||
            updatedFile?.virusScanStatus === 'error'
          ) {
            break;
          }
        }
      }

      // Re-fetch file to get latest virus scan status
      const scannedFile = await this.prisma.file.findUnique({
        where: { id: fileId },
      });

      // Only upload if file is clean
      if (scannedFile?.virusScanStatus !== 'clean') {
        logger.warn(`Skipping Drive upload for file ${fileId}: not clean`);
        return;
      }

      // Upload to Drive
      await this.driveService.uploadFile({
        submissionId: scannedFile.submissionId,
        fileId: scannedFile.id,
        filePath: scannedFile.filePath,
        filename: scannedFile.originalFilename,
        mimeType: scannedFile.mimeType,
      });
    } catch (error) {
      logger.error(`Drive upload failed for file ${fileId}:`, error);
      // Error is already handled in DriveService
    }
  }

  /**
   * Get file by ID
   */
  async getById(id: string): Promise<File | null> {
    return await this.prisma.file.findUnique({
      where: { id },
      include: { submission: true },
    });
  }

  /**
   * Get files for submission
   */
  async getBySubmission(submissionId: string): Promise<File[]> {
    return await this.prisma.file.findMany({
      where: { submissionId, deletedAt: null },
      orderBy: { uploadedAt: 'desc' },
    });
  }

  /**
   * Delete file
   */
  async deleteFile(id: string): Promise<void> {
    const file = await this.prisma.file.findUnique({
      where: { id },
    });

    if (!file) {
      throw new Error('File not found');
    }

    // Soft delete in database
    await this.prisma.file.update({
      where: { id },
      data: { deletedAt: new Date() },
    });

    // Delete physical file
    try {
      if (fs.existsSync(file.filePath)) {
        await unlinkAsync(file.filePath);
      }
    } catch (error) {
      logger.error('Failed to delete physical file:', error);
    }

    logger.info(`File deleted: ${id}`);
  }

  /**
   * Get file download stream
   */
  async getFileStream(id: string): Promise<{ stream: fs.ReadStream; file: File }> {
    const file = await this.getById(id);

    if (!file) {
      throw new Error('File not found');
    }

    if (!fs.existsSync(file.filePath)) {
      throw new Error('File not found on disk');
    }

    const stream = fs.createReadStream(file.filePath);

    return { stream, file };
  }

  /**
   * Retry failed Drive sync
   */
  async retryDriveSync(id: string): Promise<void> {
    const file = await this.prisma.file.findUnique({
      where: { id },
    });

    if (!file) {
      throw new Error('File not found');
    }

    if (file.driveSyncStatus !== DriveSyncStatus.FAILED) {
      throw new Error('File is not in failed state');
    }

    await this.driveService.retryFailedSync(id);
  }
}
