import { useState, useCallback, useEffect } from "react";
import type { FileWithStatus, StoredFileInfo } from "../types/file";

const STORAGE_KEY = "file_conversion_history";

export function useFileState() {
  const [files, setFiles] = useState<FileWithStatus[]>([]);

  // 从 localStorage 恢复历史记录
  useEffect(() => {
    const storedData = localStorage.getItem(STORAGE_KEY);
    if (storedData) {
      try {
        const storedFiles: StoredFileInfo[] = JSON.parse(storedData);
        const restoredFiles: FileWithStatus[] = storedFiles.map((f) => ({
          id: f.id,
          file: new File([], f.fileName), // 创建一个空文件对象
          status: f.status,
          progress: f.progress,
          taskId: f.taskId,
          // 恢复 URL
          previewUrl: f.status === 'completed' ? `/api/convert/${f.taskId}/preview` : undefined,
          downloadUrl: f.status === 'completed' ? `/api/convert/${f.taskId}/download` : undefined,
          completedAt: f.completedAt,
        }));
        setFiles(restoredFiles);

        // 清理过期的记录（可选，比如 24 小时前的记录）
        const now = Date.now();
        const filteredFiles = storedFiles.filter(
          (f) => now - f.timestamp < 24 * 60 * 60 * 1000
        );
        if (filteredFiles.length !== storedFiles.length) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(filteredFiles));
        }
      } catch (error) {
        console.error('Failed to restore conversion history:', error);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // 更新本地存储的方法
  const updateStorage = useCallback((currentFiles: FileWithStatus[]) => {
    const storageData: StoredFileInfo[] = currentFiles.map((f) => ({
      id: f.id,
      fileName: f.file.name,
      fileSize: f.file.size,
      taskId: f.taskId || "",
      status: f.status,
      progress: f.progress,
      timestamp: Date.now(),
      completedAt: f.completedAt,
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(storageData));
  }, []);

  // 添加文件的方法
  const addFiles = useCallback((newFiles: File[]) => {
    setFiles((prev) => {
      const filesWithStatus: FileWithStatus[] = newFiles.map((file) => ({
        id: Math.random().toString(36).substring(7),
        file,
        status: "pending",
        progress: 0,
      }));
      const updatedFiles = [...prev, ...filesWithStatus];
      updateStorage(updatedFiles);
      return updatedFiles;
    });
  }, [updateStorage]);

  // 更新文件状态的方法
  const updateFileStatus = useCallback(
    (id: string, updates: Partial<FileWithStatus>) => {
      setFiles((prev) => {
        const newFiles = prev.map((file) =>
          file.id === id ? { ...file, ...updates } : file
        );
        updateStorage(newFiles);
        return newFiles;
      });
    },
    [updateStorage]
  );

  // 移除文件的方法
  const removeFile = useCallback((id: string) => {
    setFiles((prev) => {
      const newFiles = prev.filter((file) => file.id !== id);
      updateStorage(newFiles);
      return newFiles;
    });
  }, [updateStorage]);

  // 添加清除历史记录的方法
  const clearHistory = useCallback(() => {
    setFiles([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return {
    files,
    addFiles,
    removeFile,
    updateFileStatus,
    clearHistory,  // 导出新方法
  };
}
