export interface FileWithStatus {
  id: string;
  file: File;
  status: 'pending' | 'converting' | 'completed' | 'error';
  progress: number;
  error?: string;
  taskId?: string;
  previewUrl?: string;
  downloadUrl?: string;
  description?: string;
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