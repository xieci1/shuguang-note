import logging
import os
import re
import base64
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from backend.utils.text_client import get_text_chat_client

logger = logging.getLogger(__name__)


class OutlineService:
    def __init__(self):
        logger.debug("初始化 OutlineService...")
        self.text_config = self._load_text_config()
        self.client = self._get_client()
        self.prompt_template = self._load_prompt_template()
        logger.info(f"OutlineService 初始化完成，使用服务商: {self.text_config.get('active_provider')}")

    def _load_text_config(self) -> dict:
        """加载文本生成配置"""
        config_path = Path(__file__).parent.parent.parent / 'text_providers.yaml'
        logger.debug(f"加载文本配置: {config_path}")

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                logger.debug(f"文本配置加载成功: active={config.get('active_provider')}")
                return config
            except yaml.YAMLError as e:
                logger.error(f"文本配置 YAML 解析失败: {e}")
                raise ValueError(
                    f"文本配置文件格式错误: text_providers.yaml\n"
                    f"YAML 解析错误: {e}\n"
                    "解决方案：检查 YAML 缩进和语法"
                )

        logger.warning("text_providers.yaml 不存在，使用默认配置")
        # 默认配置
        return {
            'active_provider': 'google_gemini',
            'providers': {
                'google_gemini': {
                    'type': 'google_gemini',
                    'model': 'gemini-2.0-flash-exp',
                    'temperature': 1.0,
                    'max_output_tokens': 8000
                }
            }
        }

    def _get_client(self):
        """根据配置获取客户端"""
        active_provider = self.text_config.get('active_provider', 'google_gemini')
        providers = self.text_config.get('providers', {})

        if not providers:
            logger.error("未找到任何文本生成服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 或手动编辑 text_providers.yaml 文件"
            )

        if active_provider not in providers:
            available = ', '.join(providers.keys())
            logger.error(f"文本服务商 [{active_provider}] 不存在，可用: {available}")
            raise ValueError(
                f"未找到文本生成服务商配置: {active_provider}\n"
                f"可用的服务商: {available}\n"
                "解决方案：在系统设置中选择一个可用的服务商"
            )

        provider_config = providers.get(active_provider, {})

        if not provider_config.get('api_key'):
            logger.error(f"文本服务商 [{active_provider}] 未配置 API Key")
            raise ValueError(
                f"文本服务商 {active_provider} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        logger.info(f"使用文本服务商: {active_provider} (type={provider_config.get('type')})")
        return get_text_chat_client(provider_config)

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "outline_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_outline(self, outline_text: str) -> List[Dict[str, Any]]:
        # 按 <page> 分割页面（兼容旧的 --- 分隔符）
        if '<page>' in outline_text:
            pages_raw = re.split(r'<page>', outline_text, flags=re.IGNORECASE)
        else:
            # 向后兼容：如果没有 <page> 则使用 ---
            pages_raw = outline_text.split("---")

        pages = []

        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue

            page_type = "content"
            type_match = re.match(r"\[(\S+)\]", page_text)
            if type_match:
                type_cn = type_match.group(1)
                type_mapping = {
                    "封面": "cover",
                    "内容": "content",
                    "总结": "summary",
                }
                page_type = type_mapping.get(type_cn, "content")

            pages.append({
                "index": index,
                "type": page_type,
                "content": page_text
            })

        return pages

    def _fit_page_count(self, pages: List[Dict[str, Any]], page_count: Optional[int]) -> List[Dict[str, Any]]:
        if not page_count or not pages:
            return pages

        page_count = max(2, min(page_count, 5))
        fitted = pages[:page_count]

        if len(fitted) < page_count:
            last_content = fitted[-1]["content"] if fitted else "[内容]\n补充内容"
            while len(fitted) < page_count:
                fitted.append({
                    "index": len(fitted),
                    "type": "summary" if len(fitted) == page_count - 1 else "content",
                    "content": last_content,
                })

        for index, page in enumerate(fitted):
            page["index"] = index
            if index == 0:
                page["type"] = "cover"
            elif index == page_count - 1:
                page["type"] = "summary"
            elif page.get("type") == "summary":
                page["type"] = "content"

        return fitted

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None,
        page_count: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            logger.info(f"开始生成大纲: topic={topic[:50]}..., images={len(images) if images else 0}")
            page_count_instruction = ""
            if page_count:
                page_count = max(2, min(page_count, 5))
                page_count_instruction = (
                    f"\n\n【页数要求】请严格生成 {page_count} 页，"
                    f"包括 1 页封面、{max(page_count - 2, 0)} 页内容页和 1 页总结页。"
                    "不要多页，也不要少页。"
                )
            prompt = self.prompt_template.format(topic=f"{topic}{page_count_instruction}")

            if images and len(images) > 0:
                prompt += f"\n\n注意：用户提供了 {len(images)} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。这些图片可能是产品图、个人照片或场景图，请根据图片内容来优化大纲，使生成的内容与图片相关联。"
                logger.debug(f"添加了 {len(images)} 张参考图片到提示词")

            # 从配置中获取模型参数
            active_provider = self.text_config.get('active_provider', 'google_gemini')
            providers = self.text_config.get('providers', {})
            provider_config = providers.get(active_provider, {})

            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            logger.info(f"调用文本生成 API: model={model}, temperature={temperature}")
            outline_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=images
            )

            logger.debug(f"API 返回文本长度: {len(outline_text)} 字符")
            pages = self._parse_outline(outline_text)
            pages = self._fit_page_count(pages, page_count)
            logger.info(f"大纲解析完成，共 {len(pages)} 页")

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "has_images": images is not None and len(images) > 0
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"大纲生成失败: {error_msg}")

            # 根据错误类型提供更详细的错误信息
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 模型名称不正确\n"
                    "2. 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 网络连接不稳定\n"
                    "2. API 服务暂时不可用\n"
                    "3. Base URL 配置错误\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API 调用次数超限\n"
                    "2. 账户配额用尽\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"大纲生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. Text API 配置错误或密钥无效\n"
                    "2. 网络连接问题\n"
                    "3. 模型无法访问或不存在\n"
                    "建议：检查配置文件 text_providers.yaml"
                )

            return {
                "success": False,
                "error": detailed_error
            }

    def generate_topic_ideas(self, topic: str, count: int = 5) -> Dict[str, Any]:
        """基于同一个话题生成多个不同作品方向。"""
        try:
            count = max(1, min(count, 10))
            prompt = f"""你是小红书选题策划专家。请围绕用户给出的同一个大话题，生成 {count} 个差异明显、可以分别制作成独立小红书图文作品的选题方案。

用户话题：
{topic}

要求：
1. 每个方案必须是一个独立作品方向，不要只是同义改写。
2. 方案要适合后续生成一整套多页小红书图文。
3. 输出必须是严格 JSON，不要 Markdown，不要解释。
4. JSON 格式：
{{
  "ideas": [
    {{
      "title": "选题标题",
      "angle": "切入角度",
      "audience": "目标人群",
      "hook": "封面钩子",
      "prompt": "可直接用于生成完整图文大纲的详细主题指令"
    }}
  ]
}}
"""

            active_provider = self.text_config.get('active_provider', 'google_gemini')
            providers = self.text_config.get('providers', {})
            provider_config = providers.get(active_provider, {})

            text = self.client.generate_text(
                prompt=prompt,
                model=provider_config.get('model', 'gemini-2.0-flash-exp'),
                temperature=provider_config.get('temperature', 1.0),
                max_output_tokens=provider_config.get('max_output_tokens', 8000)
            )

            ideas = self._parse_topic_ideas(text)
            return {
                "success": True,
                "ideas": ideas[:count],
                "raw": text
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"选题方案生成失败: {error_msg}")
            return {
                "success": False,
                "error": f"选题方案生成失败。\n错误详情: {error_msg}\n建议：检查文本生成服务配置"
            }

    def _parse_topic_ideas(self, text: str) -> List[Dict[str, str]]:
        """解析模型返回的选题 JSON，失败时尽量给出可用兜底。"""
        import json

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if match:
            cleaned = match.group(0)

        data = json.loads(cleaned)
        raw_ideas = data.get("ideas", []) if isinstance(data, dict) else []

        ideas = []
        for item in raw_ideas:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            prompt = str(item.get("prompt", "")).strip()
            if not title:
                continue
            ideas.append({
                "title": title,
                "angle": str(item.get("angle", "")).strip(),
                "audience": str(item.get("audience", "")).strip(),
                "hook": str(item.get("hook", "")).strip(),
                "prompt": prompt or title
            })

        if not ideas:
            raise ValueError("模型没有返回可用的选题方案")

        return ideas


def get_outline_service() -> OutlineService:
    """
    获取大纲生成服务实例
    每次调用都创建新实例以确保配置是最新的
    """
    return OutlineService()
