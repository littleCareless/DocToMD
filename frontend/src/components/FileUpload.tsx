import React, { useCallback } from "react";
import { Upload, FileType, AlertCircle } from "lucide-react";

interface FileUploadProps {
    onFilesSelected: (files: File[]) => void;
}

const ACCEPTED_TYPES = {
    "application/pdf": "PDF",
    "application/vnd.ms-powerpoint": "PowerPoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        "PowerPoint",
    "application/msword": "Word",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        "Word",
    "application/vnd.ms-excel": "Excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        "Excel",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "audio/mpeg": "MP3",
    "audio/wav": "WAV",
    "text/html": "HTML",
    "text/csv": "CSV",
    "application/json": "JSON",
    "application/xml": "XML",
    "text/xml": "XML",
    "application/zip": "ZIP",
};

export function FileUpload({ onFilesSelected }: FileUploadProps) {
    const handleDrop = useCallback(
        (e: React.DragEvent<HTMLDivElement>) => {
            e.preventDefault();
            const files = Array.from(e.dataTransfer.files);
            onFilesSelected(files);
        },
        [onFilesSelected]
    );

    const handleFileInput = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const files = e.target.files ? Array.from(e.target.files) : [];
            onFilesSelected(files);
        },
        [onFilesSelected]
    );

    return (
        <div
            className="w-full p-8 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
        >
            <div className="flex flex-col items-center justify-center gap-4">
                <Upload className="w-12 h-12 text-gray-400" />
                <div className="text-center">
                    <p className="text-lg font-medium text-gray-700">
                        Drag and drop files here, or click to select
                    </p>
                    <p className="mt-1 text-sm text-gray-500">
                        Supports PDF, PPT, Word, Excel, Images, Audio, and more
                    </p>
                </div>
                <input
                    type="file"
                    multiple
                    className="hidden"
                    onChange={handleFileInput}
                    accept={Object.keys(ACCEPTED_TYPES).join(",")}
                    id="file-upload"
                />
                <label
                    htmlFor="file-upload"
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 cursor-pointer"
                >
                    Select Files
                </label>
            </div>
        </div>
    );
}
