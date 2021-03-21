"""RedBot info.json validator"""
import json
import os
import re
from glob import glob
from typing import Any, Tuple, Union

import toml

OUTPUT = "::{level} file={file},line={line},col={col}::{message}"
IGNORE_ERRORS = False


def print_message(level: str, file: str, line: int, col: int, message: str):
    print(OUTPUT.format(level=level, file=file, line=line, col=col, message=message))


def get_key_pos(filename: str, key: str) -> Tuple[int]:
    reg_match = re.compile(f'"{key}"\s?:')
    with open(filename, "r") as f:
        lines = f.read().split("\n")
    for i, line in enumerate(lines):
        match = reg_match.search(line)
        if not match:
            raise Exception("could not get position of key")
        span = match.span()
        return (i + 1, span[0] + 1)


class ConfigNotFound(Exception):
    pass


class Config:
    def type_to_str(self, inp_type: Union[type, list, dict]):
        built_ins = {
            str: "str",
            int: "int",
        }
        if inp_type in built_ins.keys():
            return built_ins[inp_type]
        elif type(inp_type) is list:
            return f"list[{self.type_to_str(inp_type[0])}]"
        elif type(inp_type) is dict:
            return f"{self.type_to_str(inp_type['type'])} with values in {inp_type['values']}"

    def type_check(self, val: Any, desired_type: Any) -> bool:
        if desired_type is list:
            if type(val) is not list:
                return False
            for i in val:
                check = self.type_check(val[0], desired_type[0])
                if not check:
                    return False
        elif desired_type is dict:
            if "type" in desired_type:
                check = self.type_check(val, desired_type["type"])
                if not check:
                    return False
                if "values" in desired_type:
                    if val not in desired_type["values"]:
                        return False
        else:
            return type(val) is desired_type

    def validate_info(self, info: dict, filename: str) -> bool:
        """Validates an info.json file"""
        # Check key validity
        self.validate_keys(info)
        self.validate_required_keys(info)
        self.validate_types(info)
        for key in info:
            if key not in self.KEYS:
                line, col = get_key_pos(filename, key)
                if key.lower() in self.KEYS:
                    print_message(
                        "warning",
                        filename,
                        col,
                        line,
                        f"KeyError: key `{key}` needs to be lowercase",
                    )
                else:
                    print_message(
                        "warning",
                        filename,
                        col,
                        line,
                        f"KeyError: unrecognised key `{key}`",
                    )
        # Check required keys presence
        for key in self.options["required-keys"]:
            if key not in info:
                print_message(
                    "error" if not IGNORE_ERRORS else "warning",
                    filename,
                    1,
                    1,
                    f"KeyError: required key `{key}` missing",
                )
        # Check type validity
        for key, val in info.items():
            if key not in self.KEYS:
                # Already checked for key validity
                continue
            type_check = self.validate_type(val, self.KEYS[key])
            if not type_check:
                is_error = not (IGNORE_ERRORS or key in self.KEYS)
                line, col = get_key_pos(filename, key)
                print_message(
                    "warning" if IGNORE_ERRORS else "error",
                    filename,
                    line,
                    col,
                    f"TypeError: key `{key}` must be of type {self.type_to_str(self.KEYS[key])}",
                )


class RepoConfig(Config):
    KEYS = {"author": [str], "description": str, "install_msg": str, "short": str}

    def __init__(self, options: dict = None):
        if options:
            options_check = self.check_options(options)
            self.options = options
        else:
            self.options = self.DEFAULT_OPTIONS


class CogConfig(Config):
    KEYS = {
        "author": [str],
        "description": str,
        "short": str,
        "disabled": bool,
        "tags": [str],
        "install_msg": str,
        "min_bot_version": str,
        "max_bot_version": str,
        "hidden": bool,
        "required_cogs": dict,
        "requirements": [str],
        "type": {"type": str, "values": ["COG", "SHARED_LIBRARY"]},
    }
    DEFAULT_OPTIONS = {"required-keys": ["author", "description", "short", "tags"]}
    ALLOWED_OPTION_KEYS = ["required-keys"]

    def __init__(self, options: dict = None):
        if options:
            options_check = self.check_options(options)
            self.options = options
        else:
            self.options = self.DEFAULT_OPTIONS


def get_config():
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        pyproject = toml.loads(content)
        if "tool" not in pyproject:
            raise ConfigNotFound
        if "red-info-validation" not in pyproject["tool"]:
            raise ConfigNotFound
        config = pyproject["red-info-validation"]
        if not config:
            raise ConfigNotFound

    except FileNotFoundError:
        # Config doesn't exist
        pass
    except toml.decoder.TomlDecodeError:
        # Invalid toml format
        pass
