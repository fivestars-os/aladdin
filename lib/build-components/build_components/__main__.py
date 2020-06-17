#!/usr/bin/env python3
"""
The default aladdin build script to be run when "aladdin build" is invoked.

It expects your project to conform to the "component" layout described in the documentation.

A project can override this behavior and provide their own build script by specifying the
"build_docker" entry in its lamp.json file.
"""
import contextlib
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap
import time
import typing

import coloredlogs
import jinja2
import networkx
import verboselogs

from .configuration import UNDEFINED, BuildConfig, ComponentConfig, ConfigurationException, UserInfo
from .build_info import BuildInfo, PythonBuildInfo

logger = None


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
    with open("lamp.json") as lamp_file:
        lamp = json.load(lamp_file)

    # Let's get to it!
    build_components(
        lamp=lamp,
        tag_hash=os.getenv("HASH", "local"),
        build_config=BuildConfig(),
        components=sys.argv[1:],
    )


def build_components(
    lamp: dict, tag_hash: str, build_config=BuildConfig, components: typing.List[str] = None
):
    """
    Build each component for the project.

    If components is empty, this will assume each directory in the components/ directory is a
    component and will build each of them.

    Each component will result in up to two images being built: the image to be used in whatever
    intended use case the component fulfils, and a second image, identical to the first except
    that its ENTRYPOINT and CMD instructions have been "cleared". This second image will only be
    built if tag_hash is "local". The resulting images will be tagged as
    ``{project}-{component}:{tag_hash}`` and ``{project}-{component}:editor``, respectively.

    :param lamp: The data from the project's lamp.json file.
    :param tag_hash: The build hash provided by ``aladdin build``.
    :param build_config: The default values for general build settings.
    :param components: The list of components to build, defaults to all of them.
    """
    components_path = pathlib.Path("components")
    all_components = [
        item
        for item in os.listdir(components_path)
        if os.path.isdir(components_path / item) and not item.startswith("_")
    ]

    if not components:
        # No components were specified at the command line

        if tag_hash == "local":
            # Build everything if doing a local build
            components = all_components
        else:
            # Only build components that will be published
            prefix = f"{lamp['name']}-"
            components = {
                image[image.startswith(prefix) and len(prefix) :]
                for image in lamp.get("docker_images", [])
            }

    # Check that all specified components actually exist in the project
    for component in components:
        if component not in all_components:
            raise ValueError(f"Component '{component}' does not exist")

    if not components:
        logger.info(
            "No components found for this project. Create a component directory to get started."
        )
        return

    # Check for cycles in the component dependency graph
    component_graph = validate_component_dependencies(components=components)

    # Let's build in topological order
    components = [
        component
        for component in networkx.algorithms.dag.topological_sort(component_graph)
        if component in components
    ]

    # Build each component in turn
    for component in components:
        try:
            logger.notice("Starting build for %s component", component)

            component_dir = pathlib.Path("components") / component
            if (component_dir / "component.yaml").exists():
                # This component will take advantage of our advanced build features.
                # It may either be a "standard" build or a "compatible" build, depending
                # on whether they specify a base image to use in their component.yaml file.
                build_aladdin_component(
                    lamp=lamp,
                    build_config=build_config,
                    component=component,
                    component_graph=component_graph,
                    tag_hash=tag_hash,
                )
            elif (component_dir / "Dockerfile").exists():
                # This component is a traditional Dockerfile component and we won't do any
                # special processing
                build_traditional_component(
                    project=lamp["name"], component=component, tag_hash=tag_hash
                )
            else:
                # If neither of these are specified, we do not know how to build this component
                raise ConfigurationException(
                    "No component.yaml or Dockerfile found for '%s' component", component
                )

        except Exception:
            logger.error("Failed to build image for component: %s", component)
            raise
        else:
            logger.success("Built image for component: %s\n\n", component)
    else:
        logger.success("Built images for components: %s", ", ".join(components))


def validate_component_dependencies(components: typing.List[str]) -> networkx.DiGraph:
    """
    Confirm that the components' dependency hierarchy has no cycles.

    :returns: The component dependency graph
    """
    # Copy for destructive operations
    components = set(components)

    # Create the component dependency graph
    component_graph = networkx.DiGraph()

    visited = set()
    while components:
        component = components.pop()
        if component not in visited:
            # Mark visited to prevent infinite loop on unexpected cycles
            visited.add(component)

            # Add to graph, if not already present
            component_graph.add_node(component)

            # Add dependencies to graph (will implicitly add nodes)
            config = ComponentConfig.read_from_component(component)
            component_graph.add_edges_from(
                (dependency, component) for dependency in config.dependencies
            )

            # Add any dependencies to the list of components to traverse to
            components.update(config.dependencies)

    # Check the graph for cycles
    try:
        cycles = networkx.algorithms.cycles.find_cycle(component_graph)
    except networkx.exception.NetworkXNoCycle:
        return component_graph
    else:
        logger.error("Cycle(s) found in component dependency graph: %s", cycles)
        raise ConfigurationException("Cycle(s) found in component dependency graph", cycles)


def build_traditional_component(project: str, component: str, tag_hash: str) -> None:
    """
    Build the component image in the traditional Dockerfile-based manner.

    This will build an image based solely on the Dockerfile in the component directory. No aladdin
    boilerplate or transforms will be applied.

    :param project: The name of the project containing the component
    :param component: The name of the component being built.
    :param tag_hash: The hash to use as the image tag.
    """
    logger.info("Building standard image for component: %s", component)
    _docker_build(
        tags=f"{project}-{component}:{tag_hash}",
        dockerfile=pathlib.Path("components") / component / "Dockerfile",
    )


def build_aladdin_component(
    lamp: dict,
    build_config: BuildConfig,
    component: str,
    component_graph: networkx.DiGraph,
    tag_hash: str,
) -> None:
    """
    Build a component image that has been defined with a component.yaml file.

    A component can be either a "standard" build, where the base image is not specified in the
    component.yaml file and default base image for the language is used (although it may be a
    different version than the default), or a "compatible" build where one specifies an alternative
    base image to use but still wishes to build (optional) and composite in other components' assets
    into the final image.

    The "standard" build will default to applying helpful aladdin-prescribed transforms, such as
    setting the working directory and creating the aladdin-user account. The "compatible" build will
    default to not applying those transforms. Also, in the "compatible" build mode, it is expected
    that the user will provide required information about the alternative image such as the user
    account info.

    The resulting image will be tagged as ``{project}-{component}:{tag_hash}``

    If tag_hash is "local", an accompanying editor image will be built as well and tagged with
    ``{project}-{component}:editor``.

    Note: The only supported language at this time is Python 3

    :param lamp: The data from the project's lamp.json file.
    :param build_config: The default values for general build settings.
    ;param component: The name of the component to build.
    ;param component_graph: The component dependency graph.
    :param tag_hash: The build hash provided by ``aladdin build``.
    """
    # Read the component.yaml file
    component_config = ComponentConfig.read_from_component(component)

    # TODO: Confirm that the component.yaml file conforms to our JSON schema
    # TODO: Determine if it's a "standard" component or a "compatible" one.
    #       That info could be provided to the build_python_component() function as a hint
    #       to choose a more-specific build process.

    if component_config.language_name == "python":
        build_info = PythonBuildInfo(
            project=lamp["name"],
            component_graph=component_graph,
            component=component,
            config=component_config,
            tag_hash=tag_hash,
            default_language_version=build_config.default_python_version,
            poetry_version=build_config.default_poetry_version,
        )

        build_python_component(build_info)
    else:
        raise ValueError(f"Unsupported language for {component} component: {language_name}")

    if tag_hash == "local":
        # Build the editor image for development use cases
        build_editor_image(build_info)


def build_python_component(build_info: PythonBuildInfo) -> None:
    """
    Build the component.

    This builds the component image according to the ``component.yaml`` configuration. It will
    generate a Dockerfile and populate the components/ directory with some ephemeral configuration
    files to facilate the build. A copy of the utilized Dockerfile will be able to be found at
    ``components/<component>/_build.dockerfile`` for debugging and development purposes.

    :param build_info: The build info populated from the config and command line arguments.
    """
    logger.info("Building image for python component: %s", build_info.component)

    # We only support python 3 components at the moment
    language_version = build_info.language_version
    if not language_version.startswith("3"):
        raise ValueError(
            f"Unsupported python version for {component} component: {language_version}"
        )

    # Load our jinja templates for python images.
    jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader("build_components", "templates/python"), trim_blocks=True
    )

    # This is the top-level template for a component Dockerfile
    jinja_template = jinja_env.get_template("Dockerfile.j2")

    # Place the temporary files for the duration of the build.
    with build_context(
        component=build_info.component, dockerfile=jinja_template.render(build_info=build_info)
    ) as dockerfile_path:

        # Make the generated Dockerfile available to the component prior to attempting the build
        if build_info.dev:
            with contextlib.suppress():
                shutil.copyfile(
                    dockerfile_path,
                    pathlib.Path("components") / build_info.component / "_build.dockerfile",
                )

        _docker_build(tags=build_info.tag)


@contextlib.contextmanager
def build_context(component: str, dockerfile: str) -> typing.Generator:
    """
    A context manager that writes necessary files to disk for the duration of a docker build.

    It will write three files to the components/ directory:
        - The contents of dockerfile to components/Dockerfile
        - A boilerplate pip.conf that ensures --user behavior
        - A boilerplate poetry.toml that prevents virtual env usage

    This writes the provided contents to components/Dockerfile. It then deletes the file upon exit.

    :param component: The component to build.
    :param contents: The Dockerfile contents to use within the contents.
    """
    components_path = pathlib.Path("components")
    pip_conf_path = components_path / "pip.conf"
    poetry_toml_path = components_path / "poetry.toml"
    dockerfile_path = components_path / "Dockerfile"
    try:
        # In addition to the generated Dockerfile, we provide these files in the build context
        # so that the Dockerfile can COPY these artifacts into the image. These are boilerplate
        # files that we don't want to burden the aladdin client project with including.
        with open(pip_conf_path, "w") as outfile:
            outfile.write(
                textwrap.dedent(
                    """
                    # This is a dynamically generated file created by build-components for the
                    # purpose of building the component containers.
                    # It is copied into our docker images to globally configure pip

                    [global]
                    # Install packages under the user directory
                    user = true
                    # Disable the cache dir
                    no-cache-dir = false

                    [install]
                    # Disable the .local warning
                    no-warn-script-location = false
                    """
                )
            )

        with open(poetry_toml_path, "w") as outfile:
            outfile.write(
                textwrap.dedent(
                    """
                    # This is a dynamically generated file created by build-components for the
                    # purpose of building the component containers.
                    # It is copied into our docker images to globally configure poetry

                    [virtualenvs]
                    # We're in a docker container, there's no need for virtualenvs
                    # One should still configure pip to use "--user" behavior so that
                    # poetry-installed packages will be placed in ~/.local
                    create = false
                    """
                )
            )

        with open(dockerfile_path, "w") as outfile:
            outfile.write(dockerfile)

        yield dockerfile_path
    finally:
        with contextlib.suppress():
            dockerfile_path.unlink()

        with contextlib.suppress():
            pip_conf_path.unlink()

        with contextlib.suppress():
            poetry_toml_path.unlink()


def build_editor_image(build_info: BuildInfo) -> None:
    """
    Build a companion image to the final built image that removes the ENTRYPOINT and CMD settings.

    This image can be used for shelling into for debugging and/or running arbitrary commands in a
    mirror of the built image.

    The resulting image will be tagged as ``{project}-{component}:editor``

    :param build_info: The build info populated from the config and command line arguments.
    """
    logger.info("Building editor image for %s component", build_info.component)

    # Perform a "no context" docker build
    _docker_build(
        tags=build_info.editor_tag,
        dockerfile=textwrap.dedent(
            f"""
            FROM {build_info.tag}
            CMD "/bin/sh"
            ENTRYPOINT []
            """
        ).encode(),
    )


def _docker_build(
    tags: typing.Union[str, typing.List[str]],
    buildargs: dict = None,
    dockerfile: typing.Union[pathlib.Path, bytes] = None,
) -> None:
    """
    A convenience wrapper for calling out to "docker build".

    We always send the same context: the entire components/ directory.

    :param tags: The tags to be applied to the built image.
    :param buildargs: Values for ARG instructions in the dockerfile.
    :param dockerfile: The dockerfile to build against. If not provided, it's assumed that a
                       Dockerfile is present in the context directory. If it's a bytes object, it
                       will be provided to the docker build process on stdin and a "no context"
                       build will take place. Otherwise, a normal docker build will be performed
                       with the specified Dockerfile.
    """
    buildargs = buildargs or {}
    buildargs.setdefault("CACHE_BUST", str(time.time()))

    cmd = ["env", "DOCKER_BUILDKIT=1", "docker", "build"]

    for key, value in buildargs.items():
        cmd.extend(["--build-arg", f"{key}={value}"])

    tags = [tags] if isinstance(tags, str) else tags
    for tag in tags:
        cmd.extend(["--tag", tag])

    if isinstance(dockerfile, bytes):
        # If we receive the Dockerfile as content, we should pipe it to stdin.
        # This is the "no context" build.
        cmd.extend(["-"])
    else:
        # Otherwise, they can specify the path to the Dockerfile to use or let docker
        # find one in the context directory.
        if dockerfile:
            cmd.extend(["-f", dockerfile.as_posix()])
        cmd.extend(["components"])

    logger.debug("Docker build command: %s", " ".join(cmd))
    _check_call(cmd, stdin=dockerfile if isinstance(dockerfile, bytes) else None)


def _check_call(cmd: typing.List[str], stdin: bytes = None) -> None:
    """
    Make a subprocess call and indent its output to match our python logging format.

    :param cmd: The command to run.
    :param stdin: Data to send to the subprocess as its input.
    """
    if stdin is None:
        ps = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        subprocess.run(["sed", "-e", "s/^/         /"], stdin=ps.stdout, check=True)
        ps.wait()
        if ps.returncode:
            raise subprocess.CalledProcessError(ps.returncode, cmd)
    else:
        ps = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = ps.communicate(input=stdin)
        if ps.returncode:
            raise subprocess.CalledProcessError(ps.returncode, cmd)
        subprocess.run(["sed", "-e", "s/^/         /"], input=stdout, check=True)
