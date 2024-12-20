from flask import Flask, request, jsonify, send_file
from markitdown import MarkItDown
import os
from dotenv import load_dotenv
import logging
from celery import Celery
from openai import OpenAI
from werkzeug.utils import secure_filename
from flask_cors import CORS
from celery.result import AsyncResult
import httpx
import time

# 确保在最开始就加载环境变量
load_dotenv()

# 添加调试输出
print("=== Environment Variables ===")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
print(f"CELERY_BROKER_URL: {os.getenv('CELERY_BROKER_URL')}")
print(f"CELERY_RESULT_BACKEND: {os.getenv('CELERY_RESULT_BACKEND')}")
print("==========================")

# 测试 OpenAI API 连接
print("\n=== Testing OpenAI API Connection ===")
try:
    response = httpx.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        timeout=10.0
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}...")  # 只打印前200个字符
    if response.status_code == 200:
        print("Successfully connected to OpenAI API")
    else:
        print(f"Failed to connect to OpenAI API: {response.text}")
except Exception as e:
    print(f"Error connecting to OpenAI API: {e}")
print("==========================\n")

# 验证环境变量是否存在
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Create app factory function
def create_app():
    app = Flask(__name__)
    
    # 设置最大上传文件大小为 1GB
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
    
    # 配置 CORS，允许所有来源
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })
    
    # 配置 Celery
    app.config.update(
        CELERY_BROKER_URL=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        CELERY_RESULT_BACKEND=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    
    return app

# Create the app instance
app = create_app()

# Configure Celery
celery = Celery(
    app.name,
    broker=app.config['CELERY_BROKER_URL'],
    backend=app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client for LLM functionality
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    timeout=httpx.Timeout(60.0),  # 置较长的超时时间
    max_retries=3,  # 添加重试次数
)

# Initialize MarkItDown with the OpenAI client
md = MarkItDown(
    llm_client=client,
    llm_model="gpt-4-turbo-preview"
)

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
MARKDOWN_FOLDER = os.path.join(os.getcwd(), 'markdown_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MARKDOWN_FOLDER, exist_ok=True)

# Supported file extensions (根据 MarkItDown 文档)
SUPPORTED_EXTENSIONS = (
    # Documents
    '.pdf', '.pptx', '.docx', '.xlsx',
    # Images
    '.jpg', '.jpeg', '.png',
    # Audio
    '.mp3', '.wav',
    # Text-based formats
    '.html', '.csv', '.json', '.xml',
    # Archives
    '.zip'
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in [ext.lstrip('.') for ext in SUPPORTED_EXTENSIONS]

@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Start async conversion task
    task = convert_file.delay(filepath)
    
    return jsonify({
        'message': 'File uploaded successfully, conversion in progress.',
        'id': task.id
    }), 202

@app.route('/api/status/<task_id>')
def get_status(task_id):
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'progress': 0,
            'description': 'Task is waiting for execution'
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'progress': 100,
            'description': 'Conversion completed',
            'preview_url': f'/api/convert/{task_id}/preview',
            'download_url': f'/api/convert/{task_id}/download'
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'progress': 0,
            'description': 'Conversion failed',
            'error': str(task.info)
        }
    else:
        response = {
            'state': task.state,
            'progress': task.info.get('progress', 0) if task.info else 0,
            'description': 'Converting file...'
        }
    
    return jsonify(response)

@app.route('/api/convert/<task_id>/preview')
def preview_file(task_id):
    task = AsyncResult(task_id)
    
    if task.state != 'SUCCESS':
        return jsonify({'error': 'Conversion not completed'}), 400
    
    if not task.info or 'markdown_path' not in task.info:
        return jsonify({'error': 'Markdown file not found'}), 404
    
    try:
        with open(task.info['markdown_path'], 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            'content': content,
            'filename': os.path.basename(task.info['markdown_path'])
        })
    except Exception as e:
        logger.error(f"Error reading markdown file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert/<task_id>/download')
def download_file(task_id):
    task = AsyncResult(task_id)
    
    if task.state != 'SUCCESS':
        return jsonify({'error': 'Conversion not completed'}), 400
    
    if not task.info or 'markdown_path' not in task.info:
        return jsonify({'error': 'Markdown file not found'}), 404
    
    return send_file(
        task.info['markdown_path'],
        as_attachment=True,
        download_name=os.path.basename(task.info['markdown_path'])
    )

@celery.task(bind=True)
def convert_file(self, filepath):
    try:
        logger.info(f"Starting conversion for file: {filepath}")
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            raise Exception("File not found")
        
        # 更新任务进度为10%
        self.update_state(state='PROGRESS', meta={'progress': 10})
        
        # 先尝试使用 MarkItDown 转换
        logger.info("Attempting conversion with MarkItDown...")
        result = md.convert(filepath)
        content = result.text_content
        logger.debug(f"Initial conversion result: {content[:200]}...")
        
        # 检查内容
        if not content or len(content.strip()) == 0:
            logger.warning("MarkItDown returned empty content")
            
        # 如果检测到返回的是元数据，尝试使用其他方法处理
        if content.startswith('Document generated by Anna'):
            file_extension = os.path.splitext(filepath)[1].lower()
            logger.info(f"Detected metadata, trying alternative method for {file_extension}")
            
            if file_extension == '.pdf':
                try:
                    logger.info("Using pdfplumber for PDF extraction...")
                    import pdfplumber
                    
                    with pdfplumber.open(filepath) as pdf:
                        content = ''
                        total_pages = len(pdf.pages)
                        logger.info(f"PDF has {total_pages} pages")
                        
                        for i, page in enumerate(pdf.pages):
                            logger.info(f"Processing page {i+1}/{total_pages}")
                            # 更新进度
                            progress = 10 + (40 * i / total_pages)
                            self.update_state(state='PROGRESS', meta={'progress': progress})
                            
                            # 提取文本
                            text = page.extract_text()
                            if text:
                                content += text + '\n\n'
                            else:
                                logger.warning(f"No text extracted from page {i+1}")
                            
                            # 提取表格
                            tables = page.extract_tables()
                            if tables:
                                logger.info(f"Found {len(tables)} tables on page {i+1}")
                                content += f"\n### Tables from page {i+1}\n\n"
                                for table in tables:
                                    content += '| ' + ' | '.join(str(cell) for cell in table[0]) + ' |\n'
                                    content += '| ' + ' | '.join(['---'] * len(table[0])) + ' |\n'
                                    for row in table[1:]:
                                        content += '| ' + ' | '.join(str(cell) for cell in row) + ' |\n'
                                    content += '\n'
                    
                    logger.info("PDF extraction completed")
                    
                    # 检查提取的内容
                    if not content.strip():
                        logger.warning("PDF extraction resulted in empty content")
                    else:
                        logger.info(f"Extracted content length: {len(content)}")
                
                except Exception as e:
                    logger.error(f"Error in PDF extraction: {str(e)}", exc_info=True)
                    content = result.text_content
            
            elif file_extension == '.zip':
                try:
                    logger.info("Detected metadata in ZIP result, trying direct extraction...")
                    import zipfile
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        # 获取所有文本文件
                        text_files = [f for f in zip_ref.namelist() if f.endswith('.txt')]
                        content = ''
                        for txt_file in text_files:
                            with zip_ref.open(txt_file) as f:
                                content += f.read().decode('utf-8', errors='ignore') + '\n\n'
                        
                        if not content.strip():
                            # 如果没有找到文本文件，尝试其他类型的文件
                            for f in zip_ref.namelist():
                                if not f.endswith(('.jpg', '.png', '.gif')):  # 跳过图片文件
                                    try:
                                        with zip_ref.open(f) as file:
                                            content += f'# {f}\n\n'
                                            content += file.read().decode('utf-8', errors='ignore') + '\n\n'
                                    except:
                                        continue
                    logger.info("Successfully extracted ZIP content")
                except Exception as e:
                    logger.error(f"Error extracting ZIP content: {e}")
                    # 如果提取失败，保留原始内容
                    content = result.text_content
        
        # 最终检查内容
        if not content or len(content.strip()) == 0:
            logger.error("No content extracted from file")
            raise Exception("Failed to extract content from file")
        
        # 存为markdown文件
        filename = os.path.splitext(os.path.basename(filepath))[0] + '.md'
        markdown_path = os.path.join(MARKDOWN_FOLDER, filename)
        logger.info(f"Writing content to {markdown_path}")
        
        # 写入文件
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 清理原始文件
        try:
            os.remove(filepath)
            logger.info(f"Successfully removed original file: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to remove original file {filepath}: {e}")
        
        return {
            'status': 'success',
            'markdown_path': markdown_path
        }
        
    except Exception as e:
        logger.error(f"Error processing file {filepath}: {e}", exc_info=True)
        # 清理文件
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up file {filepath}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up file {filepath}: {cleanup_error}")
        raise Exception(str(e))

@app.route('/')
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
