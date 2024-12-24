import base64
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
import pytesseract
from pdf2image import convert_from_path
import tempfile
import cv2
import numpy as np
import hashlib
import json
from pathlib import Path
from paddleocr import PaddleOCR
import io
from PIL import Image

# 确保在最开始就加载环境变量
load_dotenv()

# 添加调试输出
print("=== Environment Variables ===")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')}")  # 添加这行
print(f"CELERY_BROKER_URL: {os.getenv('CELERY_BROKER_URL')}")
print(f"CELERY_RESULT_BACKEND: {os.getenv('CELERY_RESULT_BACKEND')}")
print(f"OPENAI_LLM_MODEL: {os.getenv('OPENAI_LLM_MODEL', 'glm-4v-flash')}")
print("==========================")

# 测试 OpenAI API 连接
print("\n=== Testing OpenAI API Connection ===")
base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
try:
    response = httpx.get(
        base_url,
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

logger.info(f"Initializing OpenAI client with base_url: {base_url}")
client = OpenAI(
    base_url=base_url,
    api_key=os.getenv('OPENAI_API_KEY'),

    timeout=httpx.Timeout(60.0),  # 置较长的超时时间
    max_retries=3,  # 添加重试次数
)

# Initialize MarkItDown with the OpenAI client
md = MarkItDown(
    llm_client=client,
    llm_model=os.getenv('OPENAI_LLM_MODEL', 'text-davinci-003'),
)

# 配置文件夹
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
MARKDOWN_FOLDER = os.path.join(os.getcwd(), 'markdown_files')
DEBUG_FOLDER = os.path.join(os.getcwd(), 'debug')  # 添加调试目录
CACHE_FOLDER = os.path.join(os.getcwd(), 'cache')
os.makedirs(CACHE_FOLDER, exist_ok=True)

# 创建必要的目录
for folder in [UPLOAD_FOLDER, MARKDOWN_FOLDER, DEBUG_FOLDER]:
    os.makedirs(folder, exist_ok=True)

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

def calculate_file_hash(file_path: str) -> str:
    """计算文件的SHA256哈希值"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_cached_result(file_hash: str) -> dict | None:
    """获取缓存的转换结果"""
    cache_file = os.path.join(CACHE_FOLDER, f"{file_hash}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            # 验证缓存的文件是否存在
            if os.path.exists(cache_data['markdown_path']):
                return cache_data
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
    return None

def save_cache_result(file_hash: str, result: dict):
    """保存转换结果到缓存"""
    cache_file = os.path.join(CACHE_FOLDER, f"{file_hash}.json")
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

# 修改文件夹结构，加入设备ID
def get_user_folders(device_id: str):
    """获取特定设备的文件夹路径"""
    base_folders = {
        'upload': os.path.join(UPLOAD_FOLDER, device_id),
        'markdown': os.path.join(MARKDOWN_FOLDER, device_id),
        'cache': os.path.join(CACHE_FOLDER, device_id),
    }

    # 确保所有文件夹存在
    for folder in base_folders.values():
        os.makedirs(folder, exist_ok=True)

    return base_folders

@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    device_id = request.form.get('deviceId')

    if not device_id:
        return jsonify({'error': 'No device ID provided'}), 400

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    # 获取用户特定的文件夹
    user_folders = get_user_folders(device_id)
    filepath = Path(user_folders['upload']) / secure_filename(file.filename)
    file.save(str(filepath))

    file_hash = calculate_file_hash(str(filepath))
    cache_path = os.path.join(user_folders['cache'], f"{file_hash}.json")

    # 检查用户特定的缓存
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cached_result = json.load(f)
            return jsonify({
                'message': 'File conversion completed (cached).',
                'id': file_hash
            }), 202
        except Exception:
            pass

    task = convert_file.delay(str(filepath), file_hash, device_id)
    return jsonify({
        'message': 'File uploaded successfully, conversion in progress.',
        'id': task.id
    }), 202

@app.route('/api/status/<task_id>')
def get_status(task_id):
    # 首先检查是否是缓存结果
    cached_result = get_cached_result(task_id)
    if (cached_result):
        return jsonify({
            'state': 'SUCCESS',
            'progress': 100,
            'description': 'Conversion completed (cached)',
            'preview_url': f'/api/convert/{task_id}/preview',
            'download_url': f'/api/convert/{task_id}/download'
        })

    # 如果不是缓存结果，则检查Celery任务状态
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
    # 先检查是否是缓存ID
    cached_result = get_cached_result(task_id)
    if cached_result:
        try:
            with open(cached_result['markdown_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'content': content,
                'filename': os.path.basename(cached_result['markdown_path'])
            })
        except Exception as e:
            logger.error(f"Error reading cached file: {e}")
            return jsonify({'error': str(e)}), 500

    # 如果不是缓存ID，按原来的方式处理
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
    # 先检查是否是缓存ID
    cached_result = get_cached_result(task_id)
    if cached_result:
        return send_file(
            cached_result['markdown_path'],
            as_attachment=True,
            download_name=os.path.basename(cached_result['markdown_path'])
        )

    # 如果不是缓存ID，按原来的方式处理
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

@app.route('/api/convert/clear-history', methods=['POST'])
def clear_history():
    try:
        data = request.get_json()
        task_ids = data.get('taskIds', [])
        device_id = data.get('deviceId')

        if not device_id:
            return jsonify({'error': 'No device ID provided'}), 400

        user_folders = get_user_folders(device_id)

        # 删除用户特定的文件和缓存
        for task_id in task_ids:
            # 删除缓存
            cache_file = os.path.join(user_folders['cache'], f"{task_id}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)

            # 获取并删除markdown文件
            try:
                task_result = AsyncResult(task_id)
                if task_result.successful():
                    markdown_path = task_result.info.get('markdown_path')
                    if markdown_path and os.path.exists(markdown_path):
                        os.remove(markdown_path)
            except Exception as e:
                logger.warning(f"Failed to remove file for task {task_id}: {e}")

        return jsonify({'message': 'History cleared successfully'}), 200
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({'error': str(e)}), 500

def is_valid_content(content: str) -> bool:
    """验证提取的内容是否有效"""
    # 移除空白字符后的最小有效长度
    MIN_CONTENT_LENGTH = 50

    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        return False

    # Anna's Archive 元数据特征识别
    anna_archive_indicators = [
        "Document generated by Anna",
        "Anna's Archive",
        "DuXiu collection",
        "annas-blog.org",
        "pdg_dir_name",
        "pdg_main_pages",
        "pdf_generation_missing_pages",
        '"filename_decoded"',
        '"total_pixels"',
        '"zip_password"'
    ]

    # 检查是否包含典型的JSON字段组合
    json_field_combinations = [
        ('filesize', 'md5', 'sha1'),
        ('crc32', 'uncompressed_size'),
        ('header_md5', 'sha256')
    ]

    # 计算 Anna's Archive 指标出现次数
    anna_indicators_count = sum(1 for indicator in anna_archive_indicators if indicator in content)

    # 检查 JSON 字段组合
    json_combinations_present = any(
        all(field in content for field in combination)
        for combination in json_field_combinations
    )

    # 如果包含多个 Anna's Archive 特征或特定的 JSON 字段组合，认为是元数据
    if anna_indicators_count >= 2 or json_combinations_present:
        logger.info(f"Detected Anna's Archive metadata: {anna_indicators_count} indicators, JSON fields: {json_combinations_present}")
        return False

    # 判断是否是广告或垃圾信息
    spam_keywords = [
        "开户客服微信",
        "扫描二维码",
        "手续费",
        "股票期货",
        "无门槛",
        "加微信",
        "国企证券",
        "万一",
        "开股票账户",
        "开期货账户",
        '账户',
        "加一分",
        "国企期货",
        '期货',
        "书籍下载",
        "点击网站链接",
        "二维码添加微信",
    ]

    # 计算垃圾关键词出现的次数
    spam_count = sum(1 for keyword in spam_keywords if keyword in content)
    # 如果出现超过2个关键词，认为是垃圾信息
    if (spam_count > 1):
        return False

    # 检查是否包含足够的中文字符
    chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
    if chinese_chars > 0:
        # 如果包含中文，要求中文字符至少占10%
        if chinese_chars / len(content.strip()) < 0.1:
            return False

    return True

def enhance_image_quality(image_path):
    """增强图片质量"""
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        return False

    try:
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 自适应阈值二值化
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # 降噪
        denoised = cv2.fastNlMeansDenoising(binary)

        # 提高对比度
        enhanced = cv2.convertScaleAbs(denoised, alpha=1.2, beta=0)

        # 锐化
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        # 调整亮度和对比度
        bright = cv2.convertScaleAbs(sharpened, alpha=1.1, beta=10)

        # 保存增强后的图片
        enhanced_path = image_path.replace('.png', '_enhanced.png')
        cv2.imwrite(enhanced_path, bright)

        return enhanced_path
    except Exception as e:
        logger.error(f"Image enhancement failed: {e}")
        return False

# 初始化PaddleOCR（在全局变量区域）
paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False)
logger.info("PaddleOCR initialized successfully")

def process_image_with_paddle_ocr(image_path):
    """使用PaddleOCR处理图片"""
    try:
        logger.info(f"Processing image with PaddleOCR: {image_path}")
        result = paddle_ocr.ocr(image_path, cls=True)

        if not result or not result[0]:
            logger.warning("PaddleOCR returned empty result")
            return ""

        # 提取识别的文本
        text_content = []
        for line in result[0]:
            if len(line) >= 2:  # 确保结果包含文本部分
                text_content.append(line[1][0])  # 获取识别的文本内容

        return "\n".join(text_content)
    except Exception as e:
        logger.error(f"PaddleOCR processing failed: {e}")
        return ""

@celery.task(bind=True)
def convert_file(self, filepath: str, file_hash: str, device_id: str):
    try:
        user_folders = get_user_folders(device_id)

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
        logger.info(f"Content starts with: {content[:50]}")  # 添加调试日志

        # 验证 MarkItDown 转换的内容
        valid_content = is_valid_content(content)
        logger.info(f"Content validation result: {valid_content}")  # 添加调试日志

        if not valid_content:
            logger.warning("MarkItDown content validation failed, trying OCR...")
            file_extension = os.path.splitext(filepath)[1].lower()

            if file_extension == '.pdf':
                try:
                    logger.info("Converting PDF to images for OCR processing...")
                    content = ''

                    with tempfile.TemporaryDirectory() as temp_dir:
                        # 将PDF转换为图像
                        images = convert_from_path(filepath)
                        total_images = len(images)

                        # 创建调试目录
                        debug_subdir = os.path.join(DEBUG_FOLDER, os.path.splitext(os.path.basename(filepath))[0])
                        os.makedirs(debug_subdir, exist_ok=True)
                        logger.info(f"Debug images will be saved to: {debug_subdir}")

                        for i, image in enumerate(images):
                            logger.info(f"Processing page {i+1}/{total_images}")
                            progress = 10 + (80 * i / total_images)
                            self.update_state(state='PROGRESS', meta={'progress': progress})

                            # 保存图像到临时文件和调试目录
                            temp_image = os.path.join(temp_dir, f'page_{i}.png')
                            debug_image = os.path.join(debug_subdir, f'page_{i}.png')
                            image.save(temp_image, 'PNG')
                            image.save(debug_image, 'PNG')
                            logger.info(f"Saved debug image: {debug_image}")

                            # 增强图片质量
                            enhanced_image = enhance_image_quality(temp_image)
                            if enhanced_image:
                                logger.info(f"Successfully enhanced image quality")
                                enhanced_debug = os.path.join(debug_subdir, f'page_{i}_enhanced.png')
                                import shutil
                                shutil.copy2(enhanced_image, enhanced_debug)
                                # 使用增强后的图片进行OCR
                                temp_image = enhanced_image

                            # 修改OCR处理部分
                            try:
                                logger.info("Starting multi-stage OCR process...")

                                # 1. 首先尝试Tesseract
                                logger.info("1. Attempting Tesseract OCR...")
                                tesseract_text = pytesseract.image_to_string(temp_image, lang='chi_sim+eng')

                                # 2. 尝试PaddleOCR
                                logger.info("2. Attempting PaddleOCR...")
                                paddle_text = process_image_with_paddle_ocr(temp_image)

                                # 3. 选择最佳结果
                                if is_valid_content(tesseract_text):
                                    logger.info("Using Tesseract OCR result")
                                    page_text = tesseract_text
                                elif is_valid_content(paddle_text):
                                    logger.info("Using PaddleOCR result")
                                    page_text = paddle_text
                                else:
                                    # 4. 如果两者都不理想，使用GPT-4V
                                    logger.info("Local OCR results not satisfactory, trying GPT-4V...")
                                    try:
                                        with open(temp_image, 'rb') as img_file:
                                            # GPT-4V处理代码保持不变
                                            logger.info(f"Making API request to: {client.base_url}/chat/completions")  # 添加这行
                                            with open(temp_image, 'rb') as img_file:
                                                # 记录图片大小
                                                img_file.seek(0, 2)
                                                file_size = img_file.tell()
                                                img_file.seek(0)
                                                logger.info(f"Processing image size: {file_size/1024/1024:.2f}MB")

                                                response = client.chat.completions.create(
                                                    model=os.getenv('OPENAI_LLM_MODEL', 'gpt-4-vision-preview'),
                                                    messages=[
                                                        {
                                                            "role": "user",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "请识别这个图片中的所有文字内容。如果发现表格，请转换为Markdown表格格式。请保持原始的段落结构和格式。"
                                                                },
                                                                {
                                                                    "type": "image_url",
                                                                    "image_url": {
                                                                        "url": f"data:image/png;base64,{base64.b64encode(img_file.read()).decode('utf-8')}"
                                                                    }
                                                                }
                                                            ]
                                                        }
                                                    ],
                                                )

                                                # 处理返回的文本
                                                page_text = response.choices[0].message.content
                                                logger.info(f"OCR Result Preview: {page_text[:200]}...")  # 打印前200个字符
                                                logger.info(f"OCR Result Length: {len(page_text)}")

                                                if page_text.strip():
                                                    content += f"## Page {i+1}\n\n{page_text}\n\n"
                                                else:
                                                    logger.warning(f"Empty OCR result for page {i+1}")
                                                    # 保存失败的请求信息
                                                    with open(os.path.join(debug_subdir, f'failed_request_page_{i+1}.txt'), 'w') as f:
                                                        f.write(f"Response: {response}\n")
                                                        f.write(f"Content: {page_text}")

                                    except Exception as gpt_error:
                                        logger.error(f"GPT-4V processing error: {gpt_error}")
                                        # 如果GPT-4V失败，使用Tesseract的结果
                                        page_text = tesseract_text or paddle_text or "OCR处理失败"

                                # 保存识别结果
                                if page_text.strip():
                                    content += f"## Page {i+1}\n\n{page_text}\n\n"
                                    # 保存调试信息
                                    debug_info = {
                                        'tesseract_result': tesseract_text,
                                        'paddle_result': paddle_text,
                                        'final_result': page_text
                                    }
                                    with open(os.path.join(debug_subdir, f'ocr_debug_page_{i+1}.json'), 'w', encoding='utf-8') as f:
                                        json.dump(debug_info, f, ensure_ascii=False, indent=2)
                                else:
                                    logger.warning(f"Empty OCR result for page {i+1}")

                            except Exception as ocr_error:
                                logger.error(f"OCR processing error on page {i+1}: {ocr_error}")
                                with open(os.path.join(debug_subdir, f'error_log_page_{i+1}.txt'), 'w') as f:
                                    f.write(f"Error: {str(ocr_error)}\n")
                                continue

                    # 检查最终结果
                    if content.strip():
                        logger.info(f"Total extracted content length: {len(content)}")
                        logger.info("Content preview:")
                        logger.info(content[:500])  # 打印前500个字符
                    else:
                        logger.error("No content extracted from OCR")
                        raise Exception("No content extracted from PDF via OCR")

                    # 保存完整的OCR结果用于调试
                    with open(os.path.join(debug_subdir, 'full_ocr_result.txt'), 'w', encoding='utf-8') as f:
                        f.write(content)

                except Exception as e:
                    logger.error(f"Error in PDF processing: {str(e)}", exc_info=True)
                    raise Exception(f"PDF processing failed: {str(e)}")

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
        source_path = Path(filepath)
        filename = f"{source_path.stem}.md"  # 保留完整的文件名
        markdown_path = os.path.join(user_folders['markdown'], filename)
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

        result = {
            'status': 'success',
            'markdown_path': markdown_path
        }

        # 保存结果到用户特定的缓存
        cache_path = os.path.join(user_folders['cache'], f"{file_hash}.json")
        save_cache_result(cache_path, result)

        return result

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
