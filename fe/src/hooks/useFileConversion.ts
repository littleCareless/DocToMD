import { useCallback, useRef, useEffect } from 'react';
// import type { FileWithStatus } from '../types/file';
import { convertFile } from '../services/api';
import { useStatusCheck } from './useStatusCheck';
import { useFileState } from './useFileState';

export function useFileConversion() {
  const { files, addFiles, removeFile, updateFileStatus } = useFileState();
  const { startStatusCheck } = useStatusCheck(updateFileStatus);
  const statusCheckIntervals = useRef<Record<string, number>>({});

  const convertFiles = useCallback(async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');

    for (const file of pendingFiles) {
      updateFileStatus(file.id, { status: 'converting', progress: 0 });

      try {
        const result = await convertFile(file.file);
        startStatusCheck(file.id, result.id);
      } catch (error) {
        updateFileStatus(file.id, {
          status: 'error',
          progress: 0,
          error: error instanceof Error ? error.message : 'Conversion failed'
        });
      }
    }
  }, [files, updateFileStatus, startStatusCheck]);

  const retryFile = useCallback(async (id: string) => {
    updateFileStatus(id, { status: 'pending', progress: 0, error: undefined });
    const file = files.find(f => f.id === id);
    if (file) {
      await convertFiles();
    }
  }, [files, convertFiles, updateFileStatus]);

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(statusCheckIntervals.current).forEach(clearInterval);
    };
  }, []);

  return {
    files,
    addFiles,
    removeFile,
    convertFiles,
    retryFile
  };
}
