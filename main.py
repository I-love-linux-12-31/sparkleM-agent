# SparkleM agent
# dec 2024 Yaroslav Kuznetsov
import base64
import os
import importlib

import time
import socket
import json
from confluent_kafka import Producer
from datetime import datetime

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP


import config

plugins = {}
plugins_dir = './plugins'
PLUGIN_REQUIRED_ATTRS = ["NAME", "VERSION", "AUTHOR", "get_payload"]


def serialize(value):
    return json.dumps(value).encode('utf-8')


def encrypt_message(message, public_key):
    # Шифрование сообщения
    key = RSA.import_key(public_key)
    cipher = PKCS1_OAEP.new(key)
    return cipher.encrypt(message.encode())



def reload_plugins():
    global plugins
    plugins.clear()

    for package_name in os.listdir(plugins_dir):
        package_path = os.path.join(plugins_dir, package_name)
        if os.path.isdir(package_path):
            try:
                package = importlib.import_module(f'plugins.{package_name}')

                if all({hasattr(package, attr) for attr in PLUGIN_REQUIRED_ATTRS}):
                    if package.NAME in plugins:
                        print(F"[\033[33mWARN\033[0m]: Обнаружен плагин, с уже занятым именем, но отличным пакетом. Будет использована более новая версия плагина(согласно манифесту)")
                        if plugins[package.NAME].VERSION <= package.VERSION:
                            plugins[package.NAME] = package
                    else:
                        plugins[package.NAME] = package
                    print(f"+ {package.NAME}, {package.VERSION} от {package.AUTHOR}")
                else:
                    print(f"В пакете {package_name} отсутствует один из обязательных аттрибутов: "
                          f"{', '.join(attr for attr in PLUGIN_REQUIRED_ATTRS if not hasattr(package, attr))}")
            except ImportError as e:
                print(f"Не удалось импортировать пакет {package_name}: {e}")
            except AttributeError as e:
                print(f"В пакете {package_name} отсутствует get_payload или манифест некорректен: {e}")
            except Exception as e:
                print(f"При загрузке пакета {package_name} произошла ошибка: {e}")
    print("Импортированные плагины:", plugins)

def work_function():
    kafka_config = {
        'bootstrap.servers': F'{config.config["mq_server_address"]}:{config.config["mq_server_port"]}',
        # 'group.id': 'mygroup',
        'auto.offset.reset': 'earliest'
    }

    producer = Producer(kafka_config)
    hostname = socket.gethostname()  # Получаем имя хоста
    while True:
        # Формируем сообщение для отправки
        for plugin_name in plugins:
            plugin = plugins[plugin_name]
            data = plugins[plugin_name].get_payload()
            for key in data:
                # print(f"{key}: {data[key]}")
                payload = {
                    "plugin": plugin.NAME,
                    "key": key,
                    "value": data[key],
                }
                serialized_payload = json.dumps(payload)


                message = {
                    "config_id": config.config["id"],
                    "hostname": hostname,
                    "datetime": datetime.now().isoformat(),
                    "payload": base64.b64encode(encrypt_message(serialized_payload, config.pubkey)).decode('utf-8'),
                }

                # Отправляем сообщение в Kafka
                # producer.send(plugin.TOPIC, message)

                producer.produce(plugin.TOPIC, value=serialize(message))
                producer.flush()
                print(f"Data sent: {message}")

        # Ожидаем следующий цикл
        time.sleep(config.config["send_data_interval"])


def main():
    print("[INF] Загрузка конфигурации...")
    config.load_config()
    reload_plugins()
    plugins_unpack = False
    for plugin in config.config["required_plugins"]:
        if plugin not in plugins:
            plugins_unpack = True
            break
    if plugins_unpack:
        print("[INF] Установка недостающих плагинов...")
        config.unpack_plugins()
        reload_plugins()

    work_function()



if __name__ == '__main__':
    main()
