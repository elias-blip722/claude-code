/**
 * Submission Service
 * Handles referral submission creation, updates, status changes, and queries
 */

import { PrismaClient, Submission, SubmissionStatus, SubmissionPriority, User } from '@prisma/client';
import { logger } from '../common/logger';
import { DriveService } from '../drive/drive.service';
import { NotificationService } from '../notifications/notification.service';

export interface CreateSubmissionDto {
  userId: string;
  title: string;
  description: string;
  priority?: SubmissionPriority;
}

export interface UpdateSubmissionDto {
  title?: string;
  description?: string;
  priority?: SubmissionPriority;
  assignedToId?: string;
}

export interface ChangeStatusDto {
  newStatus: SubmissionStatus;
  reason?: string;
  changedById: string;
}

export class SubmissionService {
  private prisma: PrismaClient;
  private driveService: DriveService;
  private notificationService: NotificationService;

  constructor(
    prisma: PrismaClient,
    driveService: DriveService,
    notificationService: NotificationService
  ) {
    this.prisma = prisma;
    this.driveService = driveService;
    this.notificationService = notificationService;
  }

  /**
   * Create a new submission
   */
  async create(dto: CreateSubmissionDto): Promise<Submission> {
    try {
      // Generate unique reference ID
      const referenceId = await this.generateReferenceId();

      // Create submission
      const submission = await this.prisma.submission.create({
        data: {
          referenceId,
          userId: dto.userId,
          title: dto.title,
          description: dto.description,
          priority: dto.priority || SubmissionPriority.MEDIUM,
          status: SubmissionStatus.RED, // Default status
        },
        include: {
          user: true,
        },
      });

      logger.info(`Submission created: ${referenceId}`, { submissionId: submission.id });

      // Create Drive folder asynchronously (don't block submission creation)
      this.createDriveFolderAsync(submission.id, referenceId);

      // Send confirmation notification to user
      await this.notificationService.sendSubmissionConfirmation(submission);

      // Notify admins of new submission
      await this.notificationService.notifyAdminsNewSubmission(submission);

      return submission;
    } catch (error) {
      logger.error('Failed to create submission:', error);
      throw error;
    }
  }

  /**
   * Create Drive folder asynchronously
   */
  private async createDriveFolderAsync(submissionId: string, referenceId: string): Promise<void> {
    try {
      await this.driveService.createSubmissionFolder(submissionId, referenceId);
    } catch (error) {
      logger.error(`Failed to create Drive folder for ${referenceId}:`, error);
      // Error is already logged in DriveService and database is updated
    }
  }

  /**
   * Generate unique reference ID (e.g., REF-001234)
   */
  private async generateReferenceId(): Promise<string> {
    const count = await this.prisma.submission.count();
    const nextNumber = count + 1;
    return `REF-${nextNumber.toString().padStart(6, '0')}`;
  }

  /**
   * Get submission by ID
   */
  async getById(id: string, userId?: string): Promise<Submission | null> {
    const submission = await this.prisma.submission.findUnique({
      where: { id },
      include: {
        user: true,
        assignedTo: true,
        files: {
          where: { deletedAt: null },
          orderBy: { uploadedAt: 'desc' },
        },
        comments: {
          where: { deletedAt: null },
          include: { user: true },
          orderBy: { createdAt: 'desc' },
        },
        statusHistory: {
          include: { changedBy: true },
          orderBy: { changedAt: 'desc' },
        },
        tags: {
          include: { tag: true },
        },
      },
    });

    return submission;
  }

  /**
   * Get submissions with filtering and pagination
   */
  async getMany(options: {
    userId?: string;
    status?: SubmissionStatus;
    priority?: SubmissionPriority;
    assignedToId?: string;
    search?: string;
    page?: number;
    limit?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }) {
    const {
      userId,
      status,
      priority,
      assignedToId,
      search,
      page = 1,
      limit = 25,
      sortBy = 'createdAt',
      sortOrder = 'desc',
    } = options;

    const where: any = {};

    if (userId) where.userId = userId;
    if (status) where.status = status;
    if (priority) where.priority = priority;
    if (assignedToId) where.assignedToId = assignedToId;

    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } },
        { referenceId: { contains: search, mode: 'insensitive' } },
      ];
    }

    const [submissions, total] = await Promise.all([
      this.prisma.submission.findMany({
        where,
        include: {
          user: { select: { id: true, name: true, email: true } },
          assignedTo: { select: { id: true, name: true } },
          files: { select: { id: true } },
          _count: { select: { comments: true } },
        },
        orderBy: { [sortBy]: sortOrder },
        skip: (page - 1) * limit,
        take: limit,
      }),
      this.prisma.submission.count({ where }),
    ]);

    return {
      submissions,
      pagination: {
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  /**
   * Update submission
   */
  async update(id: string, dto: UpdateSubmissionDto): Promise<Submission> {
    const submission = await this.prisma.submission.update({
      where: { id },
      data: dto,
      include: { user: true, assignedTo: true },
    });

    logger.info(`Submission updated: ${submission.referenceId}`);

    return submission;
  }

  /**
   * Change submission status (RED -> AMBER -> GREEN)
   */
  async changeStatus(id: string, dto: ChangeStatusDto): Promise<Submission> {
    const submission = await this.prisma.submission.findUnique({
      where: { id },
      include: { user: true },
    });

    if (!submission) {
      throw new Error('Submission not found');
    }

    const oldStatus = submission.status;
    const newStatus = dto.newStatus;

    // Update submission status
    const updated = await this.prisma.submission.update({
      where: { id },
      data: {
        status: newStatus,
        completedAt: newStatus === SubmissionStatus.GREEN ? new Date() : null,
      },
      include: { user: true, assignedTo: true },
    });

    // Create status history record
    await this.prisma.statusHistory.create({
      data: {
        submissionId: id,
        oldStatus,
        newStatus,
        reason: dto.reason,
        changedById: dto.changedById,
      },
    });

    logger.info(
      `Status changed for ${submission.referenceId}: ${oldStatus} -> ${newStatus}`
    );

    // Send notification to stakeholder
    if (oldStatus !== newStatus) {
      await this.notificationService.sendStatusChangeNotification(
        updated,
        oldStatus,
        newStatus
      );
    }

    return updated;
  }

  /**
   * Delete/Archive submission
   */
  async delete(id: string): Promise<void> {
    const submission = await this.prisma.submission.findUnique({
      where: { id },
    });

    if (!submission) {
      throw new Error('Submission not found');
    }

    // Soft delete - mark as archived
    await this.prisma.submission.update({
      where: { id },
      data: { archivedAt: new Date() },
    });

    // Archive in Google Drive
    try {
      await this.driveService.archiveSubmission(id);
    } catch (error) {
      logger.error('Failed to archive submission in Drive:', error);
      // Continue with deletion even if Drive archival fails
    }

    logger.info(`Submission archived: ${submission.referenceId}`);
  }

  /**
   * Get dashboard statistics
   */
  async getDashboardStats(userId?: string) {
    const where: any = userId ? { userId } : {};

    const [
      totalSubmissions,
      redCount,
      amberCount,
      greenCount,
      recentSubmissions,
      driveSyncStats,
    ] = await Promise.all([
      this.prisma.submission.count({ where }),
      this.prisma.submission.count({ where: { ...where, status: SubmissionStatus.RED } }),
      this.prisma.submission.count({ where: { ...where, status: SubmissionStatus.AMBER } }),
      this.prisma.submission.count({ where: { ...where, status: SubmissionStatus.GREEN } }),
      this.prisma.submission.findMany({
        where,
        include: {
          user: { select: { name: true, email: true } },
          assignedTo: { select: { name: true } },
        },
        orderBy: { createdAt: 'desc' },
        take: 10,
      }),
      this.driveService.getSyncStats(),
    ]);

    // Calculate average processing time
    const completedSubmissions = await this.prisma.submission.findMany({
      where: {
        ...where,
        status: SubmissionStatus.GREEN,
        completedAt: { not: null },
      },
      select: { createdAt: true, completedAt: true },
    });

    let avgProcessingTime = 0;
    if (completedSubmissions.length > 0) {
      const totalTime = completedSubmissions.reduce((sum, s) => {
        const diff = s.completedAt!.getTime() - s.createdAt.getTime();
        return sum + diff;
      }, 0);
      avgProcessingTime = totalTime / completedSubmissions.length / (1000 * 60 * 60 * 24); // in days
    }

    return {
      totalSubmissions,
      statusDistribution: {
        red: redCount,
        amber: amberCount,
        green: greenCount,
      },
      statusPercentages: {
        red: totalSubmissions > 0 ? (redCount / totalSubmissions) * 100 : 0,
        amber: totalSubmissions > 0 ? (amberCount / totalSubmissions) * 100 : 0,
        green: totalSubmissions > 0 ? (greenCount / totalSubmissions) * 100 : 0,
      },
      recentSubmissions,
      driveSyncStats,
      avgProcessingTimeDays: Math.round(avgProcessingTime * 10) / 10,
    };
  }

  /**
   * Assign submission to admin
   */
  async assign(id: string, assignedToId: string): Promise<Submission> {
    const submission = await this.prisma.submission.update({
      where: { id },
      data: { assignedToId },
      include: { user: true, assignedTo: true },
    });

    logger.info(`Submission ${submission.referenceId} assigned to ${assignedToId}`);

    // Notify assigned admin
    await this.notificationService.sendAssignmentNotification(submission);

    return submission;
  }

  /**
   * Add comment to submission
   */
  async addComment(
    submissionId: string,
    userId: string,
    content: string,
    isInternal = false
  ) {
    const comment = await this.prisma.comment.create({
      data: {
        submissionId,
        userId,
        content,
        isInternal,
      },
      include: {
        user: { select: { name: true, email: true } },
        submission: { include: { user: true } },
      },
    });

    logger.info(`Comment added to submission ${submissionId}`);

    // Notify stakeholder if not internal comment
    if (!isInternal) {
      await this.notificationService.sendCommentNotification(comment);
    }

    return comment;
  }

  /**
   * Get submission activity feed
   */
  async getActivityFeed(submissionId: string) {
    const [comments, statusChanges] = await Promise.all([
      this.prisma.comment.findMany({
        where: { submissionId, deletedAt: null },
        include: { user: true },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.statusHistory.findMany({
        where: { submissionId },
        include: { changedBy: true },
        orderBy: { changedAt: 'desc' },
      }),
    ]);

    // Merge and sort by date
    const activities = [
      ...comments.map((c) => ({
        type: 'comment',
        data: c,
        timestamp: c.createdAt,
      })),
      ...statusChanges.map((s) => ({
        type: 'status_change',
        data: s,
        timestamp: s.changedAt,
      })),
    ].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

    return activities;
  }
}
