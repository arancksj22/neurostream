export type User = {
  id: string;
  email: string;
  name: string;
  role: 'USER' | 'ADMIN';
  createdAt?: string;
};

export type VideoStatus =
  | 'PENDING'
  | 'UPLOADING'
  | 'UPLOADED'
  | 'QUEUED'
  | 'PROCESSING'
  | 'MEDIA_PROCESSED'
  | 'AI_PROCESSED'
  | 'INDEXED'
  | 'ANALYTICS_READY'
  | 'COMPLETED'
  | 'FAILED'
  | 'DELETED';

export type Video = {
  id: string;
  title: string;
  description: string | null;
  objectKey?: string;
  fileName: string;
  fileSize: string;
  contentType: string;
  status: VideoStatus;
  duration: number | null;
  thumbnailKey: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt?: string | null;
};

export type WorkflowLog = {
  id: string;
  serviceName: string;
  status: VideoStatus;
  message: string | null;
  createdAt: string;
};

export type VideoDetails = Video & {
  workflowLogs: WorkflowLog[];
  searchableReady: boolean;
  processedReady: boolean;
  fileUrl?: string;
};
