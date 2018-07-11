#!/usr/bin/env python3
import base64
import logging
import subprocess
from collections import namedtuple

class Tag(namedtuple('Tag', ['name', 'tag'])):
    def __str__(self):
        return f'{self.name}:{self.tag}'


class DockerCommands(object):

    def build(self, context, hash):
        tag = Tag(context.name, hash)
        local_tag = Tag(context.name, 'local')

        cmd_list = ['docker', 'build', '-f', context.dockerfile, '-t', str(tag), '-t',
                    str(local_tag), context.context]
        subprocess.check_call(cmd_list)

        return tag

    def publish(self, publish_rules, local_tag, login=True):
        # TODO cache the describe repositories
        repo = self.get_or_create_repo(publish_rules, local_tag.name)
        full_path = f'{repo["repositoryUri"]}:{local_tag.tag}'

        cmd_list = ['docker', 'tag', str(local_tag), full_path]
        subprocess.check_call(cmd_list)
        if login:
            self.login(publish_rules)
        cmd_list = ['docker', 'push', full_path]
        subprocess.check_call(cmd_list)
        return full_path

    def login(self, publish_rules):
        # TODO cache the login
        token_data = publish_rules.ecr.get_authorization_token()['authorizationData'][0]
        user, password = str(base64.decodebytes(bytes(
            token_data['authorizationToken'], 'ascii')), 'ascii').split(':')
        proxy = token_data['proxyEndpoint']

        cmd_list = [
            'docker', 'login',
            '-u', user,
            '-p', password,
            proxy
        ]
        subprocess.check_call(cmd_list)

    def get_or_create_repo(self, publish_rules, repo_name):
        try:
            repo = publish_rules.ecr.describe_repositories(repositoryNames=[repo_name])['repositories'][0]
        except Exception as e:
            # botocore.errorfactory.RepositoryNotFoundException, but can't import it
            logging.info(f'No repository of name {repo_name} exists on ECR, creating...')
            repo = publish_rules.ecr.create_repository(repositoryName=repo_name)['repository']
            logging.info(f'Successfully created repository {repo_name} on ECR')
        return repo
