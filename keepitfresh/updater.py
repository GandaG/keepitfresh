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

from re import findall
from urllib.request import urlopen
from urllib.parse import urljoin
from tempfile import TemporaryDirectory
from shutil import copyfileobj
from patoolib import extract_archive
from packaging.version import parse


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
    if not results:
        raise ValueError("No files found in given url with given regex.")

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
