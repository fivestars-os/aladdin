#!/usr/bin/env python3
from argparse import RawTextHelpFormatter
from arg_tools import add_namespace_argument
from command import refresh
from libs.k8s.kubernetes import Kubernetes
import logging


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('environment',
                                      help='Maniuplate configMap/environments of projects',
                                      formatter_class=RawTextHelpFormatter,
                                      epilog=('Example usage:\n'
                                              'aladdin -c CLUSTER -n NAMESPACE environment '
                                              'CONFIGMAP get\n'
                                              'aladdin -c CLUSTER -n NAMESPACE environment '
                                              'CONFIGMAP set --args a=1 b=2 --refresh DEPLOYMENT1 '
                                              'DEPLOYMENT2\n'
                                              'aladdin -c CLUSTER -n NAMESPACE environment '
                                              'CONFIGMAP unset --args a b'))
    add_namespace_argument(subparser)
    subparser.add_argument('app', help='the values of the label app for the configMap')
    subparser.add_argument('command', help='how to maniuplate the env',
                           choices=['set', 'unset', 'get'])
    subparser.add_argument('--args', nargs='+', help=('which key/value pairs to add to environment '
                                                      'for set, or which keys to remove from '
                                                      'environment for unset'))
    subparser.add_argument('--refresh', help='which deployments to refresh', nargs='*')
    subparser.set_defaults(func=environment_args)


def environment_args(args):
    if args.command == 'set':
        env_set(args.app, args.args, args.refresh, args.namespace)
    if args.command == 'unset':
        env_unset(args.app, args.args, args.refresh, args.namespace)
    if args.command == 'get':
        env_get(args.app, args.namespace)


def env_get(app, namespace=None):
    k = Kubernetes(namespace=namespace)
    env_vars = k.get_config_map(app).data
    print("\nEnvironment values for {}:".format(app))
    for var, val in env_vars.items():
        print('  {0}:  {1}'.format(var, val))
    print("\n")


def env_set(app, key_vals, refresh_deploys, namespace=None):
    k = Kubernetes(namespace=namespace)
    config_map = k.get_config_map(app)
    if not key_vals:
        return
    key_vals = {key_val[0]: key_val[1] for key_val in map(lambda x: x.split('='), key_vals)}
    data = config_map.data
    data.update(key_vals)
    k.update_config_map(config_map.metadata.name, config_map)
    logging.info("Updated configmap {} to:".format(config_map.metadata.name))
    env_get(app)

    # Check if refresh was passed
    if refresh_deploys is not None:
        # Check if refresh is not empty
        if refresh_deploys:
            refresh.refresh(refresh_deploys, namespace)
        # If refresh is empty, assume we want to reload only app
        else:
            refresh.refresh([app], namespace)


def env_unset(app, remove_keys, refresh_deploys, namespace=None):
    k = Kubernetes(namespace=namespace)
    config_map = k.get_config_map(app)
    data = config_map.data
    for key in remove_keys:
        if data.get(key):
            data.pop(key)
        else:
            logging.warning('{0} doesn\'t exist in {1}\'s configMap'.format(key, app))
    k.update_config_map(config_map.metadata.name, config_map)
    logging.info("Updated configmap {} to:".format(config_map.metadata.name))
    env_get(app)

    # Check if refresh was passed
    if refresh_deploys is not None:
        # Check if refresh is not empty
        if refresh_deploys:
            refresh.refresh(refresh_deploys, namespace)
        # If refresh is empty, assume we want to reload only app
        else:
            refresh.refresh([app], namespace)
