export interface FileWithStatus {
  id: string;
  file: File;
  status: "pending" | "converting" | "completed" | "error";
  progress: number;
  taskId?: string;
  description?: string;
  error?: string;
  previewUrl?: string;
  downloadUrl?: string;
  completedAt?: number;
}

export interface StoredFileInfo {
  id: string;
  fileName: string;
  fileSize: number;
  taskId: string;
  status: "pending" | "converting" | "completed" | "error";
  progress: number;
  timestamp: number;
  previewUrl?: string;
  downloadUrl?: string;
  error?: string;
  completedAt?: number;
}

export interface ConversionResult {
  id: string;
  message: string;
}

export interface ConversionStatus {
  state: string;
  progress: number;
  description: string;
  previewUrl?: string;
  downloadUrl?: string;
  error?: string;
}
