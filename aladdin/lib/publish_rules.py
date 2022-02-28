import boto3

from aladdin.config import load_publish_configs
from aladdin.lib.utils import singleton


@singleton
class PublishRules:
    def __init__(self):
        publish_configs = load_publish_configs()
        boto = boto3.Session(profile_name=publish_configs["aws_profile"])
        self.docker_registry = publish_configs["docker_ecr_repo"]
        self.s3_bucket = boto.resource("s3").Bucket(publish_configs["s3_helm_chart_bucket"])
        self.ecr = boto.client("ecr")
