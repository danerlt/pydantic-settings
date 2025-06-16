"""Test Apollo HTTP client."""

import time
import pytest
from typing import Dict, Any
from loguru import logger
from pydantic_settings.sources.providers.apollo.client import ApolloHttpClient, ApolloConfigNotification

# 配置 loguru
logger.remove()  # 移除默认的处理器
logger.add(
    "logs/apollo_client_test_{time}.log",
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
APOLLO_SECRET = "4f726c096c654dd88fbf88929e638439"  # 请替换为实际的密钥

class TestApolloHttpClient:
    """Test Apollo HTTP client."""

    def test_get_config(self):
        """测试获取配置"""
        logger.info("开始测试获取配置")
        client = ApolloHttpClient(
            server_url=APOLLO_TEST_SERVER,
            app_id=APOLLO_APP_ID,
            secret=APOLLO_SECRET,
            cluster=APOLLO_CLUSTER
        )
        
        # 获取配置
        config = client.get_config(APOLLO_NAMESPACE)
        logger.info(f"获取到的配置: {config}")
        
        # 验证配置
        assert config is not None
        assert "configurations" in config
        assert isinstance(config["configurations"], dict)
        assert len(config["configurations"]) > 0
        
        logger.info("获取配置测试成功")

    def test_long_polling(self):
        """测试长轮询"""
        logger.info("开始测试长轮询")
        client = ApolloHttpClient(
            server_url=APOLLO_TEST_SERVER,
            app_id=APOLLO_APP_ID,
            secret=APOLLO_SECRET,
            cluster=APOLLO_CLUSTER
        )
        
        # 记录初始配置
        initial_config = client.get_config(APOLLO_NAMESPACE)
        logger.info(f"初始配置: {initial_config}")
        
        # 定义配置更新回调
        def on_config_update(namespace: str, config: Dict[str, Any]) -> None:
            logger.info(f"配置已更新: namespace={namespace}, config={config}")
            assert namespace == APOLLO_NAMESPACE
            assert config is not None
            assert "configurations" in config
        
        # 启动长轮询
        logger.info("启动长轮询")
        client.long_polling([APOLLO_NAMESPACE], callback=on_config_update)
        
        # 等待一段时间以接收可能的更新
        logger.debug("等待配置更新...")
        time.sleep(10)
        
        # 停止长轮询
        logger.info("停止长轮询")
        client.stop_long_polling()
        
        logger.info("长轮询测试成功")

    def test_multiple_namespaces(self):
        """测试多个命名空间"""
        logger.info("开始测试多个命名空间")
        client = ApolloHttpClient(
            server_url=APOLLO_TEST_SERVER,
            app_id=APOLLO_APP_ID,
            secret=APOLLO_SECRET,
            cluster=APOLLO_CLUSTER
        )
        
        # 获取多个命名空间的配置
        namespaces = [APOLLO_NAMESPACE, "application"]
        for namespace in namespaces:
            config = client.get_config(namespace)
            logger.info(f"命名空间 {namespace} 的配置: {config}")
            assert config is not None
            assert "configurations" in config
        
        logger.info("多个命名空间测试成功")

    def test_error_handling(self):
        """测试错误处理"""
        logger.info("开始测试错误处理")
        
        # 测试无效的服务器地址
        with pytest.raises(Exception):
            client = ApolloHttpClient(
                server_url="http://invalid-server",
                app_id=APOLLO_APP_ID,
                secret=APOLLO_SECRET,
                cluster=APOLLO_CLUSTER
            )
            client.get_config(APOLLO_NAMESPACE)
        
        # 测试无效的应用 ID
        with pytest.raises(Exception):
            client = ApolloHttpClient(
                server_url=APOLLO_TEST_SERVER,
                app_id="invalid-app",
                secret=APOLLO_SECRET,
                cluster=APOLLO_CLUSTER
            )
            client.get_config(APOLLO_NAMESPACE)
        
        # 测试无效的命名空间
        with pytest.raises(Exception):
            client = ApolloHttpClient(
                server_url=APOLLO_TEST_SERVER,
                app_id=APOLLO_APP_ID,
                secret=APOLLO_SECRET,
                cluster=APOLLO_CLUSTER
            )
            client.get_config("invalid-namespace")
        
        logger.info("错误处理测试成功")

    def test_auth_headers(self):
        """测试认证头"""
        logger.info("开始测试认证头")
        client = ApolloHttpClient(
            server_url=APOLLO_TEST_SERVER,
            app_id=APOLLO_APP_ID,
            secret=APOLLO_SECRET,
            cluster=APOLLO_CLUSTER
        )
        
        # 获取配置
        config = client.get_config(APOLLO_NAMESPACE)
        logger.info(f"获取到的配置: {config}")
        
        # 验证配置
        assert config is not None
        assert "configurations" in config
        
        logger.info("认证头测试成功") 