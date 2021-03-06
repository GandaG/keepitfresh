import http.server
import os
import pathlib
import stat
import zipfile
from platform import system
from threading import Thread

import keepitfresh
import mock


def test_get_file_urls(tmpdir):
    test_func = keepitfresh.get_file_urls

    tmpdir.ensure('example-0.1.0.zip', file=True)
    tmpdir.ensure('example-0.1.1.tar.gz', file=True)
    tmpdir.ensure('example-0.1.2.7z', file=True)
    tmpdir.ensure('example-0.1.3.rar', file=True)

    os.chdir(str(tmpdir))
    port = 8001
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a, **b: None
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("localhost", port), handler)

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    test_url = 'http://localhost:{}/'.format(port)

    regex = r'example-(\d+\.\d+\.\d+)\.(?:tar\.gz|zip|rar|7z)'
    expected = {
            '{}example-0.1.1.tar.gz'.format(test_url): '0.1.1',
            '{}example-0.1.0.zip'.format(test_url): '0.1.0',
            '{}example-0.1.2.7z'.format(test_url): '0.1.2',
            '{}example-0.1.3.rar'.format(test_url): '0.1.3'}
    assert test_func(test_url, regex) == expected

    regex = r'mangledregex'
    assert test_func(test_url, regex) == {}

    server.shutdown()


def test_get_update_version():
    test_func = keepitfresh.get_update_version

    file_dict = {
            'https://pypi.python.org/'
            'packages/example-0.1.1.tar.gz': '0.1.1',
            'https://pypi.python.org/'
            'packages/example-0.1.0.zip': '0.1.0',
            'https://pypi.python.org/'
            'simple/packages/example-0.1.2.7z': '0.1.2',
            'https://pypi.python.org/'
            'simple/example/packages/example-0.1.3.rar': '0.1.3'}

    cur_ver = '0.0.0'
    expected = ('https://pypi.python.org/simple/'
                'example/packages/example-0.1.3.rar', '0.1.3')
    assert test_func(file_dict, cur_ver) == expected

    cur_ver = '0.1.3'
    expected = ()
    assert test_func(file_dict, cur_ver) == expected


def test_dl_unpack(tmpdir):
    test_func = keepitfresh.dl_unpack

    tmpdir = str(tmpdir)
    output = os.path.join(tmpdir, 'out')
    zip_file = os.path.join(tmpdir, 'example.zip')
    example_dir = os.path.join(tmpdir, 'example')
    example_dir_file = os.path.join(example_dir, 'example.file')
    example_file = os.path.join(tmpdir, 'example.file')

    os.mkdir(output)
    os.mkdir(example_dir)
    open(example_dir_file, 'w').close()
    open(example_file, 'w').close()

    with zipfile.ZipFile(zip_file, 'w') as zipf:
        zipf.write(example_file, os.path.basename(example_file))

    test_func(pathlib.Path(zip_file).as_uri(), output)
    assert os.listdir(output) == ['example.file']

    os.remove(os.path.join(output, 'example.file'))

    with zipfile.ZipFile(zip_file, 'w') as zipf:
        zipf.write(example_dir_file, os.path.relpath(example_dir_file, output))

    test_func(pathlib.Path(zip_file).as_uri(), output)
    assert os.listdir(output) == ['example']
    assert os.listdir(os.path.join(output, 'example')) == ['example.file']


@mock.patch("keepitfresh.os.execl")
def test_overwrite_restart(mock_exec, tmpdir):
    test_func = keepitfresh.overwrite_restart

    tmpdir = str(tmpdir)
    ow_file_dir = os.path.join(tmpdir, 'example')

    in_file = os.path.join(tmpdir, 'examplev2.file')
    ow_file = os.path.join(ow_file_dir, 'examplev1.file')

    os.mkdir(ow_file_dir)

    open(in_file, 'w').close()
    open(ow_file, 'w').close()

    new_in_file = os.path.join(ow_file_dir, 'examplev2.file')

    if system() == 'Windows':
        open_patcher = mock.patch('keepitfresh.open')
        subprocess_patcher = mock.patch('keepitfresh.subprocess')
        exit_patcher = mock.patch('keepitfresh.os._exit')
        mock_open = open_patcher.start()
        subprocess_patcher.start()
        exit_patcher.start()

    test_func(in_file, ow_file, 'examplev2.file')

    if system() != 'Windows':
        assert os.listdir(ow_file_dir) == ['examplev2.file']
        file_st = os.stat(new_in_file)
        assert file_st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        mock_exec.assert_called_with(new_in_file, 'examplev2.file')
        os.remove(os.path.join(ow_file_dir, 'examplev2.file'))
    else:
        expected_bat = ('@echo off\ndel /q "{}"\n'
                        'copy /y /b "{}" "{}"\n'
                        'start "" "{}"\n'.format(ow_file, in_file, ow_file_dir,
                                                 new_in_file))
        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.write.assert_called_with(expected_bat)
        open_patcher.stop()
        subprocess_patcher.stop()
        exit_patcher.stop()

    in_dir = os.path.join(tmpdir, 'example_new')
    ow_dir = os.path.join(ow_file_dir, 'example_old')
    in_dir_file = os.path.join(in_dir, 'examplev2.file')
    ow_dir_file = os.path.join(ow_dir, 'examplev1.file')

    os.mkdir(in_dir)
    os.mkdir(ow_dir)

    open(in_dir_file, 'w').close()
    open(ow_dir_file, 'w').close()

    new_in_file = os.path.join(ow_file_dir, 'example_new', 'examplev2.file')

    if system() == 'Windows':
        open_patcher = mock.patch('keepitfresh.open')
        subprocess_patcher = mock.patch('keepitfresh.subprocess')
        exit_patcher = mock.patch('keepitfresh.os._exit')
        mock_open = open_patcher.start()
        subprocess_patcher.start()
        exit_patcher.start()

    test_func(in_dir, ow_dir, os.path.join('example_new', 'examplev2.file'))

    if system() != 'Windows':
        assert os.listdir(ow_file_dir) == ['example_new']
        assert os.listdir(os.path.join(ow_file_dir,
                                       'example_new')) == ['examplev2.file']
        file_st = os.stat(new_in_file)
        assert file_st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        mock_exec.assert_called_with(new_in_file, 'examplev2.file')
    else:
        expected_bat = ('@echo off\nrd /s /q "{}"\n'
                        'robocopy "{}" "{}" /e\n'
                        'start "" "{}"\n'.format(ow_dir, in_dir,
                                                 os.path.join(ow_file_dir,
                                                              'example_new'),
                                                 new_in_file))
        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.write.assert_called_with(expected_bat)
        open_patcher.stop()
        subprocess_patcher.stop()
        exit_patcher.stop()


def test_is_fresh(tmpdir):
    test_func = keepitfresh.is_fresh

    tmpdir.ensure('example-0.1.0.zip', file=True)
    tmpdir.ensure('example-0.1.1.zip', file=True)
    tmpdir.ensure('example-0.1.2.zip', file=True)
    tmpdir.ensure('example-0.1.3.zip', file=True)

    os.chdir(str(tmpdir))
    port = 8000
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a, **b: None
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("localhost", port), handler)

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    test_url = 'http://localhost:{}/'.format(port)
    regex = r'example-(\d+\.\d+\.\d+)\.(?:tar\.gz|zip|rar|7z)'

    assert not test_func(test_url, regex, '0.1.2')
    assert test_func(test_url, regex, '0.1.3')

    server.shutdown()


@mock.patch("keepitfresh.overwrite_restart")
@mock.patch("keepitfresh.extract_archive")
def test_freshen_up(mock_unpack, mock_restart, tmpdir):
    test_func = keepitfresh.freshen_up

    tmpdir = str(tmpdir)
    zip_file = os.path.join(tmpdir, 'example-0.1.3.zip')
    example_file = os.path.join(tmpdir, 'example.file')

    open(os.path.join(tmpdir, 'example-0.1.0.zip'), 'w').close()
    open(os.path.join(tmpdir, 'example-0.1.1.zip'), 'w').close()
    open(os.path.join(tmpdir, 'example-0.1.2.zip'), 'w').close()

    with open(example_file, 'w') as ofile:
        ofile.write('aaaa')

    with zipfile.ZipFile(zip_file, 'w') as zipf:
        zipf.write(example_file, os.path.basename(example_file))

    with open(example_file, 'w') as ofile:
        ofile.write('boop')

    os.chdir(tmpdir)
    port = 8100
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a, **b: None
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("localhost", port), handler)

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    test_url = 'http://localhost:{}/'.format(port)
    regex = r'example-(\d+\.\d+\.\d+)\.(?:tar\.gz|zip|rar|7z)'

    arg_pack = {
        'base_url': test_url,
        'regex': regex,
        'current_version': '0.0.0',
        'overwrite_item': example_file,
        'entry_point': 'example.file'}
    test_func(**arg_pack)
    server.shutdown()
    mock_unpack.assert_called_once()
    mock_restart.assert_called_once()
