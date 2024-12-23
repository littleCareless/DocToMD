import React, { useState, useEffect, useRef } from "react";
import { FileType, Download, Eye, X, Clock } from "lucide-react";
import type { FileWithStatus } from "../types/file";
import { downloadMarkdown, previewMarkdown } from "../services/api";
import { formatDate } from "../utils/date"; // 新增工具函数

interface ConversionProgressProps {
  files: FileWithStatus[];
  onRetry: (id: string) => void;
}

export function ConversionProgress({
  files,
  onRetry,
}: ConversionProgressProps) {
  const [previewContent, setPreviewContent] = useState<string>("");
  const [showPreview, setShowPreview] = useState(false);
  const [elapsedTime, setElapsedTime] = useState<string>("00:00:00");
  const workerRef = useRef<Worker | null>(null);
  const timerStartedRef = useRef<boolean>(false);

  useEffect(() => {
    // 创建 Web Worker
    workerRef.current = new Worker(
      new URL("../workers/timer.worker.ts", import.meta.url)
    );

    // 监听 Worker 消息
    workerRef.current.onmessage = (e) => {
      setElapsedTime(e.data.formatted);
    };

    return () => {
      if (workerRef.current) {
        workerRef.current.postMessage("stop");
        workerRef.current.terminate();
      }
    };
  }, []);

  useEffect(() => {
    const hasConverting = files.some((f) => f.status === "converting");
    const allCompleted = files.every((f) =>
      ["completed", "error"].includes(f.status)
    );

    if (hasConverting && !timerStartedRef.current) {
      // 只有在没有启动过计时器的情况下才启动
      workerRef.current?.postMessage("start");
      timerStartedRef.current = true;
    } else if (allCompleted && timerStartedRef.current) {
      // 只有在计时器已经启动的情况下才停止
      workerRef.current?.postMessage("stop");
      timerStartedRef.current = false;
    }
  }, [files]);

  const handleDownload = async (file: FileWithStatus) => {
    if (file.taskId) {
      await downloadMarkdown(file.taskId, file.file.name);
    }
  };

  const handlePreview = async (file: FileWithStatus) => {
    if (file.taskId) {
      try {
        const { content } = await previewMarkdown(file.taskId);
        setPreviewContent(content);
        setShowPreview(true);
      } catch (error) {
        console.error("Preview failed:", error);
      }
    }
  };

  return (
    <>
      <div className="mt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            Conversion Progress
          </h3>
          {files.some(
            (f) => f.status === "converting" || f.status === "completed"
          ) && (
            <div className="flex items-center text-sm text-gray-500">
              <Clock className="w-4 h-4 mr-1" />
              <span>{elapsedTime}</span>
            </div>
          )}
        </div>
        <ul className="divide-y divide-gray-200">
          {files.map((file) => (
            <li
              key={file.id}
              className="py-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <FileType className="w-5 h-5 mr-3 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {file.file.name}
                    </p>
                    <p className="text-sm text-gray-500">{file.description}</p>
                    {file.completedAt && (
                      <p className="text-xs text-gray-400">
                        完成于: {formatDate(file.completedAt)}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {file.status === "completed" && (
                    <>
                      <button
                        onClick={() => handlePreview(file)}
                        className="p-1 text-blue-600 hover:text-blue-700"
                        title="Preview"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDownload(file)}
                        className="p-1 text-green-600 hover:text-green-700"
                        title="Download"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </>
                  )}
                  {file.status === "error" && (
                    <button
                      onClick={() => onRetry(file.id)}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      Retry
                    </button>
                  )}
                  {file.status === "converting" && (
                    <div className="w-5 h-5 border-2 border-blue-600 rounded-full border-t-transparent animate-spin" />
                  )}
                </div>
              </div>
              {file.status === "converting" && (
                <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${file.progress}%` }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-medium">Preview</h3>
              <button
                onClick={() => setShowPreview(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 p-4 overflow-auto">
              <pre className="font-mono text-sm whitespace-pre-wrap">
                {previewContent}
              </pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
