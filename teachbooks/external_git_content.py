import os.path
import re
import subprocess

from pathlib import Path
from typing import Any, Callable, Dict, Union, overload

import yaml


DEFAULT_EXTERNAL_PATH = "_git"


def process_external_toc_entries(
    src: str | Path, dest: str | Path
) -> Path:
    """Parse external (git) ToC entries, checkout repos & write new ToC to file.
    
    :param src: Path to the source table-of-contents yaml file.
    :param dest: Path to the destination table-of-contents yaml file.
    :return: Path to the new table-of-contents yaml file.
    """
    src = Path(src)
    dest = Path(dest)

    work_dir = Path(dest).parent
    
    if not work_dir.exists():
        msg = f"Directory `{work_dir}` of the toc destination does not exist."
        raise ValueError(msg)

    src_toc = parse_toc_yaml(src)
    toc = src_toc.copy()

    toc = modify_field(
        toc,
        key="external",
        func=external_to_local,
        external_path=work_dir / DEFAULT_EXTERNAL_PATH,
        root=work_dir,
    )

    write_toc_yaml(toc, dest)
    return dest


def get_repo_url(url: str) -> str:
    """Get repo url by searching for reg like https://*/*/*/

    :param url: URL path to the external content
    :return: repository URL
    """
    pattern = r"https://[^/]+/[^/]+/[^/]+(?=/)"
    match = re.search(pattern, url)
    return match[0]


def get_branch_tag_name(url: str) -> str:
    """Get branch_tag_name by searching for anything between blob and book in
    external_url

    :param url: URL path to the external content
    :return: branch or tag name
    """
    pattern = r"blob/([^/]+)/"
    match = re.search(pattern, url)
    return match[1]


def get_content_path(url: str) -> str:
    """Get relative path of the external content from the URL path

    :param url: URL path to the external content
    :return: repo path to the external content
    """
    branch_tag_name = get_branch_tag_name(url)
    *_, path = url.split(branch_tag_name)
    return path.strip("/")  # remove leading and trailing "/"


def create_content_dir_name(url: str, root_dir: Union[str, Path]) -> str:
    """Generate the path where the repo will be cloned to.

    It will be of the form:

    {root_path}/{platform}_{organization}_{repository}/{revision}

    :param url: URL path to the external content
    :param root_dir: root directory where the repo will be cloned into
    :return: path where the repo will be cloned to
    """
    branch_tag_name = get_branch_tag_name(url)
    url = get_repo_url(url)
    if url.startswith("https://"):
        url = url.removeprefix("https://")
    dir_name = url.replace("/", "_")
    return f"{root_dir}/{dir_name}/{branch_tag_name}"


def parse_toc_yaml(
        path: Union[str, Path], encoding: str = "utf8"
) -> Dict[str, Any]:
    """Parse the ToC file.

    :param path: `_toc.yml` file path
    :param encoding: `_toc.yml` file character encoding
    :return: parsed site map
    """
    with open(path, encoding=encoding) as handle:
        data = yaml.safe_load(handle)
    return data


def write_toc_yaml(
        data: Dict[str, str], path: Union[str, Path], encoding: str = "utf8"
) -> None:
    """Write a ToC file.

    :param data: site map
    :param path: `_toc.yml` file path
    :param encoding: `_toc.yml` file character encoding
    """
    with open(path, encoding=encoding, mode="w") as handle:
        yaml.safe_dump(data, handle)


def external_to_local(
        mapping: Dict[str, Any], external_path: Union[str, Path],
        root: Union[str, Path]
) -> Dict[str, Any]:
    """Modify mapping with the "external" key.

    Retrieve external components locally, and fix ToC fields accordingly.

    :param mapping: map to modify
    :param external_path: path where to store external components
    :param root: express paths to external components with respect to root
    :return: map with fields adjusted in order to refer to local resources
    """
    mapping_local = mapping.copy()
    external_url = mapping_local.pop("external")

    repo_url = get_repo_url(external_url)
    clone_url = f"{repo_url}.git"

    branch_tag_name = get_branch_tag_name(external_url)
    content_dir = create_content_dir_name(external_url, root_dir=external_path)

    if os.path.isdir(content_dir):
        print(f"{content_dir} already exists. Not re-downloading")
    else:
        # clone with branch_name
        subprocess.run([
            "git", "clone", "--single-branch", "-b",  branch_tag_name, clone_url,
            content_dir
        ])

    content_path = get_content_path(external_url)
    rel_path = os.path.relpath(content_dir, root)
    mapping_local["file"] = os.path.join(rel_path, content_path)
    return mapping_local


@overload
def modify_field(
    data: dict, key: str, func: Callable, *args, **kwargs
) -> dict: ...


@overload
def modify_field(
    data: list, key: str, func: Callable, *args, **kwargs
) -> list: ...


def modify_field(
    data: Union[dict, list], key: str, func: Callable, *args, **kwargs
) -> Union[dict, list]:
    """Modify the fields that match a given key.

    Recursively look for the fields matching a given key in a YAML-like
    mapping. Modify the matching fields by running `func` on them.

    :param data: mapping where to look for matches
    :param key: key to look for
    :param func: function to run on the matching fields
    :param args, kwargs: other positional and keyword arguments for `func`
    :return: modified mapping
    """
    if isinstance(data, dict):
        if key in data:
            return func(data, *args, **kwargs)
        else:
            return {
                k: modify_field(v, key, func, *args, **kwargs)
                for k, v in data.items()
            }
    elif isinstance(data, list):
        return [modify_field(el, key, func, *args, **kwargs) for el in data]
    return data
