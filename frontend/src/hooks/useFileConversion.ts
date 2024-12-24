import { useState, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { convertFile, clearConversionHistory } from "../services/api";
import { useStatusCheck } from "./useStatusCheck";
import { useDeviceId } from "./useDeviceId";
import type { FileWithStatus } from "../types/file";

const STORAGE_KEY = "file_conversion_history";

export function useFileConversion() {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const deviceId = useDeviceId();
  // 只保存必要的状态信息到localStorage
  const saveToLocalStorage = useCallback((updatedFiles: FileWithStatus[]) => {
    try {
      const storageData = updatedFiles.map((file) => ({
        id: file.id,
        taskId: file.taskId,
        status: file.status,
        progress: file.progress,
        description: file.description,
        error: file.error,
        previewUrl: file.previewUrl,
        downloadUrl: file.downloadUrl,
        completedAt: file.completedAt,
        fileName: file.file.name,
      }));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(storageData));
    } catch (error) {
      console.error("Failed to save conversion history:", error);
    }
  }, []);
  // 修改现有的状态更新函数，添加存储逻辑
  const updateFileStatus = useCallback(
    (id: string, updates: Partial<FileWithStatus>) => {
      setFiles((prevFiles) => {
        const newFiles = prevFiles.map((file) =>
          file.id === id ? { ...file, ...updates } : file
        );
        saveToLocalStorage(newFiles);
        return newFiles;
      });
    },
    [saveToLocalStorage]
  );
  const { startStatusCheck, checkBatchStatus } =
    useStatusCheck(updateFileStatus);

  // 修改从localStorage恢复状态的逻辑
  useEffect(() => {
    const storedData = localStorage.getItem(STORAGE_KEY);
    if (storedData) {
      try {
        const historyData = JSON.parse(storedData);
        const restoredFiles: FileWithStatus[] = historyData.map(
          (item: any) => ({
            id: item.id,
            taskId: item.taskId,
            status: item.status,
            progress: item.progress,
            description: item.description,
            error: item.error,
            previewUrl: item.previewUrl,
            downloadUrl: item.downloadUrl,
            completedAt: item.completedAt,
            file: new File([], item.fileName),
          })
        );

        setFiles(restoredFiles);

        // 只对未完成且没有错误的任务恢复状态检查
        const ongoingTasks = restoredFiles.filter(
          (file) => file.status === "converting" && !file.error
        );

        ongoingTasks.forEach((file) => {
          if (file.taskId) {
            startStatusCheck(file.id, file.taskId);
          }
        });
      } catch (error) {
        console.error("Failed to restore conversion history:", error);
      }
    }
  }, [deviceId, startStatusCheck]);

  // 确保文件状态改变时保存到localStorage
  useEffect(() => {
    if (files.length > 0) {
      saveToLocalStorage(files);
    }
  }, [files, saveToLocalStorage]);

  const addFiles = useCallback((newFiles: File[]) => {
    const fileItems: FileWithStatus[] = newFiles.map((file) => ({
      id: uuidv4(),
      file,
      status: "pending",
      progress: 0,
      description: "等待转换...",
    }));
    setFiles((prev) => [...prev, ...fileItems]);
  }, []);

  const convertFiles = useCallback(async () => {
    const pendingFiles = files.filter((f) => f.status === "pending");

    for (const file of pendingFiles) {
      updateFileStatus(file.id, {
        status: "converting",
        description: "开始转换...",
      });

      try {
        const result = await convertFile(file.file, deviceId);
        updateFileStatus(file.id, { taskId: result.id });
        startStatusCheck(file.id, result.id);
      } catch (error) {
        updateFileStatus(file.id, {
          status: "error",
          error: error instanceof Error ? error.message : "转换失败",
        });
      }
    }
  }, [files, deviceId, startStatusCheck, updateFileStatus]);

  const retryFile = useCallback(
    async (fileId: string) => {
      const file = files.find((f) => f.id === fileId);
      if (!file) return;

      updateFileStatus(fileId, {
        status: "converting",
        progress: 0,
        error: undefined,
        description: "重新开始转换...",
      });

      try {
        const result = await convertFile(file.file, deviceId);
        updateFileStatus(fileId, { taskId: result.id });
        startStatusCheck(fileId, result.id);
      } catch (error) {
        updateFileStatus(fileId, {
          status: "error",
          error: error instanceof Error ? error.message : "转换失败",
        });
      }
    },
    [files, deviceId, startStatusCheck, updateFileStatus]
  );

  const clearHistory = useCallback(async () => {
    if (files.length === 0) return;

    const taskIds = files
      .filter((f) => f.taskId)
      .map((f) => f.taskId as string);

    if (taskIds.length > 0) {
      await clearConversionHistory(taskIds, deviceId);
    }

    setFiles([]);
    localStorage.removeItem(STORAGE_KEY);
  }, [files, deviceId]);

  return {
    files,
    addFiles,
    convertFiles,
    retryFile,
    clearHistory,
    updateFileStatus,
  };
}
