"""图片生成器工厂"""
from typing import Dict, Any
from .base import ImageGeneratorBase


class ImageGeneratorFactory:
    """图片生成器工厂类"""

    # 注册的生成器类型
    GENERATORS = {
        'google_genai': ('backend.generators.google_genai', 'GoogleGenAIGenerator'),
        'openai': ('backend.generators.openai_compatible', 'OpenAICompatibleGenerator'),
        'openai_compatible': ('backend.generators.openai_compatible', 'OpenAICompatibleGenerator'),
        'image_api': ('backend.generators.image_api', 'ImageApiGenerator'),
    }

    @classmethod
    def create(cls, provider: str, config: Dict[str, Any]) -> ImageGeneratorBase:
        """
        创建图片生成器实例

        Args:
            provider: 服务商类型 ('google_genai', 'openai', 'openai_compatible')
            config: 配置字典

        Returns:
            图片生成器实例

        Raises:
            ValueError: 不支持的服务商类型
        """
        if provider not in cls.GENERATORS:
            available = ', '.join(cls.GENERATORS.keys())
            raise ValueError(
                f"不支持的图片生成服务商: {provider}\n"
                f"支持的服务商类型: {available}\n"
                "解决方案：\n"
                "1. 检查 image_providers.yaml 中的 active_provider 配置\n"
                "2. 确认 provider.type 字段是否正确\n"
                "3. 或使用环境变量 IMAGE_PROVIDER 指定服务商"
            )

        generator_class = cls._load_generator_class(provider)
        return generator_class(config)

    @classmethod
    def _load_generator_class(cls, provider: str):
        import importlib

        entry = cls.GENERATORS[provider]
        if isinstance(entry, type):
            return entry

        module_name, class_name = entry
        try:
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except ModuleNotFoundError as e:
            raise ValueError(
                f"图片生成服务商 {provider} 缺少依赖: {e.name}\n"
                "解决方案：安装项目依赖后重启后端，或在系统设置中切换到已安装依赖支持的图片服务商。"
            ) from e

    @classmethod
    def register_generator(cls, name: str, generator_class: type):
        """
        注册自定义生成器

        Args:
            name: 生成器名称
            generator_class: 生成器类
        """
        if not issubclass(generator_class, ImageGeneratorBase):
            raise TypeError(
                f"注册失败：生成器类必须继承自 ImageGeneratorBase。\n"
                f"提供的类: {generator_class.__name__}\n"
                f"基类: ImageGeneratorBase"
            )

        cls.GENERATORS[name] = generator_class
