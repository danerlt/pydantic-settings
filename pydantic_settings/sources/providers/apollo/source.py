"""Apollo 设置源."""

import os
from typing import Dict, Any, Optional
from loguru import logger
from pydantic_settings import EnvSettingsSource
from .mapping import ApolloConfigMapping

class ApolloSettingsSource(EnvSettingsSource):
    """Apollo 设置源"""

    def __init__(
        self,
        server_url: str,
        app_id: str,
        secret: str,
        cluster: str = "default",
        namespace: str = "application",
        refresh_interval: int = 60,
        case_sensitive: bool = True,
    ):
        """
        初始化 Apollo 设置源

        Args:
            server_url: Apollo 服务器地址
            app_id: 应用 ID
            secret: 密钥
            cluster: 集群名称，默认为 default
            namespace: 命名空间，默认为 application
            refresh_interval: 刷新间隔（秒），默认为 60 秒
            case_sensitive: 是否区分大小写，默认为 True
        """
        super().__init__()
        self.mapping = ApolloConfigMapping(
            server_url=server_url,
            app_id=app_id,
            secret=secret,
            cluster=cluster,
            namespace=namespace,
            refresh_interval=refresh_interval,
            case_sensitive=case_sensitive
        )
        logger.info(f"初始化 Apollo 设置源: server_url={server_url}, app_id={app_id}, namespace={namespace}")

    def __call__(self, settings: Any) -> Dict[str, Any]:
        """
        获取设置

        Args:
            settings: 设置对象

        Returns:
            设置字典
        """
        # 获取环境变量设置
        env_settings = super().__call__(settings)
        
        # 获取 Apollo 设置
        apollo_settings = {}
        for key in settings.model_fields.keys():
            try:
                value = self.mapping[key]
                apollo_settings[key] = value
                logger.debug(f"从 Apollo 获取配置: {key}={value}")
            except KeyError:
                logger.debug(f"Apollo 中不存在配置: {key}")
                continue
        
        # 合并设置
        settings_dict = {**env_settings, **apollo_settings}
        logger.debug(f"合并后的设置: {settings_dict}")
        return settings_dict

    def stop(self) -> None:
        """停止 Apollo 设置源"""
        self.mapping.stop()
        logger.info("停止 Apollo 设置源") 