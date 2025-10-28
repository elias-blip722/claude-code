/**
 * Authentication Service
 * Handles user authentication, registration, JWT tokens, and RBAC
 */

import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { PrismaClient, User, UserRole } from '@prisma/client';
import { logger } from '../common/logger';

export interface RegisterUserDto {
  email: string;
  password: string;
  name: string;
  role?: UserRole;
}

export interface LoginDto {
  email: string;
  password: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface TokenPayload {
  userId: string;
  email: string;
  role: UserRole;
}

export class AuthService {
  private prisma: PrismaClient;
  private jwtSecret: string;
  private jwtRefreshSecret: string;
  private readonly SALT_ROUNDS = 12;
  private readonly ACCESS_TOKEN_EXPIRY = '15m';
  private readonly REFRESH_TOKEN_EXPIRY = '7d';
  private readonly MAX_FAILED_ATTEMPTS = 5;
  private readonly LOCK_DURATION_MINUTES = 15;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
    this.jwtSecret = process.env.JWT_SECRET || 'your-secret-key';
    this.jwtRefreshSecret = process.env.JWT_REFRESH_SECRET || 'your-refresh-secret';
  }

  /**
   * Register a new user
   */
  async register(dto: RegisterUserDto): Promise<User> {
    try {
      // Check if user already exists
      const existingUser = await this.prisma.user.findUnique({
        where: { email: dto.email },
      });

      if (existingUser) {
        throw new Error('User with this email already exists');
      }

      // Validate password strength
      this.validatePassword(dto.password);

      // Hash password
      const hashedPassword = await bcrypt.hash(dto.password, this.SALT_ROUNDS);

      // Create user
      const user = await this.prisma.user.create({
        data: {
          email: dto.email,
          hashedPassword,
          name: dto.name,
          role: dto.role || UserRole.STAKEHOLDER,
          emailVerified: false,
        },
      });

      logger.info(`User registered successfully: ${user.email}`);

      return user;
    } catch (error) {
      logger.error('User registration failed:', error);
      throw error;
    }
  }

  /**
   * Login user with email and password
   */
  async login(dto: LoginDto, ipAddress?: string): Promise<{ user: User; tokens: AuthTokens }> {
    try {
      // Find user
      const user = await this.prisma.user.findUnique({
        where: { email: dto.email },
      });

      if (!user) {
        throw new Error('Invalid credentials');
      }

      // Check if account is locked
      if (user.lockedUntil && user.lockedUntil > new Date()) {
        const minutesRemaining = Math.ceil(
          (user.lockedUntil.getTime() - Date.now()) / (1000 * 60)
        );
        throw new Error(
          `Account is locked. Try again in ${minutesRemaining} minutes.`
        );
      }

      // Check if account is active
      if (!user.isActive) {
        throw new Error('Account is disabled. Please contact administrator.');
      }

      // Verify password
      const isPasswordValid = await bcrypt.compare(
        dto.password,
        user.hashedPassword || ''
      );

      if (!isPasswordValid) {
        // Increment failed login attempts
        await this.handleFailedLogin(user);
        throw new Error('Invalid credentials');
      }

      // Reset failed login attempts
      await this.prisma.user.update({
        where: { id: user.id },
        data: {
          failedLoginAttempts: 0,
          lockedUntil: null,
          lastLoginAt: new Date(),
          lastLoginIp: ipAddress,
        },
      });

      // Generate tokens
      const tokens = await this.generateTokens(user);

      // Create session
      await this.createSession(user.id, tokens.accessToken, tokens.refreshToken, ipAddress);

      logger.info(`User logged in successfully: ${user.email}`);

      return { user, tokens };
    } catch (error) {
      logger.error('Login failed:', error);
      throw error;
    }
  }

  /**
   * Handle failed login attempt
   */
  private async handleFailedLogin(user: User): Promise<void> {
    const failedAttempts = user.failedLoginAttempts + 1;

    const updateData: any = {
      failedLoginAttempts: failedAttempts,
    };

    // Lock account if max attempts reached
    if (failedAttempts >= this.MAX_FAILED_ATTEMPTS) {
      const lockUntil = new Date();
      lockUntil.setMinutes(lockUntil.getMinutes() + this.LOCK_DURATION_MINUTES);
      updateData.lockedUntil = lockUntil;

      logger.warn(`Account locked due to failed login attempts: ${user.email}`);
    }

    await this.prisma.user.update({
      where: { id: user.id },
      data: updateData,
    });
  }

  /**
   * Generate access and refresh tokens
   */
  private async generateTokens(user: User): Promise<AuthTokens> {
    const payload: TokenPayload = {
      userId: user.id,
      email: user.email,
      role: user.role,
    };

    const accessToken = jwt.sign(payload, this.jwtSecret, {
      expiresIn: this.ACCESS_TOKEN_EXPIRY,
    });

    const refreshToken = jwt.sign(payload, this.jwtRefreshSecret, {
      expiresIn: this.REFRESH_TOKEN_EXPIRY,
    });

    return { accessToken, refreshToken };
  }

  /**
   * Create session record
   */
  private async createSession(
    userId: string,
    accessToken: string,
    refreshToken: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7); // 7 days

    await this.prisma.session.create({
      data: {
        userId,
        token: accessToken,
        refreshToken,
        expiresAt,
        ipAddress,
        userAgent,
      },
    });
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    try {
      // Verify refresh token
      const payload = jwt.verify(refreshToken, this.jwtRefreshSecret) as TokenPayload;

      // Find session
      const session = await this.prisma.session.findUnique({
        where: { refreshToken },
        include: { user: true },
      });

      if (!session || session.expiresAt < new Date()) {
        throw new Error('Invalid or expired refresh token');
      }

      // Generate new tokens
      const tokens = await this.generateTokens(session.user);

      // Update session
      await this.prisma.session.update({
        where: { id: session.id },
        data: {
          token: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          lastActivity: new Date(),
        },
      });

      return tokens;
    } catch (error) {
      logger.error('Token refresh failed:', error);
      throw new Error('Invalid refresh token');
    }
  }

  /**
   * Logout user
   */
  async logout(accessToken: string): Promise<void> {
    try {
      await this.prisma.session.deleteMany({
        where: { token: accessToken },
      });

      logger.info('User logged out successfully');
    } catch (error) {
      logger.error('Logout failed:', error);
      throw error;
    }
  }

  /**
   * Verify JWT token
   */
  verifyToken(token: string): TokenPayload {
    try {
      return jwt.verify(token, this.jwtSecret) as TokenPayload;
    } catch (error) {
      throw new Error('Invalid token');
    }
  }

  /**
   * Validate password strength
   */
  private validatePassword(password: string): void {
    const minLength = 12;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSymbols = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    if (password.length < minLength) {
      throw new Error(`Password must be at least ${minLength} characters long`);
    }

    if (!hasUpperCase || !hasLowerCase || !hasNumbers || !hasSymbols) {
      throw new Error(
        'Password must contain uppercase, lowercase, numbers, and symbols'
      );
    }

    // Check against common passwords (simplified version)
    const commonPasswords = [
      'password123',
      'admin123',
      'letmein',
      'welcome123',
    ];
    if (commonPasswords.some((p) => password.toLowerCase().includes(p))) {
      throw new Error('Password is too common');
    }
  }

  /**
   * Change user password
   */
  async changePassword(
    userId: string,
    oldPassword: string,
    newPassword: string
  ): Promise<void> {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new Error('User not found');
    }

    // Verify old password
    const isPasswordValid = await bcrypt.compare(
      oldPassword,
      user.hashedPassword || ''
    );

    if (!isPasswordValid) {
      throw new Error('Current password is incorrect');
    }

    // Validate new password
    this.validatePassword(newPassword);

    // Hash new password
    const hashedPassword = await bcrypt.hash(newPassword, this.SALT_ROUNDS);

    // Update password
    await this.prisma.user.update({
      where: { id: userId },
      data: {
        hashedPassword,
        lastPasswordChange: new Date(),
      },
    });

    // Invalidate all sessions
    await this.prisma.session.deleteMany({
      where: { userId },
    });

    logger.info(`Password changed for user: ${user.email}`);
  }

  /**
   * Check if user has permission
   */
  hasPermission(user: User, requiredRole: UserRole): boolean {
    if (user.role === UserRole.ADMIN) {
      return true; // Admins have all permissions
    }

    return user.role === requiredRole;
  }

  /**
   * Check if user can access submission
   */
  async canAccessSubmission(userId: string, submissionId: string): Promise<boolean> {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      return false;
    }

    // Admins can access all submissions
    if (user.role === UserRole.ADMIN) {
      return true;
    }

    // Stakeholders can only access their own submissions
    const submission = await this.prisma.submission.findUnique({
      where: { id: submissionId },
    });

    return submission?.userId === userId;
  }
}
