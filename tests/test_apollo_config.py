"""Test Apollo configuration."""

import os
import time
import pytest
from typing import Dict, Any
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pydantic_settings.sources.providers.apollo import ApolloSettingsSource
from pydantic_settings import EnvSettingsSource

# 配置 loguru
logger.remove()  # 移除默认的处理器
logger.add(
    "logs/apollo_config_test_{time}.log",
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

class DatabaseConfig(BaseModel):
    """数据库配置"""
    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=5432, description="数据库端口")
    user: str = Field(default="postgres", description="数据库用户")
    password: str = Field(default="", description="数据库密码")
    database: str = Field(default="test", description="数据库名称")

class RedisConfig(BaseModel):
    """Redis 配置"""
    host: str = Field(default="localhost", description="Redis 主机")
    port: int = Field(default=6379, description="Redis 端口")
    password: str = Field(default="", description="Redis 密码")
    db: int = Field(default=0, description="Redis 数据库")

class AppConfig(BaseModel):
    """应用配置"""
    name: str = Field(default="test", description="应用名称")
    debug: bool = Field(default=False, description="是否开启调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    max_workers: int = Field(default=4, description="最大工作进程数")

class Settings(BaseSettings):
    """设置类"""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="数据库配置")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis 配置")
    app: AppConfig = Field(default_factory=AppConfig, description="应用配置")

    def customize_sources(self):
        """自定义设置源"""
        apollo_source = ApolloSettingsSource(
            server_url=APOLLO_TEST_SERVER,
            app_id=APOLLO_APP_ID,
            secret=APOLLO_SECRET,
            namespace=APOLLO_NAMESPACE,
            refresh_interval=5,  # 5 秒刷新一次
            case_sensitive=False  # 不区分大小写
        )
        return (apollo_source,)

class TestApolloConfig:
    """Test Apollo configuration."""

    def test_load_config(self):
        """测试加载配置"""
        logger.info("开始测试加载配置")
        settings = Settings()
        
        # 验证配置是否正确加载
        assert settings.database.host == "localhost"
        assert settings.database.port == 5432
        assert settings.redis.host == "localhost"
        assert settings.redis.port == 6379
        assert settings.app.name == "test"
        assert settings.app.debug is False
        
        logger.info("配置加载测试成功")

    def test_config_update(self):
        """测试配置更新"""
        logger.info("开始测试配置更新")
        settings = Settings()
        
        # 记录初始配置
        initial_db_host = settings.database.host
        initial_redis_host = settings.redis.host
        initial_app_name = settings.app.name
        
        logger.info(f"初始配置: db_host={initial_db_host}, redis_host={initial_redis_host}, app_name={initial_app_name}")
        
        # 等待配置更新
        logger.debug("等待配置更新...")
        time.sleep(10)
        
        # 验证配置是否更新
        assert settings.database.host != initial_db_host or settings.redis.host != initial_redis_host or settings.app.name != initial_app_name
        logger.info(f"更新后配置: db_host={settings.database.host}, redis_host={settings.redis.host}, app_name={settings.app.name}")
        
        logger.info("配置更新测试成功")

    def test_config_validation(self):
        """测试配置验证"""
        logger.info("开始测试配置验证")
        
        # 测试无效的数据库端口
        with pytest.raises(ValueError):
            class InvalidSettings(BaseSettings):
                database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(port=-1))
                
                def customize_sources(self):
                    apollo_source = ApolloSettingsSource(
                        server_url=APOLLO_TEST_SERVER,
                        app_id=APOLLO_APP_ID,
                        secret=APOLLO_SECRET,
                        namespace=APOLLO_NAMESPACE
                    )
                    return (apollo_source,)
            
            InvalidSettings()
        
        # 测试无效的 Redis 数据库
        with pytest.raises(ValueError):
            class InvalidSettings(BaseSettings):
                redis: RedisConfig = Field(default_factory=lambda: RedisConfig(db=-1))
                
                def customize_sources(self):
                    apollo_source = ApolloSettingsSource(
                        server_url=APOLLO_TEST_SERVER,
                        app_id=APOLLO_APP_ID,
                        secret=APOLLO_SECRET,
                        namespace=APOLLO_NAMESPACE
                    )
                    return (apollo_source,)
            
            InvalidSettings()
        
        logger.info("配置验证测试成功")

    def test_config_case_insensitive(self):
        """测试配置大小写不敏感"""
        logger.info("开始测试配置大小写不敏感")
        settings = Settings()
        
        # 验证大小写不敏感的配置访问
        assert settings.database.host == settings.database.HOST
        assert settings.redis.host == settings.redis.HOST
        assert settings.app.name == settings.app.NAME
        
        logger.info("配置大小写不敏感测试成功")

    def test_config_nested(self):
        """测试嵌套配置"""
        logger.info("开始测试嵌套配置")
        settings = Settings()
        
        # 验证嵌套配置访问
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.redis, RedisConfig)
        assert isinstance(settings.app, AppConfig)
        
        # 验证嵌套配置的值
        assert settings.database.host == "localhost"
        assert settings.redis.host == "localhost"
        assert settings.app.name == "test"
        
        logger.info("嵌套配置测试成功")

    def test_config_default_values(self):
        """测试配置默认值"""
        logger.info("开始测试配置默认值")
        settings = Settings()
        
        # 验证默认值
        assert settings.database.host == "localhost"
        assert settings.database.port == 5432
        assert settings.database.user == "postgres"
        assert settings.database.password == ""
        assert settings.database.database == "test"
        
        assert settings.redis.host == "localhost"
        assert settings.redis.port == 6379
        assert settings.redis.password == ""
        assert settings.redis.db == 0
        
        assert settings.app.name == "test"
        assert settings.app.debug is False
        assert settings.app.log_level == "INFO"
        assert settings.app.max_workers == 4
        
        logger.info("配置默认值测试成功") 