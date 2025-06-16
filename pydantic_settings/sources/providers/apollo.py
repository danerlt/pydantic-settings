"""Apollo configuration center settings source."""

from __future__ import annotations as _annotations

import json
import time
import threading
from collections.abc import Mapping
from typing import TYPE_CHECKING, Optional, Any, Dict
import requests
from pydantic import BaseModel

from .env import EnvSettingsSource

if TYPE_CHECKING:
    from pydantic_settings.main import BaseSettings

class ApolloConfigMapping(Mapping[str, Optional[str]]):
    """Apollo 配置映射类"""
    
    def __init__(
        self,
        app_id: str,
        cluster: str = "default",
        namespace: str = "application",
        server_url: str = "http://localhost:8080",
        refresh_interval: int = 60,
        case_sensitive: bool = True,
    ) -> None:
        self._app_id = app_id
        self._cluster = cluster
        self._namespace = namespace
        self._server_url = server_url.rstrip('/')
        self._refresh_interval = refresh_interval
        self._case_sensitive = case_sensitive
        self._loaded_configs: Dict[str, str] = {}
        self._last_update_time: float = 0
        self._lock = threading.Lock()
        self._notification_id: int = -1
        self._start_notification_thread()

    def _get_config_url(self) -> str:
        """获取配置的URL"""
        return f"{self._server_url}/configs/{self._app_id}/{self._cluster}/{self._namespace}"

    def _get_notification_url(self) -> str:
        """获取通知的URL"""
        return f"{self._server_url}/notifications/v2"

    def _load_configs(self) -> None:
        """加载配置"""
        try:
            response = requests.get(
                self._get_config_url(),
                params={"releaseKey": self._notification_id}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("configurations"):
                    with self._lock:
                        self._loaded_configs = data["configurations"]
                        self._last_update_time = time.time()
                        self._notification_id = data.get("releaseKey", self._notification_id)
        except Exception as e:
            print(f"Error loading Apollo configs: {e}")

    def _start_notification_thread(self) -> None:
        """启动通知线程"""
        def notification_worker():
            while True:
                try:
                    response = requests.get(
                        self._get_notification_url(),
                        params={
                            "appId": self._app_id,
                            "cluster": self._cluster,
                            "notifications": json.dumps([{
                                "namespaceName": self._namespace,
                                "notificationId": self._notification_id
                            }])
                        },
                        timeout=self._refresh_interval
                    )
                    if response.status_code == 200:
                        notifications = response.json()
                        if notifications and notifications[0].get("notificationId") != self._notification_id:
                            self._load_configs()
                except Exception as e:
                    print(f"Error in notification thread: {e}")
                time.sleep(1)

        thread = threading.Thread(target=notification_worker, daemon=True)
        thread.start()

    def __getitem__(self, key: str) -> str | None:
        """获取配置值"""
        if not self._case_sensitive:
            key = key.lower()
        
        # 检查是否需要刷新配置
        current_time = time.time()
        if current_time - self._last_update_time > self._refresh_interval:
            self._load_configs()
        
        return self._loaded_configs.get(key)

    def __len__(self) -> int:
        return len(self._loaded_configs)

    def __iter__(self):
        return iter(self._loaded_configs)

class ApolloSettingsSource(EnvSettingsSource):
    """Apollo 配置源"""
    
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        app_id: str,
        cluster: str = "default",
        namespace: str = "application",
        server_url: str = "http://localhost:8080",
        refresh_interval: int = 60,
        env_prefix: str | None = None,
        env_parse_none_str: str | None = None,
        env_parse_enums: bool | None = None,
        case_sensitive: bool = True,
    ) -> None:
        self._apollo_mapping = ApolloConfigMapping(
            app_id=app_id,
            cluster=cluster,
            namespace=namespace,
            server_url=server_url,
            refresh_interval=refresh_interval,
            case_sensitive=case_sensitive,
        )
        super().__init__(
            settings_cls,
            case_sensitive=case_sensitive,
            env_prefix=env_prefix,
            env_ignore_empty=False,
            env_parse_none_str=env_parse_none_str,
            env_parse_enums=env_parse_enums,
        )

    def _load_env_vars(self) -> Mapping[str, Optional[str]]:
        return self._apollo_mapping

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(app_id={self._apollo_mapping._app_id!r})" 