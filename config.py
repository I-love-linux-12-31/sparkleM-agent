import os
import yaml
import tarfile
import shutil
import subprocess

allowed_plugins = []
pubkey = b''
config = None


def load_config():
    global config, pubkey, allowed_plugins

    with tarfile.open('config.tar.xz', 'r:xz') as tar:
        # Загрузка config.yaml
        config_file = tar.extractfile('config.yaml')
        if config_file:
            config = yaml.safe_load(config_file)
            allowed_plugins = config['required_plugins']

        # Загрузка rsa_key.pub
        key_file = tar.extractfile('rsa_key.pub')
        if key_file:
            pubkey = key_file.read()


def unpack_plugins():
    plugins_dir = './plugins'

    # Распаковка плагинов
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    plugin_pkgs = set()

    with tarfile.open('config.tar.xz', 'r:xz') as tar:
        for member in tar.getmembers():
            if member.name.startswith('plugins/'):
                plugin_dir = member.name.split('/')[1]
                plugin_pkgs.add(plugin_dir)
                # plugin_path = os.path.join(plugins_dir, plugin_name)
                # if not os.path.exists(plugin_path):
                tar.extract(member, plugins_dir + "/..")
                # else:
                #     print(f"[INF] Целевой каталог занят. Плагин {plugin_name} не будет перезаписан!")



    for plugin in plugin_pkgs:
        plugin_path = os.path.join(plugins_dir, plugin)
        requirements_file = os.path.join(plugin_path, 'requirements.txt')

        if os.path.exists(requirements_file):
            with open(requirements_file, 'r') as f:
                if f.read().strip():
                    subprocess.run(['pip', 'install', '-r', requirements_file], check=True)
