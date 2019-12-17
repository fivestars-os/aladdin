import json
import os


def load_cluster_configs():
    return load_config()['clusters']

def load_cluster_config(cluster):
    return load_config_from_file(f'{os.environ["ALADDIN_CONFIG_DIR"]}/{cluster}/config.json')

def load_namespace_override_config(cluster, namespace):
    return load_config_from_file(f'{os.environ["ALADDIN_CONFIG_DIR"]}/{cluster}/'
        f'namespace-overrides/{namespace}/config.json')

def load_publish_configs():
    return load_config()['publish']


def load_kubernetes_configs():
    return load_config()['kubernetes']


def load_git_configs():
    return load_config()['git']


def load_config_from_file(file): 
    with open(file) as json_file:
        json_data = json.load(json_file)
    return json_data

def load_config():
    return load_config_from_file(f'{os.environ["ALADDIN_CONFIG_DIR"]}/config.json')
