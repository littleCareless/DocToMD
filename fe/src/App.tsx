import React from 'react';
import { FileUpload } from './components/FileUpload';
import { ConversionProgress } from './components/ConversionProgress';
import { FileText } from 'lucide-react';
import { useFileConversion } from './hooks/useFileConversion';

function App() {
  const { files, addFiles, convertFiles, retryFile } = useFileConversion();

  const handleConvert = async () => {
    await convertFiles();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <FileText className="w-12 h-12 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">
            File to Markdown Converter
          </h1>
          <p className="mt-2 text-gray-600">
            Convert various file formats to Markdown with ease
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <FileUpload onFilesSelected={addFiles} />
          <ConversionProgress files={files} onRetry={retryFile} />
          
          {files.some(f => f.status === 'pending') && (
            <div className="mt-6">
              <button
                onClick={handleConvert}
                className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Convert to Markdown
              </button>
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Supported formats: PDF, PPT, Word, Excel, Images, Audio, HTML, CSV, JSON, XML, ZIP</p>
        </div>
      </div>
    </div>
  );
}

export default App;