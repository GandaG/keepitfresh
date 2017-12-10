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

from re import findall
from urllib.request import urlopen
from urllib.parse import urljoin


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
