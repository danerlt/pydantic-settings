"""Apollo HTTP 客户端."""

import json
import time
import hmac
import hashlib
import base64
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from urllib.parse import urlparse, parse_qs

@dataclass
class ApolloConfigNotification:
    """Apollo 配置更新通知"""
    namespace_name: str
    notification_id: int

class ApolloNotificationMessages:
    """Apollo 配置更新消息"""
    def __init__(self):
        self.messages: Dict[str, int] = {}

    def merge_from(self, other: Dict[str, int]):
        """合并消息"""
        for key, value in other.items():
            self.messages[key] = value
            logger.debug(f"合并消息: {key} -> {value}")

    def clone(self) -> 'ApolloNotificationMessages':
        """克隆消息"""
        clone = ApolloNotificationMessages()
        clone.messages = self.messages.copy()
        logger.debug(f"克隆消息: {self.messages}")
        return clone

class ApolloAuth:
    """Apollo 认证工具类"""
    
    @staticmethod
    def _url_to_path_with_query(url: str) -> str:
        """将 URL 转换为路径和查询字符串"""
        parsed = urlparse(url)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # 按字母顺序排序查询参数
        sorted_query = sorted(query.items())
        query_string = "&".join(f"{k}={v[0]}" for k, v in sorted_query)
        
        if query_string:
            return f"{path}?{query_string}"
        return path

    @staticmethod
    def _sign_string(string_to_sign: str, secret: str) -> str:
        """签名字符串"""
        hmac_obj = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        )
        signature = base64.b64encode(hmac_obj.digest()).decode('utf-8')
        return signature

    @classmethod
    def build_http_headers(cls, url: str, app_id: str, secret: str) -> Dict[str, str]:
        """构建 HTTP 请求头"""
        timestamp = str(int(time.time() * 1000))
        path_with_query = cls._url_to_path_with_query(url)
        string_to_sign = f"{timestamp}\n{path_with_query}"
        signature = cls._sign_string(string_to_sign, secret)

        AUTHORIZATION_FORMAT = "Apollo {}:{}"
        HTTP_HEADER_AUTHORIZATION = "Authorization"
        HTTP_HEADER_TIMESTAMP = "Timestamp"

        headers = {
            HTTP_HEADER_AUTHORIZATION: AUTHORIZATION_FORMAT.format(app_id, signature),
            HTTP_HEADER_TIMESTAMP: timestamp,
            "Content-Type": "application/json"
        }
        logger.debug(f"构建认证头: {headers}")
        return headers

class ApolloHttpClient:
    """Apollo HTTP 客户端"""
    def __init__(self, server_url: str, app_id: str, secret: str, cluster: str = "default"):
        self.server_url = server_url.rstrip("/")
        self.app_id = app_id
        self.secret = secret
        self.cluster = cluster
        self.notifications: Dict[str, int] = {}
        self.notification_messages: Dict[str, ApolloNotificationMessages] = {}
        self._stop_long_polling = False
        logger.info(f"初始化 Apollo HTTP 客户端: server_url={self.server_url}, app_id={self.app_id}, cluster={self.cluster}")

    def get_config(self, namespace: str) -> Dict:
        """获取配置"""
        url = f"{self.server_url}/openapi/v1/configs/{self.app_id}/{self.cluster}/{namespace}"
        logger.debug(f"获取配置: {url}")
        try:
            headers = ApolloAuth.build_http_headers(url, self.app_id, self.secret)
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            config = response.json()
            logger.debug(f"获取配置成功: {namespace}, releaseKey={config.get('releaseKey')}")
            return config
        except requests.exceptions.RequestException as e:
            logger.error(f"获取配置失败: {namespace}, error={str(e)}")
            raise

    def long_polling(self, namespaces: List[str], callback=None):
        """长轮询配置更新"""
        self._stop_long_polling = False
        logger.info(f"开始长轮询: namespaces={namespaces}")
        
        while not self._stop_long_polling:
            try:
                # 构建通知请求
                notifications = [
                    {"namespaceName": namespace, "notificationId": self.notifications.get(namespace, -1)}
                    for namespace in namespaces
                ]
                logger.debug(f"当前通知状态: {notifications}")
                
                # 构建请求参数
                params = {
                    "appId": self.app_id,
                    "cluster": self.cluster,
                    "notifications": json.dumps(notifications)
                }
                
                # 发送长轮询请求
                url = f"{self.server_url}/openapi/v1/notifications/v2"
                logger.debug(f"发送长轮询请求: {url}, params={params}")
                headers = ApolloAuth.build_http_headers(url, self.app_id, self.secret)
                response = requests.get(url, params=params, headers=headers, timeout=90)
                
                if response.status_code == 200:
                    # 配置有更新
                    notifications = response.json()
                    logger.info(f"收到配置更新通知: {notifications}")
                    
                    for notification in notifications:
                        namespace = notification["namespaceName"]
                        notification_id = notification["notificationId"]
                        
                        # 更新通知 ID
                        old_id = self.notifications.get(namespace)
                        self.notifications[namespace] = notification_id
                        logger.debug(f"更新通知ID: {namespace}, {old_id} -> {notification_id}")
                        
                        # 更新消息
                        if "messages" in notification:
                            messages = self.notification_messages.get(namespace)
                            if messages is None:
                                messages = ApolloNotificationMessages()
                                self.notification_messages[namespace] = messages
                            messages.merge_from(notification["messages"])
                            logger.debug(f"更新消息: {namespace}, messages={notification['messages']}")
                        
                        # 重新获取配置
                        config = self.get_config(namespace)
                        
                        # 调用回调函数
                        if callback:
                            logger.debug(f"调用配置更新回调: {namespace}")
                            callback(namespace, config)
                
                elif response.status_code == 304:
                    # 配置没有更新，继续轮询
                    logger.debug("配置没有更新，继续轮询")
                    continue
                
                else:
                    # 其他错误，等待后重试
                    logger.warning(f"长轮询请求失败: status_code={response.status_code}")
                    time.sleep(1)
                    
            except requests.exceptions.Timeout:
                # 超时，继续轮询
                logger.debug("长轮询请求超时，继续轮询")
                continue
            except Exception as e:
                logger.error(f"长轮询发生错误: {str(e)}")
                time.sleep(1)

    def stop_long_polling(self):
        """停止长轮询"""
        logger.info("停止长轮询")
        self._stop_long_polling = True 