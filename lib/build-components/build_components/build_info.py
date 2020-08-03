import abc
import dataclasses
import pathlib
import typing

import networkx

from .configuration import UNDEFINED, ComponentConfig, UserInfo


@dataclasses.dataclass
class BuildInfo(abc.ABC):
    """
    A wrapper around the component config and some other high-level info to make parameterizing
    the build process a bit simpler. The build functions should use sub-classes of this rather
    than directly accessing the config object.
    """

    project: str
    component_graph: networkx.DiGraph
    component: str
    config: ComponentConfig
    tag_hash: str
    default_language_version: str

    def component_packages(self, component=None) -> typing.List[str]:
        """
        Provide a list of apt packages required for building python dependencies.

        This packages will only be installed in the builder image used to build the specified
        component. For instance if a "commands" component depends on a "shared" component and the
        "commands" component requires some packages, they will only be installed in the
        builder-commands multi-stage builder image, not the build-shared image.

        :param component: The component to check for package dependencies, defaults to the current
                          component.
        :returns: The list of packages to be installed with apt-get.
        """
        component_config = (
            self.config if not component else ComponentConfig.read_from_component(component)
        )
        return component_config.image_packages or []

    @property
    def language_name(self) -> str:
        return self.config.language_name

    @property
    def language_version(self) -> str:
        return self.config.language_version or self.default_language_version

    @property
    def tag(self) -> str:
        return f"{self.project}-{self.component}:{self.tag_hash}"

    @property
    def editor_tag(self) -> str:
        return f"{self.project}-{self.component}:editor"

    @property
    def dev(self) -> bool:
        return self.tag_hash == "local"

    @property
    @abc.abstractmethod
    def base_image(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def builder_image(self) -> str:
        pass

    @property
    def workdir_create(self):
        return self.config.image_workdir.get("create", self.config.image_base is UNDEFINED)

    @property
    def workdir(self):
        return self.config.image_workdir.get(
            "path", "/code" if self.config.image_base is UNDEFINED else None
        )

    @property
    def user_info(self) -> UserInfo:
        default_name = "aladdin-user"
        name = self.config.image_user_info.name or default_name
        return UserInfo(
            create=self.config.image_user_info.create or self.config.image_base is UNDEFINED,
            name=name,
            group=(self.config.image_user_info.group or name),
            home=(self.config.image_user_info.home or f"/home/{name}"),
            sudo=(
                self.dev
                if self.config.image_user_info.sudo is UNDEFINED
                else self.config.image_user_info.sudo
            ),
        )

    @property
    def dependencies(self) -> typing.Tuple[str]:
        """
        The topologically sorted list of dependencies required for this component.

        This will include the complete hierarchy of dependencies for this component, so it is only
        necessary to enumerate a component's direct dependencies in the component.yaml file.
        """
        dependencies = networkx.algorithms.dag.ancestors(self.component_graph, self.component)
        return tuple(
            networkx.algorithms.dag.topological_sort(self.component_graph.subgraph(dependencies))
        )

    @property
    def components(self) -> typing.Tuple[str]:
        """
        The topologically sorted list of dependencies required for this component followed by this
        component itself.
        """
        return self.dependencies + (self.component,)

    @property
    def dockerfile(self) -> str:
        """The path to the component's dockerfile, if the file exists."""
        path = pathlib.Path("components") / self.component / "Dockerfile"
        return path if path.exists() else None

    @property
    def dockerfile_content(self) -> str:
        """The path to the component's dockerfile contents."""
        with open(self.dockerfile) as dockerfile:
            return dockerfile.read()


@dataclasses.dataclass
class PythonBuildInfo(BuildInfo):
    """
    A BuildInfo class specialized for Python 3 projects.

    By default, images will be based on the official python "slim" distribution.
    """

    poetry_version: str

    @property
    def base_image(self) -> str:
        """
        If the base image is defined in the component.yaml file, this component will be built as a
        "compatible" image, where the boilerplate code is mostly disabled by default. Otherwise,
        this component will be built as a "standard" image with all of the attendant boilerplate.
        """
        return self.config.image_base or self.builder_image

    @property
    def builder_image(self) -> str:
        """
        The image to be used to build and install any python dependencies.

        It should match the same python version used in the base_image.
        """
        return f"python:{'.'.join(self.language_version.split('.', 2)[:2])}-slim"

    def component_is_poetry_project(self, component=None) -> bool:
        """
        Return whether the component directory appears to be a python poetry project.

        A poetry project is defined by having two files: pyproject.toml and poetry.lock.

        :param component: The component to check, defaults to the current component.
        :returns: Whether the required files are present.
        """
        component_path = pathlib.Path("components") / (component or self.component)
        pyproject_path = component_path / "pyproject.toml"
        lock_path = component_path / "poetry.lock"
        return pyproject_path.exists() and lock_path.exists()
