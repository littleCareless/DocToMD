import { useCallback } from 'react';
import type { FileWithStatus } from '../types/file';
import { checkConversionStatus } from '../services/api';

export function useStatusCheck(
  updateFileStatus: (id: string, updates: Partial<FileWithStatus>) => void
) {
  const startStatusCheck = useCallback((fileId: string, taskId: string) => {
    const intervalId = window.setInterval(async () => {
      try {
        const status = await checkConversionStatus(taskId);

        switch (status.state) {
          case 'SUCCESS':
            clearInterval(intervalId);
            updateFileStatus(fileId, {
              status: 'completed',
              progress: 100,
              description: status.description,
              taskId: taskId,
              previewUrl: status.previewUrl,
              downloadUrl: status.downloadUrl,
              completedAt: Date.now() // 添加完成时间
            });
            break;

          case 'FAILURE':
            clearInterval(intervalId);
            updateFileStatus(fileId, {
              status: 'error',
              error: status.error || 'Conversion failed',
              description: status.description
            });
            break;

          case 'PENDING':
          case 'PROGRESS':
            updateFileStatus(fileId, {
              status: 'converting',
              progress: status.progress,
              description: status.description
            });
            break;
        }
      } catch (error) {
        clearInterval(intervalId);
        updateFileStatus(fileId, {
          status: 'error',
          error: error instanceof Error ? error.message : 'Status check failed'
        });
      }
    }, 1000);

    return intervalId;
  }, [updateFileStatus]);

  return { startStatusCheck };
}
