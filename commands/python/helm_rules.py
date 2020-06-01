class HelmRules(object):
    def __init__(self, cluster_rules, project_name):
        self._cluster_rules = cluster_rules
        self._project_name = project_name

    @property
    def release_name(self):
        # TODO there is a limit on the name size, we should check that
        return "{0}-{1}".format(self._project_name, self._cluster_rules.namespace)

    def helm_values(self):
        return dict()
