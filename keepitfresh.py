#!/usr/bin/env python

# Copyright 2017 Daniel Nunes
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The main bulk of the library.
"""

import os
import stat
import subprocess
from platform import system
from re import findall
from shutil import copy2, copyfileobj, copytree, rmtree
from tempfile import TemporaryDirectory
from urllib.parse import urljoin
from urllib.request import urlopen

from packaging.version import parse
from patoolib import extract_archive


def get_file_urls(base_url, regex):
    """
    Inspired by uscan, the debian packaging utility.

    Looks through all ``<a href="*">`` references to files in the given
    base url and extracts them into a dictionary of (file_url, file_version)
    value-pairs.

    The **regex** argument is a regular expression that matches the file name.
    It MUST have the file's version in a capturing group and this MUST be the
    first group (``\\1`` backreference).

    As an example, consider a project named *b* by *a* which deploys
    to Github Releases with filenames such as *b-1.0.0.zip*. The function
    call would look like::

        >>> base_url = "https://github.com/a/b/releases"
        >>> regex = r"b-(\\d+\\.\\d+\\.\\d+)\\.zip"
        >>> result = get_file_urls(base_url, regex)
        >>> result
        {"https://github.com/a/b/releases/download/1.0.0/b-1.0.0.zip": "1.0.0"}
    """
    with urlopen(base_url) as web:
        content = web.read().decode(web.headers.get_content_charset())

    pattern = r'<\s*a\s+[^>]*href\s*=\s*[\"\'](.*?' + regex + r')[\"\']'
    results = findall(pattern, content)

    file_dict = {}
    for match in results:
        file_dict[urljoin(base_url, match[0])] = match[1]

    return file_dict


def get_update_version(file_dict, current_version, vcmp=None):
    """
    Look through a dictionary that maps file urls to version strings, much like
    the one returned by :func:`~keepitfresh.get_file_urls`, and get the latest
    version and corresponding file url. If no version newer than
    **current_version** is found, returns an empty tuple.

    **current_version** should be a string in the same pattern as used in
    :func:`~keepitfresh.get_file_urls`.

    To get the latest version, a comparison function is used. The default uses
    the comparison from the
    `packaging <https://packaging.pypa.io/en/latest/version/>`_ package. To
    override this, pass a function in **vcmp** that accepts two version strings
    and returns ``True`` whenever the second version string is newer than the
    first version string.
    """
    freshest_match = (None, current_version)

    for url, version in file_dict.items():
        fresher = False

        if vcmp is not None:
            fresher = vcmp(freshest_match[1], version)
        else:
            fresher = parse(freshest_match[1]) < parse(version)

        if fresher:
            freshest_match = (url, version)

    if freshest_match == (None, current_version):
        return ()
    return freshest_match


def dl_unpack(url, outdir, unpack=None):
    """
    Downloads the archive in **url** and unpacks it to **outdir**.

    Unpacking is handled by `patool <http://wummel.github.io/patool/>`_.
    If you need to override this, you can a function in **unpack** that
    accepts the archive path as the first argument and the output folder
    as the second argument.
    """
    fname = url.rsplit('/', 1)[1]
    with TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, fname)
        with urlopen(url) as response, open(file_path, 'wb') as out_file:
            copyfileobj(response, out_file)

        if unpack is not None:
            unpack(file_path, outdir)
        else:
            extract_archive(file_path, outdir=outdir, verbosity=-1)


def overwrite_restart(initem, owitem, entry_point):
    """
    Overwrites the current application file/folder and restarts the process
    with the updated application.

    Inspired by PyUpdater, uses a separate process for Unix and Windows
    (Windows does not allow file deletion while it's still being used so we
    have to work around that).

    **initem** can be either a file or a folder and is the path to the updated
    application. **owitem** can be either a file or a folder and is the path
    to the old application.

    **entry_point** is the relative path from the parent folder of **owitem**
    to the executable to restart with.
    """
    initem = os.path.abspath(initem)
    owitem = os.path.abspath(owitem)
    owdir = os.path.dirname(owitem)
    abs_path = os.path.join(owdir, entry_point)
    fname = os.path.basename(abs_path)

    if system() == 'Windows':  # pragma: no unix
        vbs_string = ('CreateObject("Wscript.Shell").Run """" '
                      '& WScript.Arguments(0) & """", 0, False')

        bat_string = "@echo off\n"

        if os.path.isdir(owitem):
            bat_string += "rd /s /q \"{}\"\n".format(owitem)
        else:
            bat_string += "del /q \"{}\"\n".format(owitem)

        if os.path.isdir(initem):
            dest = os.path.join(owdir, os.path.basename(initem))
            bat_string += "robocopy \"{}\" \"{}\" /e\n".format(initem, dest)
        else:
            bat_string += "copy /y /b \"{}\" \"{}\"\n".format(initem, owdir)

        bat_string += "start \"\" \"{}\"\n".format(abs_path)

        with TemporaryDirectory() as tmpdir:
            vbs_path = os.path.join(tmpdir, 'invisble.vbs')
            bat_path = os.path.join(tmpdir, 'restart.bat')
            with open(vbs_path, 'w', encoding='utf8') as vbs_file:
                vbs_file.write(vbs_string)
            with open(bat_path, 'w', encoding='utf8') as bat_file:
                bat_file.write(bat_string)

            args = ['wscript.exe', vbs_path, bat_path]
            subprocess.Popen(args)
            os._exit(0)

    else:  # pragma: no windows
        if os.path.isdir(owitem):
            rmtree(owitem)
        else:
            os.remove(owitem)

        if os.path.isdir(initem):
            copytree(initem, os.path.join(owdir, os.path.basename(initem)))
        else:
            copy2(initem, owdir)

        filest = os.stat(abs_path)
        os.chmod(abs_path,
                 filest.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.execl(abs_path, fname)


def is_fresh(base_url, regex, current_version, versioncmp=None):
    """
    Checks whether your application is fresh (if there is a more
    recent version).
    Returns False if there is a newer version, True otherwise.

    For what each argument means, please refer to
    :func:`~keepitfresh.freshen_up`.
    """
    file_dict = get_file_urls(base_url, regex)
    latest_match = get_update_version(file_dict, current_version, versioncmp)
    if not latest_match:
        return True
    return False


def freshen_up(**kwargs):
    """
    Finds, downloads, unpacks, overwrites and restarts your application.
    Essentially an all-in-one for your convenience.

    This function requires 5 arguments to be passed with an additional
    2 optional.

    The required arguments are as follows:

    - **base_url** - The url that contains the links to download the
      package in the form ``<a href"..."/>``.
    - **regex** - The regular expression that matches the file name.
      Must contain at least one capturing group representing the version
      string and this must be the first group.
    - **current_version** - The current version of the application as a string.
    - **overwrite_item** - The file/folder where your application is and that
      is going to be overwritten.
    - **entry_point** - The relative path from **overwrite_item** to the
      executable that restarts the application.

    The optional arguments are as follows:

    - **versioncmp** - A function to override the default version comparison
      method, that takes 2 positional arguments, two version strings, and
      returns ``True`` whenever the second version string is newer than the
      first version string.
    - **unpack** - A function to override the defauly unpacking method that
      takes two arguments, the archive path and the output folder.

    If **versioncmp** is not provided, the standard comparison method from the
    `packaging <https://packaging.pypa.io/en/latest/version/>`_ package is
    used. If **unpack** is not provided, unpacking is handled by
    `patool <http://wummel.github.io/patool/>`_.
    """
    base_url = kwargs.get('base_url')
    regex = kwargs.get('regex')
    current_version = kwargs.get('current_version')
    overwrite_item = kwargs.get('overwrite_item')
    entry_point = kwargs.get('entry_point')
    versioncmp = kwargs.get('versioncmp', None)
    unpack = kwargs.get('unpack', None)

    file_dict = get_file_urls(base_url, regex)
    latest_match = get_update_version(file_dict, current_version, versioncmp)
    if not latest_match:
        raise RuntimeError("No newer version!")
    with TemporaryDirectory() as tmpdir:
        dl_unpack(latest_match[0], tmpdir, unpack)
        if len(os.listdir(tmpdir)) == 1:
            initem = os.path.join(tmpdir, os.listdir(tmpdir)[0])
        else:
            initem = os.path.join(tmpdir, entry_point)
        overwrite_restart(initem, overwrite_item, entry_point)
