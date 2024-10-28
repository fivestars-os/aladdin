#!/usr/bin/env python3
import json
import os
import subprocess
from os.path import join
from typing import List

from aladdin.lib import logging

logger = logging.getLogger(__name__)


class Helm:
    def find_values(self, chart_path: str, values_files: List[str], namespace: str):
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

        for values_file in values_files:
            cluster_values_path = join(chart_path, "values", f"values.{values_file}.yaml")
            if os.path.isfile(cluster_values_path):
                logger.info("Found cluster values file")
                values.append(cluster_values_path)

            cluster_namespace_values_path = join(
                chart_path, "values", f"values.{values_file}.{namespace}.yaml"
            )
            if os.path.isfile(cluster_namespace_values_path):
                logger.info("Found cluster namespace values file")
                values.append(cluster_namespace_values_path)

            cluster_custom_values_path = join(
                chart_path, "values", values_file
            )
            if os.path.isfile(cluster_custom_values_path):
                logger.info("Found cluster custom values file")
                values.append(cluster_custom_values_path)

        site_values_path = join(chart_path, "values", "site.yaml")  # Only usable on LOCAL
        if cluster_code == "LOCAL" and os.path.isfile(site_values_path):
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
        values_files: List[str],
        namespace: str,
        force=False,
        dry_run=False,
        helm_args: list = None,
        all_values=True,
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
        if all_values:
            command.append(f"--values={chart_path}/values.yaml")

        command = self.prepare_command(
            command, chart_path, values_files, namespace, helm_args=helm_args, **values
        )

        logger.info("Executing: %s", " ".join(command))
        return subprocess.run(["helm", *command], check=True)

    def prepare_command(
        self,
        base_command: list,
        chart_path: str,
        values_files: List[str],
        namespace: str,
        helm_args: list = None,
        **values,
    ):
        for path in self.find_values(chart_path, values_files, namespace):
            base_command.append("--values={}".format(path))

        for set_name, set_val in values.items():
            base_command.extend(["--set", "{}={}".format(set_name, set_val)])

        if helm_args:
            base_command.extend(helm_args)

        return base_command
