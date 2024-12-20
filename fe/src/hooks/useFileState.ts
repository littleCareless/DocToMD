import { useState, useCallback } from 'react';
import type { FileWithStatus } from '../types/file';

export function useFileState() {
  const [files, setFiles] = useState<FileWithStatus[]>([]);

  const addFiles = useCallback((newFiles: File[]) => {
    const filesWithStatus: FileWithStatus[] = newFiles.map(file => ({
      id: Math.random().toString(36).substring(7),
      file,
      status: 'pending',
      progress: 0
    }));
    setFiles(prev => [...prev, ...filesWithStatus]);
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles(prev => prev.filter(file => file.id !== id));
  }, []);

  const updateFileStatus = useCallback((id: string, updates: Partial<FileWithStatus>) => {
    setFiles(prev => prev.map(file => 
      file.id === id ? { ...file, ...updates } : file
    ));
  }, []);

  return {
    files,
    addFiles,
    removeFile,
    updateFileStatus
  };
}