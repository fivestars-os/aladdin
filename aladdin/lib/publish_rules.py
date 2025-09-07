import boto3

from aladdin.lib.utils import singleton


@singleton
class PublishRules:
    def __init__(self):
        boto = boto3.Session()
        self.ecr = boto.client("ecr")
