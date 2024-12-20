import React, { useState } from "react";
import { FileType, Download, Eye, X } from "lucide-react";
import type { FileWithStatus } from "../types/file";
import { downloadMarkdown, previewMarkdown } from "../services/api";

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
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Conversion Progress
                </h3>
                <ul className="divide-y divide-gray-200">
                    {files.map((file) => (
                        <li key={file.id} className="py-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center">
                                    <FileType className="w-5 h-5 text-gray-400 mr-3" />
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">
                                            {file.file.name}
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            {file.description}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    {file.status === "completed" && (
                                        <>
                                            <button
                                                onClick={() =>
                                                    handlePreview(file)
                                                }
                                                className="p-1 text-blue-600 hover:text-blue-700"
                                                title="Preview"
                                            >
                                                <Eye className="w-5 h-5" />
                                            </button>
                                            <button
                                                onClick={() =>
                                                    handleDownload(file)
                                                }
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
                                        <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
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
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col">
                        <div className="flex justify-between items-center p-4 border-b">
                            <h3 className="text-lg font-medium">Preview</h3>
                            <button
                                onClick={() => setShowPreview(false)}
                                className="text-gray-400 hover:text-gray-500"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-4 overflow-auto flex-1">
                            <pre className="whitespace-pre-wrap font-mono text-sm">
                                {previewContent}
                            </pre>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
