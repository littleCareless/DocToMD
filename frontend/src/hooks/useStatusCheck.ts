import { useCallback } from "react";
import type { FileWithStatus } from "../types/file";
import {
  checkConversionStatus,
  getBatchConversionStatus,
} from "../services/api";

export function useStatusCheck(
  updateFileStatus: (id: string, updates: Partial<FileWithStatus>) => void
) {
  const startStatusCheck = useCallback(
    (fileId: string, taskId: string) => {
      const intervalId = window.setInterval(async () => {
        try {
          const status = await checkConversionStatus(taskId);

          switch (status.state) {
            case "SUCCESS":
              clearInterval(intervalId);
              updateFileStatus(fileId, {
                status: "completed",
                progress: 100,
                description: status.description,
                taskId: taskId,
                previewUrl: status.previewUrl,
                downloadUrl: status.downloadUrl,
                completedAt: Date.now(), // 添加完成时间
              });
              break;

            case "FAILURE":
              // 只有当前状态不是error时才更新为error
              updateFileStatus(fileId, {
                status: "error",
                error: status.error || "Conversion failed",
                description: status.description,
              });
              clearInterval(intervalId);
              break;

            case "PENDING":
            case "PROGRESS":
              // 只有当前状态是 converting 或 pending 时才更新进度
              updateFileStatus(fileId, {
                status: "converting",
                progress: status.progress,
                description: status.description,
              });
              break;
          }
        } catch (error) {
          // 捕获到错误时不更新状态，只停止检查
          clearInterval(intervalId);
          console.error("Status check failed:", error);
        }
      }, 1000);

      return intervalId;
    },
    [updateFileStatus]
  );

  // 修改批量检查逻辑
  const checkBatchStatus = useCallback(async (taskIds: string[]) => {
    try {
      const statusMap = await getBatchConversionStatus(taskIds);

      Object.entries(statusMap).forEach(([taskId, status]) => {
        // 只针对成功的状态进行更新
        if (status.state === "SUCCESS") {
          const updates: Partial<FileWithStatus> = {
            status: "completed",
            progress: 100,
            previewUrl: status.previewUrl,
            downloadUrl: status.downloadUrl,
            description: status.description,
          };
          document.dispatchEvent(
            new CustomEvent("updateFileStatus", {
              detail: { taskId, updates },
            })
          );
        }
      });
    } catch (error) {
      console.error("Failed to check batch status:", error);
    }
  }, []);

  return { startStatusCheck, checkBatchStatus };
}
