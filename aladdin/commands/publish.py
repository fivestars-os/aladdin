import logging
import subprocess
import tempfile
from itertools import product

from aladdin.config import load_git_configs
from aladdin.lib.docker import DockerCommands, Tag
from aladdin.lib.git import Git
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.utils import working_directory
from aladdin.lib.project_conf import ProjectConf
from aladdin.lib.publish_rules import PublishRules
from aladdin.lib.arg_tools import container_command


def parse_args(sub_parser):

    subparser = sub_parser.add_parser(
        "publish", help="Build the docker and helm package and publish to ecr and S3"
    )
    exclude_steps_group = subparser.add_mutually_exclusive_group()
    exclude_steps_group.add_argument(
        "--build-only",
        action="store_true",
        help="only builds docker images in your minikube env with hash and timestamp as tags",
    )
    exclude_steps_group.add_argument(
        "--build-publish-ecr-only",
        action="store_true",
        help="only build and publish docker images to ecr",
    )
    exclude_steps_group.add_argument(
        "--publish-helm-only",
        action="store_true",
        help=(
            "only publish helm chart to s3. WARNING: make sure you build"
            " and publish the docker images to ecr before deploying"
        ),
    )
    clean_options_groups = subparser.add_mutually_exclusive_group()
    clean_options_groups.add_argument(
        "--build-local",
        action="store_true",
        help="do a local docker build rather than pulling cleanly from git",
    )

    remote_options_group = subparser.add_argument_group("remote options")
    remote_options_group.add_argument(
        "--repo",
        help="which git repo to pull from, which should be used if it differs from chart name",
    )
    remote_options_group.add_argument(
        "--git-ref", help="which commit hash or branch or tag to checkout and publish from"
    )
    remote_options_group.add_argument(
        "--init-submodules",
        action="store_true",
        help="recursively initialize and update all submodules included in the project",
    )
    subparser.add_argument(
        "--helm2",
        action="store_true",
        help="Use helm2 instead of helm3",
    )

    clean_options_groups.add_argument_group(remote_options_group)

    subparser.set_defaults(func=publish_args)


@container_command
def publish_args(args):
    if args.build_local:
        publish(args.build_only, args.build_publish_ecr_only, args.publish_helm_only, args.helm2)
    else:
        publish_clean(
            args.build_only,
            args.build_publish_ecr_only,
            args.publish_helm_only,
            args.repo,
            args.git_ref,
            args.init_submodules,
            args.helm2
        )


def publish(build_only, build_publish_ecr_only, publish_helm_only, helm2=False):
    pc = ProjectConf()
    pr = PublishRules()
    d = DockerCommands()
    h = Helm(helm2)

    # tags is a list in case we want to add other tags in the future
    tags = [Git.get_hash()]

    if not publish_helm_only:
        for tag in tags:
            env = {"HASH": tag}
            pc.build_docker(env)
        if not build_only:
            images = pc.get_docker_images()
            image_tags = [Tag(image, tag) for image, tag in product(images, tags)]
            asso = {}
            d.login(pr)
            for image_tag in image_tags:
                res = d.publish(pr, image_tag, login=False)
                asso[image_tag] = res

    if not build_only and not build_publish_ecr_only:
        hash = tags[0]
        for path in pc.get_helm_chart_paths():
            h.publish(pc.name, pr, path, hash)
    logging.info(f"Ran publish on {pc.name} with git hash: {tags[0]}")


def publish_clean(
    build_only, build_publish_ecr_only, publish_helm_only, repo, git_ref, init_submodules, helm2=False
):
    g = Git()
    git_account = load_git_configs()["account"]
    repo = repo or ProjectConf().name
    git_url = f"git@github.com:{git_account}/{repo}.git"
    ref = git_ref or g.get_full_hash()
    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            g.clone(git_url, tmpdirname)
        except subprocess.CalledProcessError:
            logging.warn(f"Could not clone repo {git_url}. Does it exist?")
            return
        try:
            g.checkout(tmpdirname, ref)
        except subprocess.CalledProcessError:
            logging.warn(
                f"Could not checkout to ref {ref} in repo {git_url}. Have you pushed it to remote?"
            )
            return
        if init_submodules:
            try:
                g.init_submodules(tmpdirname)
            except subprocess.CalledProcessError:
                logging.warn(
                    "Could not initialize submodules. Make sure you use ssh urls in"
                    " the .gitmodules folder and double check your credentials."
                )
                return
        with working_directory(tmpdirname):
            publish(build_only, build_publish_ecr_only, publish_helm_only, helm2)
