import { API_ENDPOINTS } from '../config/api';
import type { ConversionResult, ConversionStatus } from '../types/file';

export async function convertFile(file: File): Promise<ConversionResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(API_ENDPOINTS.convert, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Conversion failed');
  }

  const result = await response.json();
  return {
    id: result.id,
    message: result.message
  };
}

export async function checkConversionStatus(taskId: string): Promise<ConversionStatus> {
  const response = await fetch(`${API_ENDPOINTS.status}/${taskId}`);

  if (!response.ok) {
    throw new Error('Failed to fetch conversion status');
  }

  const result = await response.json();
  return {
    state: result.state,
    progress: result.progress,
    description: result.description,
    previewUrl: result.preview_url,
    downloadUrl: result.download_url,
    error: result.error
  };
}

export async function previewMarkdown(taskId: string): Promise<{ content: string; filename: string }> {
  const response = await fetch(`${API_ENDPOINTS.convert}/${taskId}/preview`);

  if (!response.ok) {
    throw new Error('Failed to preview file');
  }

  return response.json();
}

export async function downloadMarkdown(taskId: string, filename: string) {
  const response = await fetch(`${API_ENDPOINTS.convert}/${taskId}/download`);
  if (!response.ok) {
    throw new Error('Failed to download file');
  }

  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename.replace(/\.[^/.]+$/, '') + '.md';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(downloadUrl);
}
