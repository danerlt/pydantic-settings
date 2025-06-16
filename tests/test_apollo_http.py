"""Test Apollo HTTP API and config update notification."""

import json
import time
import pytest
import requests
from typing import Dict
from loguru import logger
from pydantic_settings.sources.providers.apollo.client import ApolloHttpClient

# 配置 loguru
logger.remove()  # 移除默认的处理器
logger.add(
    "logs/apollo_test_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    encoding="utf-8"
)
logger.add(
    lambda msg: print(msg, end=""),
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
    colorize=True
)

# Apollo 配置中心测试服务器地址
APOLLO_TEST_SERVER = "http://81.68.181.139"
APOLLO_APP_ID = "aiem-incremental-learning"
APOLLO_NAMESPACE = "dev.yaml"
APOLLO_CLUSTER = "default"
APOLLO_SECRET = "your-secret-key"  # 请替换为实际的密钥

class TestApolloHttp:
    """Test Apollo HTTP API."""

    def test_get_config(self):
        """测试获取配置"""
        logger.info("开始测试获取配置")
        client = ApolloHttpClient(APOLLO_TEST_SERVER, APOLLO_APP_ID, APOLLO_SECRET)
        config = client.get_config(APOLLO_NAMESPACE)
        assert config is not None
        assert "configurations" in config
        assert "releaseKey" in config
        logger.info(f"获取配置测试成功: releaseKey={config['releaseKey']}")

    def test_long_polling(self):
        """测试长轮询配置更新"""
        logger.info("开始测试长轮询配置更新")
        client = ApolloHttpClient(APOLLO_TEST_SERVER, APOLLO_APP_ID, APOLLO_SECRET)
        updated_configs = {}

        def on_config_update(namespace: str, config: Dict):
            """配置更新回调"""
            updated_configs[namespace] = config
            logger.info(f"收到配置更新: namespace={namespace}, releaseKey={config.get('releaseKey')}")

        # 启动长轮询
        import threading
        polling_thread = threading.Thread(
            target=client.long_polling,
            args=([APOLLO_NAMESPACE],),
            kwargs={"callback": on_config_update}
        )
        polling_thread.daemon = True
        polling_thread.start()
        logger.info("长轮询线程已启动")

        try:
            # 等待一段时间，观察配置更新
            logger.debug("等待配置更新...")
            time.sleep(5)

            # 验证配置是否更新
            assert APOLLO_NAMESPACE in updated_configs
            assert "configurations" in updated_configs[APOLLO_NAMESPACE]
            logger.info("配置更新验证成功")

        finally:
            # 停止长轮询
            logger.info("停止长轮询")
            client.stop_long_polling()
            polling_thread.join(timeout=1)

    def test_multiple_namespaces(self):
        """测试多个命名空间的长轮询"""
        logger.info("开始测试多个命名空间的长轮询")
        client = ApolloHttpClient(APOLLO_TEST_SERVER, APOLLO_APP_ID, APOLLO_SECRET)
        updated_configs = {}

        def on_config_update(namespace: str, config: Dict):
            """配置更新回调"""
            updated_configs[namespace] = config
            logger.info(f"收到配置更新: namespace={namespace}, releaseKey={config.get('releaseKey')}")

        # 启动长轮询
        import threading
        polling_thread = threading.Thread(
            target=client.long_polling,
            args=([APOLLO_NAMESPACE, "application"],),
            kwargs={"callback": on_config_update}
        )
        polling_thread.daemon = True
        polling_thread.start()
        logger.info("长轮询线程已启动")

        try:
            # 等待一段时间，观察配置更新
            logger.debug("等待配置更新...")
            time.sleep(5)

            # 验证配置是否更新
            for namespace in [APOLLO_NAMESPACE, "application"]:
                assert namespace in updated_configs
                assert "configurations" in updated_configs[namespace]
            logger.info("多命名空间配置更新验证成功")

        finally:
            # 停止长轮询
            logger.info("停止长轮询")
            client.stop_long_polling()
            polling_thread.join(timeout=1)

    def test_error_handling(self):
        """测试错误处理"""
        logger.info("开始测试错误处理")
        client = ApolloHttpClient(APOLLO_TEST_SERVER, APOLLO_APP_ID, APOLLO_SECRET)
        
        # 测试不存在的命名空间
        logger.debug("测试不存在的命名空间")
        with pytest.raises(requests.exceptions.HTTPError):
            client.get_config("non-existent-namespace")
        
        # 测试不存在的应用
        logger.debug("测试不存在的应用")
        with pytest.raises(requests.exceptions.HTTPError):
            client = ApolloHttpClient(APOLLO_TEST_SERVER, "non-existent-app", APOLLO_SECRET)
            client.get_config(APOLLO_NAMESPACE)
        
        logger.info("错误处理测试完成") 