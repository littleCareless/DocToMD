import React from 'react';
import { FileType, X } from 'lucide-react';

interface FileListProps {
  files: File[];
  onRemove: (index: number) => void;
}

export function FileList({ files, onRemove }: FileListProps) {
  if (files.length === 0) return null;

  return (
    <div className="mt-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Selected Files</h3>
      <ul className="divide-y divide-gray-200">
        {files.map((file, index) => (
          <li key={index} className="py-3 flex items-center justify-between">
            <div className="flex items-center">
              <FileType className="w-5 h-5 text-gray-400 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
              </div>
            </div>
            <button
              onClick={() => onRemove(index)}
              className="text-gray-400 hover:text-gray-500"
            >
              <X className="w-5 h-5" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}