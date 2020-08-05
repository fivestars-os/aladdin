#!/usr/bin/env python3
import os
import subprocess
import logging

from botocore.exceptions import ClientError
from os.path import join, dirname, expanduser

logger = logging.getLogger(__name__)


class Helm(object):
    PACKAGE_PATH = "helm_charts/0.0.0/{project_name}/{git_ref}/{project_name}.{git_ref}.tgz"
    VALUE_PATH = "helm_charts/0.0.0/{project_name}/{git_ref}/values.{values_name}.yaml"

    @property
    def helm_home(self):
        return join(expanduser("~"), ".helm")

    def init(self):
        # We need to have local helm initialized for it to works
        subprocess.check_call(["helm", "init", "--client-only"])

    def publish(self, name, publish_rules, helm_path, hash):

        # HelmContext = namedtuple('HelmContext', ['chart_home', 'values_files', 'name'])

        version = "0.0.0"

        logger.info("Building package")
        self.init()

        subprocess.check_call(
            ["helm", "package", "--version", version, name], cwd=dirname(helm_path)
        )
        package_path = join(dirname(helm_path), "{}-{}.tgz".format(name, version))
        bucket_path = self.PACKAGE_PATH.format(project_name=name, git_ref=hash)

        logger.info("Uploading chart")
        publish_rules.s3_bucket.upload_file(package_path, bucket_path)
        os.remove(package_path)

    def pull_package(self, project_name, publish_rules, git_ref, extract_dir):
        extract_loc = "{}/{}.tgz".format(extract_dir, project_name)
        try:
            publish_rules.s3_bucket.download_file(
                self.PACKAGE_PATH.format(project_name=project_name, git_ref=git_ref), extract_loc
            )
        except ClientError:
            logger.error(
                "Error downloading from S3: {}".format(
                    self.PACKAGE_PATH.format(project_name=project_name, git_ref=git_ref)
                )
            )
            raise
        subprocess.check_call(["tar", "-xvzf", extract_loc, "-C", extract_dir])

    def find_values(self, chart_path, cluster_name, namespace):

        values = []

        # Find all possible values yaml files for override in increasing priority
        cluster_values_path = join(chart_path, "values", "values.{}.yaml".format(cluster_name))
        cluster_namespace_values_path = join(
            chart_path, "values", "values.{}.{}.yaml".format(cluster_name, namespace)
        )
        site_values_path = join(chart_path, "values", "site.yaml")  # Only usable on LOCAL

        if os.path.isfile(cluster_values_path):
            logger.info("Found cluster values file")
            values.append(cluster_values_path)

        if os.path.isfile(cluster_namespace_values_path):
            logger.info("Found cluster namespace values file")
            values.append(cluster_namespace_values_path)

        if cluster_name == "LOCAL" and os.path.isfile(site_values_path):
            logger.info("Found site values file")
            values.append(site_values_path)

        return values

    def stop(self, helm_rules):
        release_name = helm_rules.release_name

        command = ["helm", "delete", "--purge", release_name]

        if self.release_exists(release_name):
            subprocess.run(command, check=True)
            logger.info("Successfully removed release {}".format(release_name))
        else:
            logger.warning(
                "Could not remove release {} because it doesn't exist".format(release_name)
            )

    def release_exists(self, release_name):
        command = ["helm", "status", release_name]
        ret_code = subprocess.run(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        # If return code is 0, release exists
        if ret_code == 0:
            return True
        else:
            return False

    def rollback_relative(self, helm_rules, num_versions):
        release_name = helm_rules.release_name

        # Some ugly logic to get the current revision - probably can be better
        output = subprocess.Popen(("helm", "list"), stdout=subprocess.PIPE)
        output = subprocess.check_output(("grep", release_name), stdin=output.stdout)
        current_revision = int(output.decode("utf-8").replace(" ", "").split("\t")[1])

        if num_versions > current_revision:
            logger.warning("Can't rollback that far")
            return

        self.rollback(helm_rules, current_revision - num_versions)

    def rollback(self, helm_rules, revision):
        release_name = helm_rules.release_name
        command = ["helm", "rollback", release_name, str(revision)]
        subprocess.run(command, check=True)

    def start(
        self, helm_rules, chart_path, cluster_name, namespace, force=False, helm_args=None, **values
    ):
        if helm_args is None:
            helm_args = []
        if force:
            helm_args.append("--force")
        return self._run(helm_rules, chart_path, cluster_name, namespace, helm_args, **values)

    def dry_run(self, helm_rules, chart_path, cluster_name, namespace, helm_args=None, **values):
        if helm_args is None:
            helm_args = []
        helm_args += ["--dry-run", "--debug"]
        return self._run(helm_rules, chart_path, cluster_name, namespace, helm_args, **values)

    def _run(self, helm_rules, chart_path, cluster_name, namespace, helm_args=None, **values):
        release_name = helm_rules.release_name

        command = [
            "helm",
            "upgrade",
            release_name,
            chart_path,
            "--install",
            "--namespace={}".format(namespace),
        ]

        for path in self.find_values(chart_path, cluster_name, namespace):
            command.append("--values={}".format(path))

        for set_name, set_val in values.items():
            command.extend(["--set", "{}={}".format(set_name, set_val)])

        if helm_args:
            command.extend(helm_args)

        logger.info("Executing: " + " ".join(command))
        subprocess.run(command, check=True)
