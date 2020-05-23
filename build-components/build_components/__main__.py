#!/usr/bin/env python3
"""
The aladdin build script indicated in this project's lamp.json file.

It will run when ``aladdin build`` is invoked.
"""
import atexit
import collections
import contextlib
import functools
import json
import logging
import os
import pathlib
import pkg_resources
import shutil
import subprocess
import sys
import tempfile
import textwrap
import typing
import uuid

import coloredlogs
import networkx
import verboselogs
import yaml

logger = None


class Undefined:
    def __bool__(self):
        return False

    def __str__(self):
        raise NotImplementedError


UNDEFINED = Undefined()


class ConfigurationException(Exception):
    """Raised if there is an error in the component.yaml."""


class UserInfo(collections.namedtuple("UserInfo", ["name", "group", "home"])):
    def __bool__(self):
        return all(self)

    @property
    def chown(self):
        return f"{self.name}:{self.group}"


class ComponentConfig:
    """The representation of the component.yaml."""

    def __init__(self, data: dict):
        self._data = data

    def get(self, path: str, default: typing.Any = UNDEFINED):
        """
        Perform a lookup on the provided path name.

        :param path: The dot-delimited path to the config value.
        :param default: The value to return if the config value was not found.
        """
        return functools.reduce(
            lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
            path.split("."),
            self._data,
        )

    @property
    def version(self):
        return self.get("meta.version", 1)

    @property
    def language_name(self):
        name = self.get("language.name")
        return name.lower() if name else UNDEFINED

    @property
    def language_version(self):
        version = self.get("language.version")
        return str(version) if version else UNDEFINED

    @property
    def image_base(self):
        return self.get("image.base")

    @property
    def image_aladdinize(self):
        return self.get("image.aladdinize", True if self.image_base is UNDEFINED else False)

    @property
    def image_add_poetry(self):
        return self.get("image.add_poetry", True if self.image_base is UNDEFINED else False)

    @property
    def image_user_info(self):
        return UserInfo(
            name=self.get("image.user.name"),
            group=self.get("image.user.group"),
            home=self.get("image.user.home"),
        )

    @property
    def dependencies(self):
        return self.get("dependencies", [])


class BuildInfo(
    collections.namedtuple(
        "BuildInfo",
        [
            "project",
            "to_publish",
            "component_graph",
            "component",
            "config",
            "hash",
            "default_language_version",
            "poetry_version",
        ],
    )
):
    """
    A wrapper around the component config and some other high-level info to make parameterizing
    the build process a bit simpler. The build functions should use this rather than directly
    accessing the config.
    """

    def set_user_info(self, user_info: UserInfo):
        self._user_info = user_info

    def set_language_version(self, version: str):
        self._language_version = version

    @property
    def language_name(self):
        return self.config.language_name

    @property
    def language_version(self):
        return getattr(
            self, "_language_version", self.config.language_version or self.default_language_version
        )

    @property
    def tag(self):
        return f"{self.project}-{self.component}:{self.hash}"

    @property
    def editor_tag(self):
        return f"{self.project}-{self.component}:editor"

    @property
    def builder_tag(self):
        return f"{self.project}-{self.component}:builder"

    @property
    def dev(self):
        return self.hash == "local"

    @property
    def poetry_no_dev(self):
        return "" if self.dev else "--no-dev"

    @property
    def python_optimize(self):
        return "" if self.dev else "-O"

    @property
    def add_user_to_sudoers(self):
        return self.dev

    @property
    def base_image(self):
        return (
            self.config.image_base
            or f"python:{'.'.join(self.language_version.split('.', 2)[:2])}-slim"
        )

    @property
    def builder_base_image(self):
        return f"python:{'.'.join(self.language_version.split('.', 2)[:2])}-slim"

    @property
    def aladdinize(self):
        return (
            self.config.image_aladdinize if self.config.image_aladdinize is not UNDEFINED else True
        )

    @property
    def add_poetry(self):
        return (
            self.config.image_add_poetry if self.config.image_add_poetry is not UNDEFINED else True
        )

    @property
    def specialized_dockerfile(self):
        path = pathlib.Path("components") / self.component / "Dockerfile"
        return path.as_posix() if path.exists() else None

    @property
    def user_info(self):
        return getattr(self, "_user_info", self.config.image_user_info)

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


class DockerIgnore:
    """
    A class to be used to temporarily modify the singleton .dockerignore file for the various
    build steps we undertake in the component building process. This is the core magic that allows
    us to place all of our code under a single docker context but judiciously decide which parts to
    send to each build step.
    """

    def __init__(self, ignore_file: typing.IO, original_file_name: str):
        self._ignore_file = ignore_file
        with open(original_file_name) as original_file:
            self._original_content = original_file.read()

        self.write("")
        self.write("### Ephemeral modifications ###")
        self.write("# Specific instructions")

    def append_file(self, file_path_to_append: pathlib.Path, prefix: str = ""):
        """
        Append the contents of a file to the .dockerignore file.

        If ``prefix`` is provided, any non-comment, non-empty lines will have the prefix applied as
        they are appended to the .dockerignore file.

        :param file_path_to_append: The components/ directory-relative path to the file to append.
        :param prefix: The directory prefix to apply to all lines in the appended file.
        """
        relative_path = file_path_to_append.relative_to(pathlib.Path("components"))
        with open(file_path_to_append) as file_to_append:
            self.write("")
            self.write(f"### Contents of {relative_path.as_posix()} ###")
            line = file_to_append.readline()
            while line:
                # Prefix non-comment, non-blank lines with the provided prefix
                line = line.strip()
                if line.startswith("#"):
                    self.write(line)
                elif line:
                    self.write(f"{prefix}{line.rstrip()}")
                else:
                    self.write("")
                line = file_to_append.readline()

    def ignore_all(self):
        """
        Add a line that instructs docker to not send anything in the context.

        It is expected that this is followed by calls to ``include()``.
        """
        self.ignore("**")

    def ignore_defaults(self):
        """Copy the contents of the original .DockerIgnore file into the temporary one."""
        self.write("")
        self.write("### Original content ###")
        self.write(self._original_content)

    def ignore(self, entry: str):
        """
        Explicitly ignore ``entry``.

        :param entry: The pattern to ignore.
        """
        self.write(entry)

    def include(self, entry: str):
        """
        Explicitly include ``entry`` after a previous ``ignore_all()`` call.

        :param entry: The pattern to include.
        """
        self.write(f"!{entry}")

    def write(self, entry: str):
        """
        Write the entry line with a new-line to the ignore file and then flush the file.

        :param entry: The pattern to write.
        """
        self._ignore_file.write(f"{entry}\n")
        self._ignore_file.flush()


def dockerignore(mode: str):
    """
    A decorator to allow the decorated function to manipulate the .dockerignore file for a build.

    It provides the ignore_file argument to the decorated function with the DockerIgnore instance
    wrapping the already opened file.

    :param mode: The file mode string to use to open the .dockerignore file
    :return: The decorated function
    """
    original_path = pathlib.Path("components") / ".dockerignore"

    def decorator(func: typing.Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with tempfile.NamedTemporaryFile() as tmpfile:
                shutil.copyfile(original_path, tmpfile.name)
                atexit.register(shutil.copyfile, tmpfile.name, original_path)
                try:
                    with open(original_path, mode) as file:
                        return func(ignore_file=DockerIgnore(file, tmpfile.name), *args, **kwargs)
                finally:
                    shutil.copyfile(tmpfile.name, original_path)
                    atexit.unregister(shutil.copyfile)

        return wrapper

    return decorator


def main():
    """Kick off the build process with data gathered from the system and environment."""

    # Install some nice logging tools
    global logger

    verboselogs.install()
    coloredlogs.install(
        level=logging.DEBUG,
        fmt="%(levelname)-8s %(message)s",
        level_styles=dict(
            spam=dict(color="green", faint=True),
            debug=dict(color="black", bold=True),
            verbose=dict(color="blue"),
            info=dict(color="white"),
            notice=dict(color="magenta"),
            warning=dict(color="yellow"),
            success=dict(color="green", bold=True),
            error=dict(color="red"),
            critical=dict(color="red", bold=True),
        ),
        field_styles=dict(
            asctime=dict(color="green"),
            hostname=dict(color="magenta"),
            levelname=dict(color="white"),
            name=dict(color="white", bold=True),
            programname=dict(color="cyan"),
            username=dict(color="yellow"),
        ),
    )

    # This will be a VerboseLogger
    logger = logging.getLogger(__name__)

    # Provide the lamp.json file data to the build process
    with open("lamp.json") as file:
        lamp = json.load(file)

    # Let's get to it!
    build(lamp=lamp, hash=os.getenv("HASH", "local"), components=sys.argv[1:])


def build(
    lamp: dict,
    hash: str,
    components: typing.List[str] = None,
    default_python_version: str = "3.8",
    poetry_version: str = "1.0.5",
):
    """
    Build each component for the project.

    If components is empty, this will assume each directory in the components/ directory is a
    component and will build each of them.

    :param lamp: The data from the project's lamp.json file.
    :param hash: The build hash provided by ``aladdin build``.
    :param components: The list of components to build, defaults to all of them.
    :param default_python_version: The python version to use for the base image if not provided in
                                   the component's ``component.yaml`` file, defaults to ``"3.8"``.
    :param poetry_version: The version of poetry to install in the component images, defaults to
                           ``"1.0.5"``.
    """
    components_path = pathlib.Path("components")
    all_components = [
        item
        for item in os.listdir(components_path)
        if os.path.isdir(components_path / item) and not item.startswith("_")
    ]

    if not components:
        # Just build everything
        components = all_components
    else:
        for component in components:
            if component not in all_components:
                raise ValueError(f"Component '{component}' does not exist")

    if not components:
        logger.info(
            "No components found for this project. Create a component directory to get started."
        )
        return

    # Check for cycles in the component dependency graph
    component_graph = validate_component_dependencies(components=all_components)

    for component in components:
        logger.notice("Starting build for %s component", component)
        # Read the component.yaml file
        component_config = read_component_config(component)

        # We currently assume every component is python.
        # This assumption could conceivably be configured in the lamp.json file for
        # language-homogenous projects.
        language = component_config.language_name or "python"

        if language == "python":
            build_info = BuildInfo(
                project=lamp["name"],
                to_publish=lamp["docker_images"],
                component_graph=component_graph,
                component=component,
                config=component_config,
                hash=hash,
                # TODO: Handle these in a better manner when adding support for other languages
                default_language_version=default_python_version,
                poetry_version=poetry_version,
            )

            language_version = build_info.language_version
            if language_version.startswith("3"):
                # We only support python 3 components at the moment
                build_python_component_image(build_info)
            else:
                raise ValueError(
                    f"Unsupported python version for {component} component: {language_version}"
                )
        else:
            raise ValueError(
                f"Unsupported language for {component} component: {language}:{language_version}"
            )
    else:
        logger.success("Built images for components: %s", ", ".join(components))


def validate_component_dependencies(components: typing.List[str]) -> networkx.DiGraph:
    """
    Confirm that the components' dependency hierarchy has no cycles.

    :return: The component dependency graph
    """
    # Create our component dependency graph
    component_graph = networkx.DiGraph()
    component_graph.add_nodes_from(components)
    for component in components:
        config = read_component_config(component)
        component_graph.add_edges_from(
            (dependency, component) for dependency in config.dependencies
        )

    # Check for dependency cycles
    try:
        cycles = networkx.algorithms.cycles.find_cycle(component_graph)
    except networkx.exception.NetworkXNoCycle:
        return component_graph
    else:
        logger.error("Cycle(s) found in component dependency graph: %s", cycles)
        raise ConfigurationException("Cycle(s) found in component dependency graph", cycles)


def read_component_config(component: str) -> ComponentConfig:
    """
    Read the component's ``component.yaml`` file into a ``ComponentConfig`` object.

    :param component: The component's config to read.
    :return: The config data for the component. If the component does not provide a
             ``component.yaml`` file, this returns an empty config.
    """
    try:
        with open(pathlib.Path("components") / component / "component.yaml") as file:
            return ComponentConfig(yaml.safe_load(file))
    except ConfigurationException:
        raise
    except Exception:
        return ComponentConfig({})


def build_python_component_image(build_info: BuildInfo):
    """
    Build the component.

    This builds the component image according to the ``component.yaml`` configuration. It begins by
    building or tagging a base image and then adding to it things like the poetry tool and any
    component dependency assets.

    :param build_info: The build info populated from the config and command line arguments.
    """
    try:
        logger.notice("Building image for component: %s", build_info.component)

        # Determine the python version of the base image
        build_info.set_language_version(get_image_python_version(build_info))

        # Start off by simply tagging our base image
        # All subsequent steps here will just move the tag to the newly built image
        tag_base_image(build_info)

        # Create a builder image that can be used across components (rely on Dockerfile caching)
        build_builder_image(build_info)

        # Opt out by setting image.add_poetry=false or by specifying a base image
        if build_info.add_poetry:
            add_poetry(build_info)

        # Opt out by setting image.aladdinize=false or by specifying a base image
        if build_info.aladdinize:
            aladdinize_image(build_info)

        # Opt out by not providing a Dockerfile in the component directory
        if build_info.specialized_dockerfile:
            build_specialized_image(build_info)

        # Set the user info from the image so we can install python libraries in
        # the correct location
        build_info.set_user_info(get_image_user_info(build_info))

        # Add the component dependencies' assets
        add_dependency_components(build_info)

        # Add the component's assets
        add_component(build_info, build_info.component)

        # Add the user's ~/.local/bin to the PATH
        if build_info.add_poetry:
            add_local_bin(build_info)

        # # Build the editor image for facilitating poetry package updates
        build_editor_image(build_info)

    except Exception:
        logger.error("Failed to build image for component: %s", build_info.component)
        raise
    else:
        logger.success("Built image for component: %s\n\n", build_info.component)


def tag_base_image(build_info: BuildInfo):
    """
    Tag the starting point image.

    Most components will build off of the default image (hopefully always somewhat close to the
    latest python release).

    If one does not wish to use the default image, provide another in the ``image.base`` field of
    the ``component.yaml``.

    :param build_info: The build info populated from the config and command line arguments.
    """
    logger.info(
        "Tagging base image '%s' for %s component", build_info.base_image, build_info.component
    )

    _check_call(["docker", "pull", build_info.base_image])
    _check_call(["docker", "tag", build_info.base_image, build_info.tag])


@dockerignore("w")
def build_builder_image(build_info: BuildInfo, ignore_file: DockerIgnore):
    logger.info("Creating builder image for %s component", build_info.component)

    ignore_file.ignore_all()
    ignore_file.include("pip.conf")
    ignore_file.include("poetry.toml")

    _docker_build(
        dockerfile=pkg_resources.resource_filename(__package__, "python/builder.dockerfile"),
        tag=build_info.builder_tag,
        buildargs=dict(
            FROM_IMAGE=build_info.builder_base_image, POETRY_VERSION=build_info.poetry_version
        ),
    )


@dockerignore("w")
def aladdinize_image(build_info: BuildInfo, ignore_file: DockerIgnore):
    """
    Add the aladdin boilerplate.

    This creates the aladdin-user user and sets the ``WORKDIR`` to ``/code``.

    If one does not wish to add the aladdin boilerplate, specify ``image.aladdinize`` as ``false``
    in the ``component.yaml``.

    :param build_info: The build info populated from the config and command line arguments.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info("Adding aladdin boilerplate to %s component", build_info.component)

    ignore_file.ignore_all()

    _docker_build(
        dockerfile=pkg_resources.resource_filename(__package__, "python/aladdinize.dockerfile"),
        tag=build_info.tag,
        buildargs=dict(
            FROM_IMAGE=build_info.tag,
            PYTHON_OPTIMIZE=build_info.python_optimize,
            ADD_TO_SUDOERS="true" if build_info.add_user_to_sudoers else "false",
        ),
        purpose="aladdinize",
    )


@dockerignore("w")
def add_poetry(build_info: BuildInfo, ignore_file: DockerIgnore):
    """
    Add the poetry package manager to the image.

    This allows one to use the image to create/modify the ``pyproject.toml`` and ``poetry.lock``
    files for a component.

    :param build_info: The build info populated from the config and command line arguments.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info("Adding poetry to %s component", build_info.component)

    ignore_file.ignore_all()

    _docker_build(
        dockerfile=pkg_resources.resource_filename(__package__, "python/add-poetry.dockerfile"),
        tag=build_info.tag,
        buildargs=dict(BUILDER_IMAGE=build_info.builder_tag, FROM_IMAGE=build_info.tag),
        purpose="add-poetry",
    )


@dockerignore("a")
def build_specialized_image(build_info: BuildInfo, ignore_file: DockerIgnore):
    """
    Apply the component's ``Dockerfile`` to the image.

    This allows one to further customize the (possibly aladdinized) base image with more specific
    Dockerfile instructions. The context provided to the Dockerfile is the full ``components/``
    directory, minus the .dockerignore items, of course.

    :param build_info: The build info populated from the config and command line arguments.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info(
        "Building specialized image for %s component (dockerfile=%s)",
        build_info.component,
        build_info.specialized_dockerfile,
    )

    component_dockerignore_path = (
        pathlib.Path("components") / build_info.component / ".dockerignore"
    )
    if component_dockerignore_path.exists():
        ignore_file.append_file(component_dockerignore_path, prefix=f"{build_info.component}/")

    _docker_build(
        dockerfile=build_info.specialized_dockerfile,
        tag=build_info.tag,
        buildargs=dict(
            BUILDER_IMAGE=build_info.builder_tag,
            FROM_IMAGE=build_info.tag,
            PYTHON_OPTIMIZE=build_info.python_optimize,
        ),
        purpose="specialized",
    )


@contextlib.contextmanager
def extractor_image(from_image: str):
    """
    Yields a function to receive a string shell command to run in the given image.

    Use this to run arbitrary shell commands in an image, even if the image has set its
    ENTRYPOINT and CMD settinsg. It will run the command in a derived image with those settings
    cleared, then delete the image once done.

    :param from_image: The image to run the command in.
    """
    # Build a temporary image that can be used to pull image data out of the container.
    # We need to get rid of the ENTRYPOINT and CMD configurations.
    IMAGE_NAME = f"info_extractor:{uuid.uuid1().hex}"

    _docker_build(
        dockerfile=pkg_resources.resource_filename(__package__, "python/lobotomize.dockerfile"),
        tag=IMAGE_NAME,
        buildargs=dict(FROM_IMAGE=from_image),
    )

    def call_in_lobotomized_image(shell_command: str) -> str:
        """
        Execute a shell command in a container from the lobotomized image.

        :param shell_command: The command to execute.
        :return: The resulting stdout output string.
        """
        sp = subprocess.run(
            ["docker", "run", "--rm", IMAGE_NAME, "/bin/sh", "-c", shell_command],
            check=True,
            stdout=subprocess.PIPE,
        )
        return sp.stdout.decode(sys.stdout.encoding).strip()

    try:
        yield call_in_lobotomized_image
    finally:
        _check_call(["docker", "rmi", IMAGE_NAME])


def get_image_python_version(build_info: BuildInfo) -> str:
    """
    Retrieve the image's python version either from the component.yaml config or the image itself.

    :param build_info: The build info populated from the config and command line arguments.
    :return: The python version string.
    """
    # Go directly to the config here
    if build_info.config.language_version:
        logger.notice("Using configured python version: %s", build_info.config.language_version)
        return build_info.config.language_version

    try:
        with extractor_image(from_image=build_info.base_image) as call_in_extractor:
            python_version = call_in_extractor(
                "python -c 'import platform; print(platform.python_version())'"
            )

        assert (
            python_version.count(".") == 2
        ), f"Unexpected python version string: {retrieved_version}"
        logger.notice("Extracted python version from base image: %s", python_version)
    except Exception:
        logger.warning("Failed to extract python version from base image")
        python_version = "3.8"
    return python_version


def get_image_user_info(build_info: BuildInfo) -> UserInfo:
    """
    Retrieve the image's user info either from the component.yaml config or the image itself.

    :param build_info: The build info populated from the config and command line arguments.
    :return: The user info.
    """
    # Go directly to the config here
    if build_info.config.image_user_info:
        logger.notice("Using configured user info: %s", build_info.config.image_user_info)
        return build_info.config.image_user_info

    try:
        with extractor_image(from_image=build_info.tag) as call_in_extractor:
            user_name, user_groups, user_home = call_in_extractor(
                "whoami; groups; echo $HOME"
            ).split("\n")

        user_groups = user_groups.split()
        user_info = UserInfo(
            name=user_name, group=user_groups[0] if user_groups else None, home=user_home
        )
        logger.notice("Extracted user info from base image: %s", user_info)
        assert all(user_info)
        return user_info
    except Exception:
        logger.error("Failed to extract user info from base image")
        raise ConfigurationException("You must provide image.user_info in component.yaml")


def add_dependency_components(build_info: BuildInfo):
    """
    Add all of the components' dependencies to the image.

    This will iterate recursively over all of the dependencies found in the component's
    component.yaml and copy in the dependencies' poetry-managed libraries as well as the
    dependencies' code itself.

    :param build_info: The build info populated from the config and command line arguments.
    """
    dependencies = build_info.dependencies

    if dependencies:
        logger.info(
            "Processing dependencies for %s: %s", build_info.component, ", ".join(dependencies)
        )
        for component in dependencies:
            add_component(build_info, component)


def add_component(build_info: BuildInfo, component: str):
    """
    Add a component's poetry-managed libraries and the component's own assets to the image.

    If ``component`` is the component whose image is currently being built and it appears to be
    using poetry to define its project, it will also be ``poetry installed`` in the image. This is
    to account for any components that define commands under ``[tool.poetry.scripts]`` in their
    ``pyproject.toml`` file. Those commands will be available in the container as first-class
    command line commands.

    :param build_info: The build info populated from the config and command line arguments.
    :param component: The component to add to the image.
    """
    logger.info("Adding %s to %s component", component, build_info.component)

    # Determine if component we are adding has python package dependencies that need to be installed
    component_path = pathlib.Path("components") / component
    pyproject_path = component_path / "pyproject.toml"
    lock_path = component_path / "poetry.lock"
    component_has_python_packages = pyproject_path.exists() and lock_path.exists()

    if component_has_python_packages:
        add_component_python_packages(build_info, component)
    add_component_content(
        build_info=build_info,
        component=component,
        poetry_install_component=(
            component == build_info.component and component_has_python_packages
        ),
    )


@dockerignore("w")
def add_component_python_packages(build_info: BuildInfo, component: str, ignore_file: DockerIgnore):
    """
    Add the poetry-managed python packages from the specified component to the image.

    :param build_info: The build info populated from the config and command line arguments.
    :param component: The component's python packages to add to the image.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info("Adding %s python dependencies to %s component", component, build_info.component)

    # Only keep the files for performing a poetry install
    ignore_file.ignore_all()
    ignore_file.include("pip.conf")
    ignore_file.include("poetry.toml")
    ignore_file.include(f"{component}/pyproject.toml")
    ignore_file.include(f"{component}/poetry.lock")

    # Build the poetry dependencies
    _docker_build(
        dockerfile=pkg_resources.resource_filename(
            __package__, "python/add-component-python-dependencies.dockerfile"
        ),
        tag=build_info.tag,
        buildargs=dict(
            BUILDER_IMAGE=build_info.builder_tag,
            FROM_IMAGE=build_info.tag,
            COMPONENT=component,
            POETRY_NO_DEV=build_info.poetry_no_dev,
            PYTHON_OPTIMIZE=build_info.python_optimize,
            USER_HOME=build_info.user_info.home,
            USER_CHOWN=build_info.user_info.chown,
        ),
        purpose=f"add-{component}-packages",
    )


@dockerignore("w")
def add_component_content(
    build_info: BuildInfo, component: str, poetry_install_component: bool, ignore_file: DockerIgnore
):
    """
    Copy in the component's code and other data.

    This will populate the component's directory in the image.

    :param build_info: The build info populated from the config and command line arguments.
    :param component: The component's content to add to the image.
    :param poetry_install_component: Whether or not to do one final ``poetry install`` for this
                                     component. When this is enabled, this will install any poetry
                                     scripts defined by the component into the ~/.local/bin
                                     directory, thus making them available for unqualified CLI
                                     invocation.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info("Adding %s content to %s component", component, build_info.component)

    # Only keep the component content files
    ignore_file.ignore_all()
    ignore_file.include(component)
    ignore_file.ignore_defaults()

    # But allow the component to also indicate what they wish to ignore
    component_dockerignore_path = pathlib.Path("components") / component / ".dockerignore"
    if component_dockerignore_path.exists():
        ignore_file.append_file(component_dockerignore_path, prefix=f"{component}/")

    # Copy the built poetry dependencies and the component code into the target image
    _docker_build(
        dockerfile=pkg_resources.resource_filename(
            __package__, "python/add-component-content.dockerfile"
        ),
        tag=build_info.tag,
        buildargs=dict(
            FROM_IMAGE=build_info.tag,
            COMPONENT=component,
            POETRY_INSTALL_COMPONENT="true" if poetry_install_component else "false",
            PYTHON_OPTIMIZE=build_info.python_optimize,
            USER_CHOWN=build_info.user_info.chown,
        ),
        purpose=f"add-{component}-content",
    )


@dockerignore("w")
def add_local_bin(build_info: BuildInfo, ignore_file: DockerIgnore):
    """
    Add the image user's ``~/.local/bin`` directory to the image PATH.

    This ensures that any scripts installed by the component's python packages are available.

    :param build_info: The build info populated from the config and command line arguments.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info(
        "Adding %s/.local/bin to PATH for %s component",
        build_info.user_info.home,
        build_info.component,
    )

    ignore_file.ignore_all()

    _docker_build(
        dockerfile=pkg_resources.resource_filename(
            __package__, "python/add-local-bin-to-path.dockerfile"
        ),
        tag=build_info.tag,
        buildargs=dict(FROM_IMAGE=build_info.tag, USER_HOME=build_info.user_info.home),
    )


@dockerignore("w")
def build_editor_image(build_info: BuildInfo, ignore_file: DockerIgnore):
    """
    Build a companion image to the final built image that removes the ENTRYPOINT and CMD settings.

    This image can be used for shelling into for debugging and/or running arbitrary commands in a
    mirror of the built image.

    :param build_info: The build info populated from the config and command line arguments.
    :param ignore_file: The ``.dockerignore`` file handle to be used to update its contents.
    """
    logger.info("Building editor image for %s component", build_info.component)

    ignore_file.ignore_all()

    _docker_build(
        dockerfile=pkg_resources.resource_filename(__package__, "python/lobotomize.dockerfile"),
        tag=build_info.editor_tag,
        buildargs=dict(FROM_IMAGE=build_info.tag),
    )


def _docker_build(dockerfile: str, tag: str, buildargs: dict = None, purpose: str = None):
    """
    A convenience wrapper for calling out to "docker build".

    We always send the same context: the components/ directory.

    If ``purpose`` is provided, it will create an extra tag on the resulting image. This
    can be used to help preserve these interstitial images when a ``docker system prune``
    takes place. This will only happen if the build hash is ``local``.

    :param dockerfile: The dockerfile to build against.
    :param tags: The tags to be applied to the built image.
    :param buildargs: Values for ARG instructions in the dockerfile.
    :param purpose: A string used to create an extra tag for the resulting image.
    """
    buildargs = buildargs or {}

    tags = [tag]
    if purpose:
        tag_image, tag_tag = tag.split(":")
        tags.append(f"{tag_image}-{purpose}:{tag_tag}")

    cmd = ["docker", "build"]
    for key, value in buildargs.items():
        cmd.extend(["--build-arg", f"{key}={value}"])
    for tag in tags:
        cmd.extend(["--tag", tag])
    cmd.extend(["-f", dockerfile, "components"])

    # Log the build command in a more readable format
    logger.debug(
        "docker build %s -f %s components"
        + "\n"
        + textwrap.indent(
            "\n".join(f"{key}={value}" for key, value in sorted(buildargs.items())), " " * 13
        )
        + "\n",
        " ".join(f"--tag {tag}" for tag in tags),
        dockerfile,
    )

    # Log the .dockerignore file contents used for the build
    with open(pathlib.Path("components") / ".dockerignore") as ignore_file:
        logger.debug(".dockerignore file:\n%s", textwrap.indent(ignore_file.read(), " " * 9))

    logger.debug("Docker build output:")
    _check_call(cmd)


def _check_call(cmd: typing.List[str]):
    """
    Make a subprocess call and indent its output to match our python logging format.

    :param cmd: The command to run.
    """
    ps = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    subprocess.run(["sed", "-e", "s/^/         /"], stdin=ps.stdout, check=True)
    ps.wait()
    if ps.returncode:
        raise subprocess.CalledProcessError(ps.returncode, cmd)
