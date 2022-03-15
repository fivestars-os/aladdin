#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from os.path import join

import yaml
from botocore.exceptions import ClientError

from aladdin.lib import logging

logger = logging.getLogger(__name__)


class Helm:
    PACKAGE_DIR_PATH = "helm_charts/0.0.0/{project_name}/{git_ref}/"
    PACKAGE_PATH = "helm_charts/0.0.0/{project_name}/{git_ref}/{chart_name}.{git_ref}.tgz"

    def publish(self, project_name, publish_rules, chart_path, git_hash):

        version = f"0.0.0+{git_hash}"

        logger.info("Building package")

        with open(os.path.join(chart_path, "Chart.yaml")) as chart_manifest:
            chart_name = yaml.safe_load(chart_manifest)["name"]

        subprocess.check_call([
            "helm",
            "package",
            "--version",
            version,
            "--app-version",
            git_hash,
            chart_path
        ], cwd=chart_path)

        try:
            package_path = join(chart_path, "{}-{}.tgz".format(chart_name, version))
            bucket_path = self.PACKAGE_PATH.format(
                project_name=project_name, chart_name=chart_name, git_ref=git_hash
            )

            logger.info("Uploading %s chart to %s", chart_name, bucket_path)
            publish_rules.s3_bucket.upload_file(package_path, bucket_path)
        finally:
            os.remove(package_path)

    def pull_packages(self, project_name, publish_rules, git_ref, extract_dir, chart_name=None):
        """
        Retrieve all charts published for this project at this git_ref.

        This will download all the published charts and extract them to extract_dir.

        :param project_name: The name of the aladdin project being retrieved.
        :param publish_rules: Details for accessing the S3 bucket.
        :param git_ref: The version of the chart(s) to retrieve.
        :param extract_dir: Where to place the downloaded charts.
        :param chart_name: Specific chart to pull.
        """
        # List the contents of the publish "directory" and find
        # everything that looks like a chart.
        package_keys = [
            obj.key
            for obj in publish_rules.s3_bucket.objects.filter(
                Prefix=self.PACKAGE_DIR_PATH.format(project_name=project_name, git_ref=git_ref)
            )
            if obj.key.endswith(f"{chart_name}.{git_ref}.tgz" if chart_name else f".{git_ref}.tgz")
        ]

        if not package_keys:
            logger.error(f"No published charts found for: {chart_name or project_name} in {project_name}@{git_ref}")
            sys.exit(1)

        # Download the chart archives and extract the contents into their own chart sub-directories
        for package_key in package_keys:
            downloaded_package = join(extract_dir, os.path.basename(package_key))
            try:
                publish_rules.s3_bucket.download_file(package_key, downloaded_package)
            except ClientError:
                logger.error("Error downloading from S3: {}".format(package_key))
                raise
            else:
                subprocess.check_call(["tar", "-xvzf", downloaded_package, "-C", extract_dir])
            finally:
                try:
                    os.remove(downloaded_package)
                except FileNotFoundError:
                    pass

    def find_values(self, chart_path, cluster_name, namespace):
        """
        Find all possible values yaml files for override in increasing priority
        Values and overrides are defined/specified in helm args in a specific order
        1. project values.yaml (picked up by helm automatically)
        2. project cluster values.yaml
        3. project cluster namespace values.yaml
        4. site.yaml file (on local)
        5. aladdin-config default `values.yaml`
        6. aladdin-config cluster `values.yaml`
        7. aladdin-config cluster namespace `values.yaml`
        8. user passed overrides
        """
        values = []
        # cluster_name could be an alias, "CLUSTER_CODE" is what is used in aladdin-config
        cluster_code = os.environ["CLUSTER_CODE"]

        cluster_values_path = join(chart_path, "values", f"values.{cluster_name}.yaml")
        if os.path.isfile(cluster_values_path):
            logger.info("Found cluster values file")
            values.append(cluster_values_path)

        cluster_namespace_values_path = join(
            chart_path, "values", f"values.{cluster_name}.{namespace}.yaml"
        )
        if os.path.isfile(cluster_namespace_values_path):
            logger.info("Found cluster namespace values file")
            values.append(cluster_namespace_values_path)

        site_values_path = join(chart_path, "values", "site.yaml")  # Only usable on LOCAL
        if cluster_name == "LOCAL" and os.path.isfile(site_values_path):
            logger.info("Found site values file")
            values.append(site_values_path)

        aladdin_config_values_path = os.path.join(
            os.environ["ALADDIN_CONFIG_DIR"],
            "default",
            "values.yaml"
        )
        if os.path.isfile(aladdin_config_values_path):
            logger.info("Found aladdin config values file")
            values.append(aladdin_config_values_path)

        cluster_config_values_path = os.path.join(
            os.environ["ALADDIN_CONFIG_DIR"],
            cluster_code,
            "values.yaml"
        )
        if os.path.isfile(cluster_config_values_path):
            logger.info("Found cluster config values file")
            values.append(cluster_config_values_path)

        cluster_namespace_config_values_path = os.path.join(
            os.environ["ALADDIN_CONFIG_DIR"],
            cluster_code,
            "namespace-overrides",
            namespace,
            "values.yaml"
        )
        if os.path.isfile(cluster_namespace_config_values_path):
            logger.info("Found cluster namespace config values file")
            values.append(cluster_namespace_config_values_path)

        return values

    def stop(self, release_name, namespace):

        command = ["helm", "delete", release_name, "--namespace", namespace]

        if self.release_exists(release_name, namespace):
            subprocess.run(command, check=True)
            logger.info("Successfully removed release {}".format(release_name))
        else:
            logger.warning(
                "Could not remove release {} because it doesn't exist".format(release_name)
            )

    def release_exists(self, release_name, namespace):
        command = ["helm", "status", release_name, "--namespace", namespace]

        ret_code = subprocess.run(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        # If return code is 0, release exists
        if ret_code == 0:
            return True
        else:
            return False

    def rollback_relative(self, release_name, num_versions, namespace):

        helm_list_command = ["helm", "list", "--namespace", namespace, "-o", "json"]
        output = json.loads(subprocess.run(helm_list_command, capture_output=True).stdout)
        current_revision = int([k["revision"] for k in output if k["name"] == release_name][0])

        if num_versions > current_revision:
            logger.warning("Can't rollback that far")
            return

        self.rollback(release_name, current_revision - num_versions, namespace)

    def rollback(self, release_name, revision, namespace):
        command = ["helm", "rollback", release_name, str(revision), "--namespace", namespace]
        subprocess.run(command, check=True)

    def upgrade(
        self,
        release_name: str,
        chart_path: str,
        cluster_name: str,
        namespace: str,
        force=False,
        dry_run=False,
        helm_args: list = None,
        **values,
    ):
        if helm_args is None:
            helm_args = []
        if force:
            helm_args.append("--force")
        if dry_run:
            helm_args.extend(["--dry-run", "--debug"])
        command = [
            "upgrade",
            release_name,
            chart_path,
            "--install",
            f"--namespace={namespace}",
        ]

        command = self.prepare_command(
            command, chart_path, cluster_name, namespace, helm_args=helm_args, **values
        )

        logger.info("Executing: %s", " ".join(command))
        return subprocess.run(["helm", *command], check=True)

    def prepare_command(
        self,
        base_command: list,
        chart_path: str,
        cluster_name: str,
        namespace: str,
        helm_args: list = None,
        **values,
    ):
        for path in self.find_values(chart_path, cluster_name, namespace):
            base_command.append("--values={}".format(path))

        for set_name, set_val in values.items():
            base_command.extend(["--set", "{}={}".format(set_name, set_val)])

        if helm_args:
            base_command.extend(helm_args)

        return base_command
