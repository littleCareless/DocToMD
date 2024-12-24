import { useCallback, useRef, useEffect } from "react";
import { convertFile } from "../services/api";
import { useStatusCheck } from "./useStatusCheck";
import { useFileState } from "./useFileState";
import { useDeviceId } from "./useDeviceId"; // 新增

export function useFileConversion() {
  const { files, addFiles, removeFile, updateFileStatus, clearHistory } =
    useFileState();
  const { startStatusCheck } = useStatusCheck(updateFileStatus);
  const statusCheckIntervals = useRef<Record<string, number>>({});
  const deviceId = useDeviceId(); // 获取设备ID

  const convertFiles = useCallback(async () => {
    if (!deviceId) return; // 如果没有设备ID，不执行转换

    const pendingFiles = files.filter((f) => f.status === "pending");

    for (const file of pendingFiles) {
      updateFileStatus(file.id, { status: "converting", progress: 0 });

      try {
        const result = await convertFile(file.file, deviceId); // 传递deviceId
        startStatusCheck(file.id, result.id);
      } catch (error) {
        updateFileStatus(file.id, {
          status: "error",
          progress: 0,
          error: error instanceof Error ? error.message : "Conversion failed",
        });
      }
    }
  }, [files, updateFileStatus, startStatusCheck, deviceId]);

  const retryFile = useCallback(
    async (id: string) => {
      updateFileStatus(id, {
        status: "pending",
        progress: 0,
        error: undefined,
      });
      const file = files.find((f) => f.id === id);
      if (file) {
        await convertFiles();
      }
    },
    [files, convertFiles, updateFileStatus]
  );

  const handleClearHistory = useCallback(async () => {
    if (!deviceId) {
      console.error("No device ID available");
      return;
    }
    await clearHistory(deviceId);
  }, [clearHistory, deviceId]);

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
    retryFile,
    clearHistory: handleClearHistory, // 使用包装后的方法
    deviceId, // 导出deviceId供其他组件使用
  };
}
