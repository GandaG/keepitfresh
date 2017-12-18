.. include:: ../README.rst
    :end-line: -4


Installation
------------

To install *keepitfresh*, use pip::

    pip install keepitfresh

Simple as that! You now have *keepitfresh* available in your environment.


Usage
-----

You can find a more thourough description of each argument below, this section
illustrates an example usage with some pseudo-code::

    >>> base_url = 'http://www.example.com/'
    >>> regex = r'(\d+\.\d+\.\d+)\.(?:tar\.gz|zip|rar|7z)'
    >>> current_version = '0.0.1'
    >>> overwrite_item = 'path/to/application'
    >>> entry_point = 'example.exe'
    >>> # check if it can be updated
    >>> is_fresh(base_url, regex, current_version):
    False

    >>> # current version is not fresh, let's update
    >>> payload = {'base_url': base_url 'regex': regex, 'current_version': current_version, 'overwrite_item': overwrite_item, 'entry_point': entry_point}
    >>> freshen_up(**payload)  # process will restart automatically

Usually you should only call :func:`~keepitfresh.is_fresh` if you're not
updating. Otherwise do this::

    >>> try:
    ...     freshen_up(**payload)
    ... except RuntimeError:
    ...     # no new version
    ...

For some further examples on base url and regex combos take a look at this
`page <https://wiki.debian.org/debian/watch#Common_upstream_source_sites>`_,
originally meant for *uscan* but also usable for this package.


Reference
---------

.. autofunction:: keepitfresh.freshen_up

.. autofunction:: keepitfresh.is_fresh

.. autofunction:: keepitfresh.get_file_urls

.. autofunction:: keepitfresh.get_update_version

.. autofunction:: keepitfresh.dl_unpack

.. autofunction:: keepitfresh.overwrite_restart

.. toctree::
    :hidden:

    self
