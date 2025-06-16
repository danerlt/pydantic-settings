#!/usr/bin/env python  
# -*- coding:utf-8 -*-  
""" 
@author: danerlt 
@file: test_pyapollo
@time: 2025-06-16
@contact: danerlt001@gmail.com
"""
import time

from pydantic_settings.sources.providers.apollo.client import ApolloClient

# 将配置对象传入客户端
client = ApolloClient(meta_server_address="http://localhost:8080",
                      app_id="aiem-incremental-learning",
                      namespaces=["dev.yml"],
                      )

index = 1
while True:
    index += 1
    print(index)
    print(client._cache)
    print(1, client.get_value("database", namespace="dev.yml"))
    print(2, client.get_value("database", namespace="dev.yml").get("host"))
    time.sleep(3)
