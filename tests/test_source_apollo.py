"""Test pydantic_settings.ApolloSettingsSource"""

import json
import pytest
import yaml
import requests
from pydantic import BaseModel
from typing import List

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from pydantic_settings.sources import ApolloSettingsSource

# Apollo 配置中心测试服务器地址
APOLLO_TEST_SERVER = "http://81.68.181.139"
APOLLO_APP_ID = "aiem-incremental-learning"
APOLLO_NAMESPACE = "dev.yaml"

# 测试配置数据
TEST_CONFIG = {
    "database.host": "localhost",
    "database.port": "5432",
    "database.user": "test_user",
    "database.password": "test_password",
    "database.pool_size": "20",
    "database.pool_timeout": "30",
    "database.pool_recycle": "3600",
    "app.name": "test_app",
    "app.debug": "true",
    "app.log_level": "INFO",
    "app.workers": "4",
    "app.timeout": "30",
    "redis.host": "localhost",
    "redis.port": "6379",
    "redis.db": "0",
    "redis.password": "redis_password",
    "redis.pool_size": "10",
    "model.batch_size": "32",
    "model.learning_rate": "0.001",
    "model.epochs": "100",
    "model.early_stopping_patience": "10",
    "model.validation_split": "0.2",
    "feature.window_size": "24",
    "feature.stride": "1",
    "feature.normalization": "true",
    "feature.feature_columns": "temperature,humidity,pressure,wind_speed,wind_direction",
    "training.data_path": "/data/training",
    "training.model_save_path": "/models",
    "training.checkpoint_path": "/checkpoints",
    "training.tensorboard_path": "/logs/tensorboard",
    "training.early_stopping_metric": "val_loss",
    "training.early_stopping_mode": "min"
}

def setup_apollo_test_config():
    """设置 Apollo 测试配置"""
    # 读取 YAML 文件
    with open("tests/test_apollo_config.yaml", "r") as f:
        yaml_config = yaml.safe_load(f)

    # 将 YAML 配置转换为扁平化的键值对
    flat_config = {}
    def flatten_dict(d, prefix=""):
        for k, v in d.items():
            if isinstance(v, dict):
                flatten_dict(v, f"{prefix}{k}.")
            elif isinstance(v, list):
                flat_config[f"{prefix}{k}"] = ",".join(map(str, v))
            else:
                flat_config[f"{prefix}{k}"] = str(v)

    flatten_dict(yaml_config)

    # 发布配置到 Apollo
    config_url = f"{APOLLO_TEST_SERVER}/openapi/v1/apps/{APOLLO_APP_ID}/clusters/default/namespaces/{APOLLO_NAMESPACE}/items"
    headers = {"Content-Type": "application/json"}
    
    for key, value in flat_config.items():
        item_data = {
            "key": key,
            "value": value,
            "comment": f"Test config for {key}"
        }
        try:
            response = requests.post(config_url, json=item_data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error setting config {key}: {e}")

    # 发布配置
    release_url = f"{APOLLO_TEST_SERVER}/openapi/v1/apps/{APOLLO_APP_ID}/clusters/default/namespaces/{APOLLO_NAMESPACE}/releases"
    release_data = {
        "releaseTitle": "Test Release",
        "releaseComment": "Test release for integration tests",
        "releasedBy": "test"
    }
    try:
        response = requests.post(release_url, json=release_data, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error releasing config: {e}")

@pytest.fixture(scope="session", autouse=True)
def setup_apollo():
    """设置 Apollo 测试环境"""
    try:
        setup_apollo_test_config()
        yield
    except requests.exceptions.ConnectionError:
        pytest.skip("Apollo server is not available")

class TestApolloSettingsSource:
    """Test ApolloSettingsSource."""

    def test_apollo_settings_source_init(self):
        """Test ApolloSettingsSource initialization."""
        class TestSettings(BaseSettings):
            pass

        source = ApolloSettingsSource(
            TestSettings,
            app_id=APOLLO_APP_ID,
            namespace=APOLLO_NAMESPACE,
            server_url=APOLLO_TEST_SERVER
        )
        
        assert source._apollo_mapping._app_id == APOLLO_APP_ID
        assert source._apollo_mapping._namespace == APOLLO_NAMESPACE
        assert source._apollo_mapping._server_url == APOLLO_TEST_SERVER

    def test_apollo_settings_source_load_configs(self):
        """Test loading configurations from Apollo."""
        class TestSettings(BaseSettings):
            pass

        source = ApolloSettingsSource(
            TestSettings,
            app_id=APOLLO_APP_ID,
            namespace=APOLLO_NAMESPACE,
            server_url=APOLLO_TEST_SERVER
        )
        
        # Force load configs
        source._apollo_mapping._load_configs()
        
        # Verify configs are loaded
        assert source._apollo_mapping["database.host"] == "localhost"
        assert source._apollo_mapping["database.port"] == "5432"
        assert source._apollo_mapping["app.name"] == "test_app"
        assert source._apollo_mapping["app.debug"] == "true"

    def test_apollo_settings_source_with_pydantic_model(self):
        """Test Apollo settings with Pydantic model."""
        class DatabaseConfig(BaseModel):
            host: str
            port: int
            user: str
            password: str
            pool_size: int
            pool_timeout: int
            pool_recycle: int

        class AppConfig(BaseModel):
            name: str
            debug: bool
            log_level: str
            workers: int
            timeout: int

        class RedisConfig(BaseModel):
            host: str
            port: int
            db: int
            password: str
            pool_size: int

        class ModelConfig(BaseModel):
            batch_size: int
            learning_rate: float
            epochs: int
            early_stopping_patience: int
            validation_split: float

        class FeatureConfig(BaseModel):
            window_size: int
            stride: int
            normalization: bool
            feature_columns: List[str]

        class TrainingConfig(BaseModel):
            data_path: str
            model_save_path: str
            checkpoint_path: str
            tensorboard_path: str
            early_stopping_metric: str
            early_stopping_mode: str

        class TestSettings(BaseSettings):
            database: DatabaseConfig
            app: AppConfig
            redis: RedisConfig
            model: ModelConfig
            feature: FeatureConfig
            training: TrainingConfig

            @classmethod
            def settings_customise_sources(
                cls,
                settings_cls: type[BaseSettings],
                init_settings: PydanticBaseSettingsSource,
                env_settings: PydanticBaseSettingsSource,
                dotenv_settings: PydanticBaseSettingsSource,
                file_secret_settings: PydanticBaseSettingsSource,
            ) -> tuple[PydanticBaseSettingsSource, ...]:
                return (ApolloSettingsSource(settings_cls, app_id=APOLLO_APP_ID, namespace=APOLLO_NAMESPACE, server_url=APOLLO_TEST_SERVER),)

        settings = TestSettings()
        
        # 验证数据库配置
        assert settings.database.host == "localhost"
        assert settings.database.port == 5432
        assert settings.database.user == "test_user"
        assert settings.database.password == "test_password"
        assert settings.database.pool_size == 20
        assert settings.database.pool_timeout == 30
        assert settings.database.pool_recycle == 3600

        # 验证应用配置
        assert settings.app.name == "test_app"
        assert settings.app.debug is True
        assert settings.app.log_level == "INFO"
        assert settings.app.workers == 4
        assert settings.app.timeout == 30

        # 验证 Redis 配置
        assert settings.redis.host == "localhost"
        assert settings.redis.port == 6379
        assert settings.redis.db == 0
        assert settings.redis.password == "redis_password"
        assert settings.redis.pool_size == 10

        # 验证模型配置
        assert settings.model.batch_size == 32
        assert settings.model.learning_rate == 0.001
        assert settings.model.epochs == 100
        assert settings.model.early_stopping_patience == 10
        assert settings.model.validation_split == 0.2

        # 验证特征配置
        assert settings.feature.window_size == 24
        assert settings.feature.stride == 1
        assert settings.feature.normalization is True
        assert settings.feature.feature_columns == ["temperature", "humidity", "pressure", "wind_speed", "wind_direction"]

        # 验证训练配置
        assert settings.training.data_path == "/data/training"
        assert settings.training.model_save_path == "/models"
        assert settings.training.checkpoint_path == "/checkpoints"
        assert settings.training.tensorboard_path == "/logs/tensorboard"
        assert settings.training.early_stopping_metric == "val_loss"
        assert settings.training.early_stopping_mode == "min"

    def test_apollo_settings_source_notification_update(self):
        """Test configuration update through notification."""
        class TestSettings(BaseSettings):
            pass

        source = ApolloSettingsSource(
            TestSettings,
            app_id=APOLLO_APP_ID,
            namespace=APOLLO_NAMESPACE,
            server_url=APOLLO_TEST_SERVER,
            refresh_interval=1
        )
        
        # Initial load
        source._apollo_mapping._load_configs()
        assert source._apollo_mapping["database.host"] == "localhost"
        
        # Update config in Apollo
        config_url = f"{APOLLO_TEST_SERVER}/openapi/v1/apps/{APOLLO_APP_ID}/clusters/default/namespaces/{APOLLO_NAMESPACE}/items"
        update_data = {
            "key": "database.host",
            "value": "new-host",
            "comment": "Update host for test"
        }
        headers = {"Content-Type": "application/json"}
        requests.post(config_url, json=update_data, headers=headers)
        
        # Release update
        release_url = f"{APOLLO_TEST_SERVER}/openapi/v1/apps/{APOLLO_APP_ID}/clusters/default/namespaces/{APOLLO_NAMESPACE}/releases"
        release_data = {
            "releaseTitle": "Update Test",
            "releaseComment": "Update host for test",
            "releasedBy": "test"
        }
        requests.post(release_url, json=release_data, headers=headers)
        
        # Wait for notification
        import time
        time.sleep(2)
        
        # Verify update
        assert source._apollo_mapping["database.host"] == "new-host"

    def test_apollo_settings_source_error_handling(self):
        """Test error handling in Apollo settings."""
        class TestSettings(BaseSettings):
            pass

        source = ApolloSettingsSource(
            TestSettings,
            app_id="non-existent-app",
            namespace=APOLLO_NAMESPACE,
            server_url=APOLLO_TEST_SERVER
        )
        
        # Should not raise exception
        source._apollo_mapping._load_configs()
        assert len(source._apollo_mapping) == 0 