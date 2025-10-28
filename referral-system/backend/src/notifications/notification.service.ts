/**
 * Notification Service
 * Handles email and in-app notifications for all system events
 */

import { PrismaClient, Submission, SubmissionStatus, NotificationType, User } from '@prisma/client';
import nodemailer from 'nodemailer';
import { logger } from '../common/logger';

export class NotificationService {
  private prisma: PrismaClient;
  private transporter: nodemailer.Transporter;
  private fromEmail: string;
  private appUrl: string;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
    this.fromEmail = process.env.EMAIL_FROM || 'noreply@referralsystem.com';
    this.appUrl = process.env.APP_URL || 'http://localhost:3000';

    this.initializeEmailTransporter();
  }

  /**
   * Initialize email transporter
   */
  private initializeEmailTransporter(): void {
    // Use SendGrid, AWS SES, or SMTP
    const emailProvider = process.env.EMAIL_PROVIDER || 'smtp';

    if (emailProvider === 'sendgrid') {
      this.transporter = nodemailer.createTransporter({
        service: 'SendGrid',
        auth: {
          user: 'apikey',
          pass: process.env.SENDGRID_API_KEY,
        },
      });
    } else {
      // SMTP configuration
      this.transporter = nodemailer.createTransporter({
        host: process.env.SMTP_HOST || 'localhost',
        port: parseInt(process.env.SMTP_PORT || '587'),
        secure: process.env.SMTP_SECURE === 'true',
        auth: {
          user: process.env.SMTP_USER,
          pass: process.env.SMTP_PASS,
        },
      });
    }
  }

  /**
   * Send submission confirmation email to stakeholder
   */
  async sendSubmissionConfirmation(submission: any): Promise<void> {
    try {
      const subject = `Submission Received: ${submission.referenceId}`;
      const body = `
        <h2>Thank you for your submission</h2>
        <p>Dear ${submission.user.name},</p>
        <p>We have received your referral submission and it is being processed.</p>

        <h3>Submission Details:</h3>
        <ul>
          <li><strong>Reference ID:</strong> ${submission.referenceId}</li>
          <li><strong>Title:</strong> ${submission.title}</li>
          <li><strong>Submitted:</strong> ${new Date(submission.createdAt).toLocaleString()}</li>
          <li><strong>Status:</strong> <span style="color: red;">RED</span> (Not yet reviewed)</li>
        </ul>

        <p><strong>Backup Confirmation:</strong> Your files have been securely backed up to our system.</p>

        <p>You can track your submission at: <a href="${this.appUrl}/submissions/${submission.id}">${this.appUrl}/submissions/${submission.id}</a></p>

        <p>You will receive email updates when your submission status changes.</p>

        <p>Best regards,<br/>Referral Management Team</p>
      `;

      await this.sendEmail(submission.user.email, subject, body);

      // Create in-app notification
      await this.createNotification(
        submission.userId,
        NotificationType.SUBMISSION_CREATED,
        'Submission Received',
        `Your submission ${submission.referenceId} has been received and is being processed.`,
        `/submissions/${submission.id}`
      );

      logger.info(`Confirmation email sent to ${submission.user.email}`);
    } catch (error) {
      logger.error('Failed to send confirmation email:', error);
      // Don't throw - email failure shouldn't break submission
    }
  }

  /**
   * Notify all admins of new submission
   */
  async notifyAdminsNewSubmission(submission: any): Promise<void> {
    try {
      const admins = await this.prisma.user.findMany({
        where: { role: 'ADMIN', isActive: true },
      });

      const driveLink = submission.googleDriveFolderUrl || 'Pending sync';

      for (const admin of admins) {
        const subject = `New Submission: ${submission.referenceId}`;
        const body = `
          <h2>New Referral Submission</h2>
          <p>Dear ${admin.name},</p>
          <p>A new referral has been submitted and requires review.</p>

          <h3>Submission Details:</h3>
          <ul>
            <li><strong>Reference ID:</strong> ${submission.referenceId}</li>
            <li><strong>Submitted By:</strong> ${submission.user.name} (${submission.user.email})</li>
            <li><strong>Title:</strong> ${submission.title}</li>
            <li><strong>Priority:</strong> ${submission.priority}</li>
            <li><strong>Submitted:</strong> ${new Date(submission.createdAt).toLocaleString()}</li>
          </ul>

          <p><strong>Google Drive Folder:</strong> <a href="${driveLink}">Open in Drive</a></p>

          <p><a href="${this.appUrl}/admin/submissions/${submission.id}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Review Submission</a></p>

          <p>Best regards,<br/>Referral Management System</p>
        `;

        await this.sendEmail(admin.email, subject, body);

        // Create in-app notification
        await this.createNotification(
          admin.id,
          NotificationType.SUBMISSION_CREATED,
          'New Submission',
          `${submission.user.name} submitted ${submission.referenceId}`,
          `/admin/submissions/${submission.id}`
        );
      }

      logger.info(`New submission notifications sent to ${admins.length} admins`);
    } catch (error) {
      logger.error('Failed to notify admins:', error);
    }
  }

  /**
   * Send status change notification to stakeholder
   */
  async sendStatusChangeNotification(
    submission: any,
    oldStatus: SubmissionStatus,
    newStatus: SubmissionStatus
  ): Promise<void> {
    try {
      const statusColors = {
        RED: '#f44336',
        AMBER: '#ff9800',
        GREEN: '#4caf50',
      };

      const statusMessages = {
        RED: 'Your submission has been received and is awaiting review.',
        AMBER: 'Your submission is being reviewed by our team.',
        GREEN: 'Your submission has been completed and resolved.',
      };

      const subject = `Status Update: ${submission.referenceId} - ${newStatus}`;
      const body = `
        <h2>Submission Status Updated</h2>
        <p>Dear ${submission.user.name},</p>
        <p>The status of your submission has been updated.</p>

        <h3>Submission Details:</h3>
        <ul>
          <li><strong>Reference ID:</strong> ${submission.referenceId}</li>
          <li><strong>Title:</strong> ${submission.title}</li>
          <li><strong>Previous Status:</strong> <span style="color: ${statusColors[oldStatus]};">${oldStatus}</span></li>
          <li><strong>New Status:</strong> <span style="color: ${statusColors[newStatus]};">${newStatus}</span></li>
        </ul>

        <p><strong>What this means:</strong> ${statusMessages[newStatus]}</p>

        ${newStatus === SubmissionStatus.GREEN ? '<p>Thank you for your submission. No further action is required.</p>' : ''}

        <p><a href="${this.appUrl}/submissions/${submission.id}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Submission</a></p>

        <p>Best regards,<br/>Referral Management Team</p>
      `;

      await this.sendEmail(submission.user.email, subject, body);

      // Create in-app notification
      await this.createNotification(
        submission.userId,
        NotificationType.STATUS_CHANGED,
        `Status Updated: ${newStatus}`,
        `Your submission ${submission.referenceId} status changed to ${newStatus}`,
        `/submissions/${submission.id}`
      );

      logger.info(`Status change email sent to ${submission.user.email}`);
    } catch (error) {
      logger.error('Failed to send status change email:', error);
    }
  }

  /**
   * Send Drive sync failure alert to admins
   */
  async sendDriveSyncFailureAlert(submissionId: string, error: string): Promise<void> {
    try {
      const admins = await this.prisma.user.findMany({
        where: { role: 'ADMIN', isActive: true },
      });

      const submission = await this.prisma.submission.findUnique({
        where: { id: submissionId },
        include: { user: true },
      });

      if (!submission) return;

      for (const admin of admins) {
        const subject = `[ALERT] Google Drive Sync Failed: ${submission.referenceId}`;
        const body = `
          <h2 style="color: #f44336;">Google Drive Sync Failure</h2>
          <p>Dear ${admin.name},</p>
          <p>A Google Drive sync operation has failed and requires attention.</p>

          <h3>Details:</h3>
          <ul>
            <li><strong>Submission:</strong> ${submission.referenceId}</li>
            <li><strong>Submitter:</strong> ${submission.user.name}</li>
            <li><strong>Error:</strong> ${error}</li>
            <li><strong>Time:</strong> ${new Date().toLocaleString()}</li>
          </ul>

          <p><a href="${this.appUrl}/admin/submissions/${submission.id}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Retry Sync</a></p>

          <p>Please investigate and retry the sync operation.</p>

          <p>Referral Management System</p>
        `;

        await this.sendEmail(admin.email, subject, body);

        // Create in-app notification
        await this.createNotification(
          admin.id,
          NotificationType.DRIVE_SYNC_FAILED,
          'Drive Sync Failed',
          `Failed to sync ${submission.referenceId} to Google Drive`,
          `/admin/submissions/${submission.id}`
        );
      }

      logger.warn(`Drive sync failure alerts sent for ${submission.referenceId}`);
    } catch (error) {
      logger.error('Failed to send Drive sync failure alert:', error);
    }
  }

  /**
   * Send comment notification
   */
  async sendCommentNotification(comment: any): Promise<void> {
    try {
      const subject = `New Comment on ${comment.submission.referenceId}`;
      const body = `
        <h2>New Comment on Your Submission</h2>
        <p>Dear ${comment.submission.user.name},</p>
        <p>A new comment has been added to your submission.</p>

        <h3>Comment Details:</h3>
        <p><strong>From:</strong> ${comment.user.name}</p>
        <p><strong>Comment:</strong></p>
        <blockquote style="border-left: 3px solid #ccc; padding-left: 10px; margin: 10px 0;">
          ${comment.content}
        </blockquote>

        <p><a href="${this.appUrl}/submissions/${comment.submissionId}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View & Reply</a></p>

        <p>Best regards,<br/>Referral Management Team</p>
      `;

      await this.sendEmail(comment.submission.user.email, subject, body);

      // Create in-app notification
      await this.createNotification(
        comment.submission.userId,
        NotificationType.COMMENT_ADDED,
        'New Comment',
        `${comment.user.name} commented on ${comment.submission.referenceId}`,
        `/submissions/${comment.submissionId}`
      );
    } catch (error) {
      logger.error('Failed to send comment notification:', error);
    }
  }

  /**
   * Send assignment notification
   */
  async sendAssignmentNotification(submission: any): Promise<void> {
    try {
      if (!submission.assignedTo) return;

      const subject = `Submission Assigned: ${submission.referenceId}`;
      const body = `
        <h2>Submission Assigned to You</h2>
        <p>Dear ${submission.assignedTo.name},</p>
        <p>A referral submission has been assigned to you for review.</p>

        <h3>Submission Details:</h3>
        <ul>
          <li><strong>Reference ID:</strong> ${submission.referenceId}</li>
          <li><strong>Title:</strong> ${submission.title}</li>
          <li><strong>Submitted By:</strong> ${submission.user.name}</li>
          <li><strong>Priority:</strong> ${submission.priority}</li>
          <li><strong>Status:</strong> ${submission.status}</li>
        </ul>

        <p><a href="${this.appUrl}/admin/submissions/${submission.id}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Review Now</a></p>

        <p>Best regards,<br/>Referral Management System</p>
      `;

      await this.sendEmail(submission.assignedTo.email, subject, body);

      // Create in-app notification
      await this.createNotification(
        submission.assignedToId,
        NotificationType.ASSIGNMENT_CHANGED,
        'Submission Assigned',
        `${submission.referenceId} has been assigned to you`,
        `/admin/submissions/${submission.id}`
      );
    } catch (error) {
      logger.error('Failed to send assignment notification:', error);
    }
  }

  /**
   * Send email
   */
  private async sendEmail(to: string, subject: string, htmlBody: string): Promise<void> {
    try {
      // Queue email instead of sending immediately
      await this.prisma.emailQueue.create({
        data: {
          to,
          subject,
          htmlBody,
          priority: 5,
        },
      });

      logger.info(`Email queued to ${to}: ${subject}`);
    } catch (error) {
      logger.error('Failed to queue email:', error);
      throw error;
    }
  }

  /**
   * Process email queue (called by background job)
   */
  async processEmailQueue(): Promise<void> {
    try {
      const emails = await this.prisma.emailQueue.findMany({
        where: {
          status: 'PENDING',
          scheduledFor: { lte: new Date() },
        },
        orderBy: [{ priority: 'asc' }, { createdAt: 'asc' }],
        take: 10,
      });

      for (const email of emails) {
        try {
          await this.prisma.emailQueue.update({
            where: { id: email.id },
            data: { status: 'SENDING' },
          });

          await this.transporter.sendMail({
            from: this.fromEmail,
            to: email.to,
            subject: email.subject,
            html: email.htmlBody,
          });

          await this.prisma.emailQueue.update({
            where: { id: email.id },
            data: {
              status: 'SENT',
              sentAt: new Date(),
            },
          });

          logger.info(`Email sent to ${email.to}`);
        } catch (error) {
          logger.error(`Failed to send email to ${email.to}:`, error);

          await this.prisma.emailQueue.update({
            where: { id: email.id },
            data: {
              status: 'FAILED',
              attempts: { increment: 1 },
              lastAttemptAt: new Date(),
              error: (error as Error).message,
            },
          });
        }
      }
    } catch (error) {
      logger.error('Email queue processing failed:', error);
    }
  }

  /**
   * Create in-app notification
   */
  private async createNotification(
    userId: string,
    type: NotificationType,
    title: string,
    message: string,
    link?: string
  ): Promise<void> {
    try {
      await this.prisma.notification.create({
        data: {
          userId,
          type,
          title,
          message,
          link,
        },
      });
    } catch (error) {
      logger.error('Failed to create notification:', error);
    }
  }

  /**
   * Get user notifications
   */
  async getUserNotifications(userId: string, unreadOnly = false) {
    return await this.prisma.notification.findMany({
      where: {
        userId,
        ...(unreadOnly ? { isRead: false } : {}),
      },
      orderBy: { createdAt: 'desc' },
      take: 50,
    });
  }

  /**
   * Mark notification as read
   */
  async markAsRead(id: string): Promise<void> {
    await this.prisma.notification.update({
      where: { id },
      data: {
        isRead: true,
        readAt: new Date(),
      },
    });
  }

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(userId: string): Promise<void> {
    await this.prisma.notification.updateMany({
      where: { userId, isRead: false },
      data: {
        isRead: true,
        readAt: new Date(),
      },
    });
  }
}
