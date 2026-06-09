"""
大纲生成相关 API 路由

包含功能：
- 生成大纲（支持图片上传）
"""

import time
import base64
import logging
from flask import Blueprint, request, jsonify
from backend.auth import require_user
from backend.services.outline import get_outline_service
from .utils import log_request, log_error

logger = logging.getLogger(__name__)


def create_outline_blueprint():
    """创建大纲路由蓝图（工厂函数，支持多次调用）"""
    outline_bp = Blueprint('outline', __name__)

    @outline_bp.route('/outline', methods=['POST'])
    @require_user()
    def generate_outline(_current_user):
        """
        生成大纲（支持图片上传）

        请求格式：
        1. multipart/form-data（带图片文件）
           - topic: 主题文本
           - images: 图片文件列表

        2. application/json（无图片或 base64 图片）
           - topic: 主题文本
           - images: base64 编码的图片数组（可选）

        返回：
        - success: 是否成功
        - outline: 原始大纲文本
        - pages: 解析后的页面列表
        """
        start_time = time.time()

        try:
            # 解析请求数据
            topic, images, page_count = _parse_outline_request()

            log_request('/outline', {'topic': topic, 'images': images, 'page_count': page_count})

            # 验证必填参数
            if not topic:
                logger.warning("大纲生成请求缺少 topic 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
                }), 400

            # 调用大纲生成服务
            logger.info(f"🔄 开始生成大纲，主题: {topic[:50]}...")
            outline_service = get_outline_service()
            result = outline_service.generate_outline(topic, images if images else None, page_count=page_count)

            # 记录结果
            elapsed = time.time() - start_time
            if result["success"]:
                logger.info(f"✅ 大纲生成成功，耗时 {elapsed:.2f}s，共 {len(result.get('pages', []))} 页")
                return jsonify(result), 200
            else:
                logger.error(f"❌ 大纲生成失败: {result.get('error', '未知错误')}")
                return jsonify(result), 500

        except Exception as e:
            log_error('/outline', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"大纲生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    @outline_bp.route('/topics', methods=['POST'])
    @require_user()
    def generate_topic_ideas(_current_user):
        """
        基于同一个话题生成多个不同作品方向。

        请求体：
        - topic: 原始话题
        - count: 生成数量，默认 5
        """
        try:
            data = request.get_json() or {}
            topic = data.get('topic', '').strip()
            count = int(data.get('count', 5))

            log_request('/topics', {'topic': topic, 'count': count})

            if not topic:
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。"
                }), 400

            outline_service = get_outline_service()
            result = outline_service.generate_topic_ideas(topic, count=count)
            return jsonify(result), 200 if result["success"] else 500

        except Exception as e:
            log_error('/topics', e)
            return jsonify({
                "success": False,
                "error": f"选题方案生成异常。\n错误详情: {str(e)}"
            }), 500

    return outline_bp


def _parse_outline_request():
    """
    解析大纲生成请求

    支持两种格式：
    1. multipart/form-data - 用于文件上传
    2. application/json - 用于 base64 图片

    返回：
        tuple: (topic, images, page_count) - 主题、图片列表和目标页数
    """
    # 检查是否是 multipart/form-data（带图片文件）
    if request.content_type and 'multipart/form-data' in request.content_type:
        topic = request.form.get('topic')
        page_count = _parse_page_count(request.form.get('page_count'))
        images = []

        # 获取上传的图片文件
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    image_data = file.read()
                    images.append(image_data)

        return topic, images, page_count

    # JSON 请求（无图片或 base64 图片）
    data = request.get_json()
    topic = data.get('topic')
    page_count = _parse_page_count(data.get('page_count'))
    images = []

    # 支持 base64 格式的图片
    images_base64 = data.get('images', [])
    if images_base64:
        for img_b64 in images_base64:
            # 移除可能的 data URL 前缀
            if ',' in img_b64:
                img_b64 = img_b64.split(',')[1]
            images.append(base64.b64decode(img_b64))

    return topic, images, page_count


def _parse_page_count(value):
    try:
        if value in (None, ''):
            return None
        return max(2, min(int(value), 5))
    except Exception:
        return None
