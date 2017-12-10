from keepitfresh import updater
import os
import pathlib
import mock
import pytest
import zipfile


@mock.patch("keepitfresh.updater.urlopen")
def test_get_file_urls(mock_open):
    test_func = updater.get_file_urls

    mock_webpage = mock_open.return_value.__enter__.return_value
    mock_webpage.read.return_value = \
        (b'<!DOCTYPE html><html><head><title>'
         b'Links for uptodate</title></head><body>'
         b'<h1>Links for uptodate</h1>'
         b'<a href="/packages/example-0.1.1.tar.gz"'
         b'>example-0.1.1.tar.gz</a><br/>'
         b'<a href="../../packages/'
         b'example-0.1.0.zip">example-0.1.0.zip</a>'
         b'<br/><a href="../packages/'
         b'example-0.1.2.7z">example-0.1.2.7z</a>'
         b'<br/><a href="packages/example-0.1.3.rar">'
         b'example-0.1.3.rar</a><br/></body></html>')
    mock_webpage.headers.get_content_charset.return_value = 'utf8'

    test_url = "https://pypi.python.org/simple/example/"
    regex = r'example-(\d+\.\d+\.\d+)\.(?:tar\.gz|zip|rar|7z)'

    expected = {
            'https://pypi.python.org/'
            'packages/example-0.1.1.tar.gz': '0.1.1',
            'https://pypi.python.org/'
            'packages/example-0.1.0.zip': '0.1.0',
            'https://pypi.python.org/'
            'simple/packages/example-0.1.2.7z': '0.1.2',
            'https://pypi.python.org/'
            'simple/example/packages/example-0.1.3.rar': '0.1.3'}

    assert test_func(test_url, regex) == expected

    regex = r'mangledregex'

    with pytest.raises(ValueError):
        test_func(test_url, regex)


def test_get_update_version():
    test_func = updater.get_update_version

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
    test_func = updater.dl_unpack

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
