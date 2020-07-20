import dataclasses
import functools
import pathlib
import typing

import yaml


# You won't be able to instantiate this outside of this module
class _Undefined:
    """Used to create a sentinel object for missing configuration values."""

    def __bool__(self):
        return False

    def __str__(self):
        raise NotImplementedError


UNDEFINED = _Undefined()

del _Undefined


class ConfigurationException(Exception):
    """Raised if there is an error in the component.yaml or the component structure."""


@dataclasses.dataclass
class UserInfo:
    """Data defining a component image's USER."""

    create: str
    name: str
    group: str
    home: str
    sudo: str

    def __bool__(self):
        raise NotImplementedError

    @property
    def chown(self) -> str:
        return f"{self.name}:{self.group}"


class ComponentConfig:
    """The representation of the component.yaml."""

    @classmethod
    def read_from_component(cls, component: str) -> "ComponentConfig":
        """
        Read a component's ``component.yaml`` file into a ``ComponentConfig`` object.

        :param component: The component's config to read.
        :returns: The config data for the component. If the component does not provide a
                  ``component.yaml`` file, this returns an empty config.
        """
        try:
            with open(pathlib.Path("components") / component / "component.yaml") as file:
                return cls(yaml.safe_load(file))
        except ConfigurationException:
            raise
        except Exception:
            return cls({})

    def __init__(self, data: dict):
        self._data = data

    def __bool__(self):
        return bool(self._data)

    def get(self, path: str, default: typing.Any = UNDEFINED) -> typing.Any:
        """
        Perform a lookup on the provided path name.

        :param path: The dot-delimited path to the config value.
        :param default: The value to return if the config value was not found.
        """
        # TODO: Consider using jmespath here instead
        return functools.reduce(
            lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
            path.split("."),
            self._data,
        )

    @property
    def version(self) -> int:
        return self.get("meta.version", 1)

    @property
    def language_name(self) -> str:
        name = self.get("language.name")
        return name.lower() if name else UNDEFINED

    @property
    def language_version(self) -> str:
        version = self.get("language.version")
        return str(version) if version else UNDEFINED

    @property
    def language_spec(self) -> dict:
        return self.get("language.spec")

    @property
    def image_base(self) -> str:
        return self.get("image.base")

    @property
    def image_packages(self) -> typing.List[str]:
        return self.get("image.packages")

    @property
    def image_user_info(self) -> UserInfo:
        return UserInfo(
            create=self.get("image.user.create"),
            name=self.get("image.user.name"),
            group=self.get("image.user.group"),
            home=self.get("image.user.home"),
            sudo=self.get("image.user.sudo"),
        )

    @property
    def image_workdir(self) -> dict:
        return self.get("image.workdir", {})

    @property
    def dependencies(self) -> typing.List[str]:
        return self.get("dependencies", [])


@dataclasses.dataclass
class BuildConfig:
    """
    System defaults that can be overridden by command-line arguments and/or component.yaml settings.
    """

    default_python_version: str = "3.8"
    default_poetry_version: str = "1.0.9"
