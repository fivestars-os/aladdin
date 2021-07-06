import subprocess
import os

class K3d:

    def import_images(self, images):
        subprocess.check_call(["k3d", "image", "import", "-c", os.environ["CLUSTER_CODE"], *images])
