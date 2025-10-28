/**
 * Admin Dashboard Component
 * Shows overview of all submissions, RAG status, and Drive sync statistics
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  FolderOpen as DriveIcon,
  CheckCircle as SyncedIcon,
  Error as FailedIcon,
  Sync as SyncingIcon,
  PendingActions as PendingIcon,
} from '@mui/icons-material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface DashboardStats {
  totalSubmissions: number;
  statusDistribution: {
    red: number;
    amber: number;
    green: number;
  };
  statusPercentages: {
    red: number;
    amber: number;
    green: number;
  };
  recentSubmissions: Submission[];
  driveSyncStats: {
    totalFiles: number;
    syncedFiles: number;
    failedFiles: number;
    pendingFiles: number;
    syncingFiles: number;
    syncSuccessRate: number;
  };
  avgProcessingTimeDays: number;
}

interface Submission {
  id: string;
  referenceId: string;
  title: string;
  status: 'RED' | 'AMBER' | 'GREEN';
  priority: string;
  createdAt: string;
  user: {
    name: string;
    email: string;
  };
  assignedTo?: {
    name: string;
  };
  googleDriveFolderUrl?: string;
  driveSyncStatus: 'PENDING' | 'SYNCING' | 'SYNCED' | 'FAILED';
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/dashboard/stats', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard stats');
      }

      const data = await response.json();
      setStats(data);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'RED':
        return 'error';
      case 'AMBER':
        return 'warning';
      case 'GREEN':
        return 'success';
      default:
        return 'default';
    }
  };

  const getSyncStatusIcon = (status: string) => {
    switch (status) {
      case 'SYNCED':
        return <SyncedIcon color="success" />;
      case 'FAILED':
        return <FailedIcon color="error" />;
      case 'SYNCING':
        return <SyncingIcon color="info" />;
      case 'PENDING':
        return <PendingIcon color="warning" />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!stats) {
    return null;
  }

  // Prepare chart data
  const chartData = [
    { name: 'RED (Not Reviewed)', value: stats.statusDistribution.red, color: '#f44336' },
    { name: 'AMBER (In Review)', value: stats.statusDistribution.amber, color: '#ff9800' },
    { name: 'GREEN (Completed)', value: stats.statusDistribution.green, color: '#4caf50' },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Submissions
              </Typography>
              <Typography variant="h3">{stats.totalSubmissions}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Drive Sync Success Rate
              </Typography>
              <Typography variant="h3" color={stats.driveSyncStats.syncSuccessRate >= 95 ? 'success.main' : 'error.main'}>
                {stats.driveSyncStats.syncSuccessRate.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Avg. Processing Time
              </Typography>
              <Typography variant="h3">{stats.avgProcessingTimeDays} days</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Files Synced
              </Typography>
              <Typography variant="h3">
                {stats.driveSyncStats.syncedFiles} / {stats.driveSyncStats.totalFiles}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts and Details */}
      <Grid container spacing={3}>
        {/* Status Distribution Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Submission Status Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Drive Sync Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Google Drive Sync Status
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box display="flex" justifyContent="space-between" mb={2}>
                <Typography>Synced:</Typography>
                <Typography fontWeight="bold" color="success.main">
                  {stats.driveSyncStats.syncedFiles}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" mb={2}>
                <Typography>Failed:</Typography>
                <Typography fontWeight="bold" color="error.main">
                  {stats.driveSyncStats.failedFiles}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" mb={2}>
                <Typography>Syncing:</Typography>
                <Typography fontWeight="bold" color="info.main">
                  {stats.driveSyncStats.syncingFiles}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" mb={2}>
                <Typography>Pending:</Typography>
                <Typography fontWeight="bold" color="warning.main">
                  {stats.driveSyncStats.pendingFiles}
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Recent Submissions Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Submissions
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Reference ID</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Submitter</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Drive Sync</TableCell>
                    <TableCell>Priority</TableCell>
                    <TableCell>Assigned To</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {stats.recentSubmissions.map((submission) => (
                    <TableRow key={submission.id}>
                      <TableCell>{submission.referenceId}</TableCell>
                      <TableCell>{submission.title}</TableCell>
                      <TableCell>{submission.user.name}</TableCell>
                      <TableCell>
                        <Chip label={submission.status} color={getStatusColor(submission.status) as any} size="small" />
                      </TableCell>
                      <TableCell>{getSyncStatusIcon(submission.driveSyncStatus)}</TableCell>
                      <TableCell>{submission.priority}</TableCell>
                      <TableCell>{submission.assignedTo?.name || 'Unassigned'}</TableCell>
                      <TableCell>
                        {submission.googleDriveFolderUrl && (
                          <IconButton
                            size="small"
                            onClick={() => window.open(submission.googleDriveFolderUrl, '_blank')}
                            title="Open in Google Drive"
                          >
                            <DriveIcon />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
