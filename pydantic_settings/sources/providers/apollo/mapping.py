"""Apollo 配置映射."""

import threading
import time
from typing import Dict, Any, Optional
from loguru import logger
from .client import ApolloHttpClient

class ApolloConfigMapping:
    """Apollo 配置映射"""

    def __init__(
        self,
        server_url: str,
        app_id: str,
        secret: str,
        cluster: str = "default",
        namespace: str = "application",
        refresh_interval: int = 60,
        case_sensitive: bool = True
    ):
        """
        初始化 Apollo 配置映射

        Args:
            server_url: Apollo 服务器地址
            app_id: 应用 ID
            secret: 密钥
            cluster: 集群名称，默认为 default
            namespace: 命名空间，默认为 application
            refresh_interval: 刷新间隔（秒），默认为 60 秒
            case_sensitive: 是否区分大小写，默认为 True
        """
        self.client = ApolloHttpClient(server_url, app_id, secret, cluster)
        self.namespace = namespace
        self.refresh_interval = refresh_interval
        self.case_sensitive = case_sensitive
        self._configs: Dict[str, Any] = {}
        self._last_refresh_time = 0
        self._lock = threading.Lock()
        self._notification_thread: Optional[threading.Thread] = None
        self._stop_notification = False
        logger.info(f"初始化 Apollo 配置映射: server_url={server_url}, app_id={app_id}, namespace={namespace}")

    def _load_configs(self) -> None:
        """加载配置"""
        try:
            config = self.client.get_config(self.namespace)
            if config and "configurations" in config:
                with self._lock:
                    self._configs = config["configurations"]
                    self._last_refresh_time = time.time()
                    logger.debug(f"加载配置成功: {self._configs}")
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            raise

    def _start_notification_thread(self) -> None:
        """启动通知线程"""
        if self._notification_thread is None or not self._notification_thread.is_alive():
            self._stop_notification = False
            self._notification_thread = threading.Thread(
                target=self._notification_loop,
                daemon=True
            )
            self._notification_thread.start()
            logger.info("启动通知线程")

    def _notification_loop(self) -> None:
        """通知循环"""
        def on_config_update(namespace: str, config: Dict) -> None:
            """配置更新回调"""
            if config and "configurations" in config:
                with self._lock:
                    self._configs = config["configurations"]
                    self._last_refresh_time = time.time()
                    logger.debug(f"配置已更新: {self._configs}")

        while not self._stop_notification:
            try:
                self.client.long_polling([self.namespace], callback=on_config_update)
            except Exception as e:
                logger.error(f"通知循环发生错误: {str(e)}")
                time.sleep(1)

    def __getitem__(self, key: str) -> Any:
        """
        获取配置值

        Args:
            key: 配置键

        Returns:
            配置值
        """
        if not self.case_sensitive:
            key = key.lower()

        # 检查是否需要刷新配置
        current_time = time.time()
        if current_time - self._last_refresh_time > self.refresh_interval:
            self._load_configs()

        # 启动通知线程
        self._start_notification_thread()

        # 获取配置值
        with self._lock:
            if not self.case_sensitive:
                # 不区分大小写时，查找匹配的键
                for k, v in self._configs.items():
                    if k.lower() == key:
                        return v
                raise KeyError(f"配置键不存在: {key}")
            return self._configs[key]

    def __contains__(self, key: str) -> bool:
        """
        检查配置键是否存在

        Args:
            key: 配置键

        Returns:
            是否存在
        """
        if not self.case_sensitive:
            key = key.lower()
            return any(k.lower() == key for k in self._configs.keys())
        return key in self._configs

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，如果不存在则返回默认值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值或默认值
        """
        try:
            return self[key]
        except KeyError:
            return default

    def stop(self) -> None:
        """停止通知线程"""
        self._stop_notification = True
        if self._notification_thread and self._notification_thread.is_alive():
            self._notification_thread.join(timeout=1)
        self.client.stop_long_polling()
        logger.info("停止通知线程") 