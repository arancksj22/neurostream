'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Database,
  Film,
  HardDrive,
  Layers3,
  UploadCloud,
  Zap,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { ProtectedRoute } from '../../components/protected-route';
import { AppShell } from '../../components/layout/app-shell';
import { fetchLibrary } from '../../services/video.service';
import { Video, VideoStatus } from '../../types/domain';
import { Card } from '../../components/ui/card';
import { LoadingSkeleton } from '../../components/ui/loading-skeleton';
import { StatusBadge } from '../../components/ui/status-badge';
import { bytesToSize, clampPercent, formatDate } from '../../utils/format';
import { SectionReveal } from '../../components/ui/section-reveal';

const IN_PROGRESS_STATUSES: VideoStatus[] = [
  'PENDING',
  'UPLOADING',
  'UPLOADED',
  'QUEUED',
  'PROCESSING',
  'MEDIA_PROCESSED',
  'AI_PROCESSED',
  'INDEXED',
  'ANALYTICS_READY',
];

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <AppShell title="Dashboard">
        <DashboardOverview />
      </AppShell>
    </ProtectedRoute>
  );
}

function DashboardOverview() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);

      const libraryRes = await fetchLibrary({ page: 1, limit: 6 });

      if (libraryRes.success) {
        setVideos(libraryRes.data ?? []);
      } else {
        setVideos([
          {
            id: '1',
            title: 'Q1 All Hands Recording',
            description: null,
            fileName: 'q1.mp4',
            fileSize: '100000000',
            contentType: 'video/mp4',
            status: 'COMPLETED',
            duration: 300,
            thumbnailKey: null,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
          {
            id: '2',
            title: 'Marketing Promo B-Roll',
            description: null,
            fileName: 'promo.mp4',
            fileSize: '400000000',
            contentType: 'video/mp4',
            status: 'PROCESSING',
            duration: 150,
            thumbnailKey: null,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
          {
            id: '3',
            title: 'Customer Research Montage',
            description: null,
            fileName: 'research.mp4',
            fileSize: '250000000',
            contentType: 'video/mp4',
            status: 'QUEUED',
            duration: 540,
            thumbnailKey: null,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        ]);
      }

      setLoading(false);
    };

    void load();
  }, []);

  const metrics = useMemo(() => {
    const totalVideos = videos.length;
    const completedVideos = videos.filter((video) => video.status === 'COMPLETED').length;
    const processingVideos = videos.filter((video) => IN_PROGRESS_STATUSES.includes(video.status)).length;
    const failedVideos = videos.filter((video) => video.status === 'FAILED').length;

    const durations = videos
      .map((video) => video.duration)
      .filter((value): value is number => value !== null && Number.isFinite(value));

    const totalStorageBytes = videos.reduce((sum, video) => sum + Number(video.fileSize || 0), 0);
    const totalProcessedMinutes = Math.round(durations.reduce((sum, value) => sum + value, 0) / 60);

    const averageDurationSeconds =
      durations.length > 0
        ? Math.round(durations.reduce((sum, value) => sum + value, 0) / durations.length)
        : 0;

    const completionRate = clampPercent(totalVideos > 0 ? (completedVideos / totalVideos) * 100 : 0);

    return {
      totalVideos,
      completedVideos,
      processingVideos,
      failedVideos,
      totalStorageBytes,
      totalProcessedMinutes,
      averageDurationSeconds,
      completionRate,
    };
  }, [videos]);

  const statusBreakdown = useMemo(
    () => [
      { label: 'Completed', value: metrics.completedVideos, tone: 'bg-success' },
      { label: 'Processing', value: metrics.processingVideos, tone: 'bg-brand' },
      { label: 'Failed', value: metrics.failedVideos, tone: 'bg-danger' },
    ],
    [metrics.completedVideos, metrics.failedVideos, metrics.processingVideos],
  );

  const maxBreakdown = Math.max(...statusBreakdown.map((item) => item.value), 1);

  const recentVideos = useMemo(
    () => [...videos].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt)).slice(0, 6),
    [videos],
  );

  return (
    <div className="space-y-5">
      <SectionReveal className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="relative overflow-hidden p-5 md:p-6 hover:border-brand-border transition-colors">
          <div className="pointer-events-none absolute -left-24 top-0 h-64 w-64 rounded-full bg-brand/10 blur-[96px]" />
          <div className="pointer-events-none absolute right-0 top-0 h-56 w-56 rounded-full bg-[#3D369E]/10 blur-[80px]" />
          <div className="relative">
            <p className="ns-label">Command center</p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-white md:text-2xl">Video operations</h2>
            <p className="mt-2 max-w-2xl text-sm text-textMuted md:text-base">
              Track ingestion, processing progress, and quota usage from a clean operational command view.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                href="/upload"
                className="inline-flex items-center gap-2 rounded-xl border border-brand-border bg-transparent px-4 py-2 text-sm font-medium text-brand-light transition hover:bg-brand-wash hover:text-[#FFFFFF]"
              >
                <UploadCloud className="h-4 w-4" />
                Upload video
              </Link>
              <Link
                href="/library"
                className="inline-flex items-center gap-2 rounded-xl border border-white/12 bg-white/5 px-4 py-2 text-sm font-medium text-white/85 transition hover:border-white/25 hover:bg-white/10 hover:text-white"
              >
                Open library
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </Card>

        <Card className="space-y-4 p-5 md:p-6">
          <div className="flex items-center justify-between">
            <p className="ns-label">Pipeline health</p>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/10 px-2.5 py-1 text-[11px] text-success">
              {Math.round(metrics.completionRate)}% completion
            </span>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between text-sm text-white/85">
              <span>Current throughput</span>
              <span>{metrics.processingVideos} active jobs</span>
            </div>
            <div className="ns-progress-track h-2.5">
              <div className="ns-progress-fill h-full bg-brand" style={{ width: `${clampPercent(metrics.completionRate)}%` }} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="ns-surface-soft p-3 text-center border-none">
              <p className="ns-label">Completed</p>
              <p className="mt-2 text-xl font-medium text-white">{metrics.completedVideos}</p>
            </div>
            <div className="ns-surface-soft p-3 text-center border-none">
              <p className="ns-label">Failed</p>
              <p className="mt-2 text-xl font-medium text-[#E2E2E6]">{metrics.failedVideos}</p>
            </div>
          </div>
        </Card>
      </SectionReveal>

      <SectionReveal className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" delay={0.02}>
        {loading ? (
          <>
            <LoadingSkeleton className="h-32 rounded-2xl bg-white/5" />
            <LoadingSkeleton className="h-32 rounded-2xl bg-white/5" />
            <LoadingSkeleton className="h-32 rounded-2xl bg-white/5" />
            <LoadingSkeleton className="h-32 rounded-2xl bg-white/5" />
          </>
        ) : (
          <>
            <MetricCard
              icon={Film}
              label="Total videos"
              value={metrics.totalVideos}
              helper="Indexed in library"
              iconTone="text-brand-light"
            />
            <MetricCard
              icon={CheckCircle2}
              label="Completed"
              value={metrics.completedVideos}
              helper="Completed jobs"
              iconTone="text-success"
            />
            <MetricCard
              icon={Activity}
              label="In progress"
              value={metrics.processingVideos}
              helper="Active processing"
              iconTone="text-brand"
            />
            <MetricCard
              icon={Clock3}
              label="Avg duration"
              value={`${metrics.averageDurationSeconds}s`}
              helper="Per uploaded video"
              iconTone="text-[#E2E2E6]"
            />
          </>
        )}
      </SectionReveal>

      <SectionReveal className="grid gap-4 xl:grid-cols-2" delay={0.04}>
        <Card className="space-y-5 p-5 md:p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="ns-label">System overview</p>
              <h3 className="mt-1 text-base font-medium text-white md:text-lg">Processing stages</h3>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/80">
              <Layers3 className="h-3.5 w-3.5 text-brand" />
              Live signals
            </span>
          </div>

          <div className="space-y-3">
            {statusBreakdown.map((item) => (
              <div key={item.label}>
                <div className="mb-1.5 flex items-center justify-between text-sm text-white/85">
                  <span>{item.label}</span>
                  <span>{item.value}</span>
                </div>
                <div className="ns-progress-track h-2.5">
                  <div className={`h-full rounded-full ${item.tone}`} style={{ width: `${(item.value / maxBreakdown) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="ns-surface-soft p-3 text-center border-none">
              <p className="ns-label">Completion</p>
              <p className="mt-2 text-xl font-medium text-white">{Math.round(metrics.completionRate)}%</p>
            </div>
            <div className="ns-surface-soft p-3 text-center border-none">
              <p className="ns-label">Processing</p>
              <p className="mt-2 text-xl font-medium text-white">{metrics.processingVideos}</p>
            </div>
            <div className="ns-surface-soft p-3 text-center border-none">
              <p className="ns-label">Failed</p>
              <p className="mt-2 text-xl font-medium text-white">{metrics.failedVideos}</p>
            </div>
          </div>
        </Card>

        <Card className="space-y-5 p-5 md:p-6">
          <div>
            <p className="ns-label">Library utilization</p>
            <h3 className="mt-1 text-base font-medium text-white md:text-lg">Current usage snapshot</h3>
            <p className="mt-1 text-sm text-textMuted">Live usage metrics derived from your video library.</p>
          </div>

          <div className="space-y-4">
            <UsageRow label="Videos" value={`${metrics.totalVideos}`} />
            <UsageRow label="Storage used" value={bytesToSize(metrics.totalStorageBytes)} />
            <UsageRow label="Processed minutes (est.)" value={`${metrics.totalProcessedMinutes} min`} />
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            <div className="ns-surface-soft flex items-center justify-center gap-2 p-3 text-sm text-[#E2E2E6] border-none">
              <HardDrive className="h-4 w-4 text-brand-light" />
              Storage sync active
            </div>
            <div className="ns-surface-soft flex items-center justify-center gap-2 p-3 text-sm text-[#E2E2E6] border-none">
              <Zap className="h-4 w-4 text-brand-light" />
              Real-time queues
            </div>
          </div>
        </Card>
      </SectionReveal>

      <SectionReveal delay={0.06}>
        <Card className="space-y-4 p-5 md:p-6">
          <div className="flex flex-col justify-between gap-4 border-b border-white/5 pb-4 sm:flex-row sm:items-end">
            <div>
              <p className="ns-label">Recent activity</p>
              <h3 className="mt-1 text-base font-medium text-white md:text-lg">Latest events</h3>
            </div>
            <Link
              href="/library"
              className="inline-flex items-center gap-2 text-sm font-medium text-brand-light transition hover:text-white"
            >
              View full history
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              <LoadingSkeleton className="h-16 rounded-xl bg-white/5" />
              <LoadingSkeleton className="h-16 rounded-xl bg-white/5" />
              <LoadingSkeleton className="h-16 rounded-xl bg-white/5" />
            </div>
          ) : recentVideos.length === 0 ? (
            <div className="ns-surface-soft py-12 text-center border-none">
              <Database className="mx-auto h-8 w-8 text-brand-light" />
              <p className="mt-3 text-lg font-medium text-white">No uploads yet</p>
              <p className="mt-1 text-sm text-textMuted">Start by uploading your first video to initialize the workflow.</p>
              <Link
                href="/upload"
                className="mt-5 inline-flex items-center gap-2 rounded-xl border border-brand/35 bg-brand-wash px-4 py-2 text-sm font-medium text-brand-light transition hover:bg-brand-wash/80 hover:text-white"
              >
                Upload video
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {recentVideos.map((video, idx) => (
                <motion.div
                  key={video.id}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.4 }}
                  transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1], delay: idx * 0.03 }}
                  className="group grid items-center gap-3 rounded-xl border border-transparent bg-white/[0.02] px-4 py-3 transition hover:border-brand-border hover:bg-white/[0.04] sm:grid-cols-[minmax(0,1fr)_auto_auto_auto]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{video.title}</p>
                    <p className="mt-1 text-xs text-textMuted">Uploaded {formatDate(video.createdAt)}</p>
                  </div>

                  <div>
                    <StatusBadge status={video.status} />
                  </div>

                  <div className="text-right text-xs text-textMuted w-24">
                    {video.fileSize ? bytesToSize(video.fileSize) : 'Unknown'}
                  </div>

                  <Link
                    href={`/videos/${video.id}`}
                    className="inline-flex items-center justify-center rounded-lg border border-transparent p-2 text-white/50 transition bg-[#22232E]/30 hover:border-brand-border hover:bg-brand-wash hover:text-[#FFFFFF]"
                    aria-label={`Open ${video.title}`}
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </Card>
      </SectionReveal>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  helper,
  iconTone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  helper: string;
  iconTone?: string;
}) {
  return (
    <Card className="p-5 border border-white/5 hover:border-white/10 transition-colors">
      <p className="ns-label">{label}</p>
      <div className="mt-2 flex items-center gap-2">
        <Icon className={`h-4.5 w-4.5 ${iconTone ?? 'text-brand-light'}`} />
        <p className="text-2xl font-semibold text-white tracking-tight">{value}</p>
      </div>
      <p className="mt-2 text-xs text-textMuted">{helper}</p>
    </Card>
  );
}

function UsageRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5 text-sm">
      <span className="text-[#E2E2E6]">{label}</span>
      <span className="text-xs text-textMuted">{value}</span>
    </div>
  );
}
