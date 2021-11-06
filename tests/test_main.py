import os
from pathlib import Path

import cloudconvert
import pytest
from mock.mock import call

from flac_converter.main import main, convert_file_to_mp3, CloudConvertError

DATA_FOLDER = Path(__file__).parent.resolve().joinpath("data")
FLAC_FILE_NAME = "sample4"


@pytest.fixture(scope="module")
def connect_to_sandbox():
    cloudconvert.configure(api_key=os.environ['API_KEY'], sandbox=True)


@pytest.fixture(scope="module", autouse=True)
def reset_sandbox(connect_to_sandbox):
    """Cleanup the old tasks so we are not blocked"""
    tasks = cloudconvert.Job.all()

    for task in tasks:
        cloudconvert.Job.delete(task['id'])


def test_convert_file_to_mp3_non_existing_file():
    with pytest.raises(Exception) as excinfo:
        convert_file_to_mp3("/random/path.flac")
    assert "Does not find the exact path of the file: /random/path.flac" in str(excinfo)


def test_convert_file_to_mp3_ape_file():
    with pytest.raises(CloudConvertError) as excinfo:
        convert_file_to_mp3(DATA_FOLDER.joinpath("И. Савчук - Смуглянка.ape"))
    assert excinfo.value.failed_task['code'] == "INVALID_CONVERSION_TYPE"


def test_convert_file_to_mp3_not_whitelisted_file():
    with pytest.raises(CloudConvertError) as excinfo:
        convert_file_to_mp3(DATA_FOLDER.joinpath("not_whitelisted.flac"))
    assert excinfo.value.failed_task['code'] == "SANDBOX_FILE_NOT_ALLOWED"


def test_convert_file_to_mp3_flac_file():
    try:  # clean before test - just in case
        os.remove(DATA_FOLDER.joinpath(FLAC_FILE_NAME + ".mp3"))
    except OSError:
        pass

    convert_file_to_mp3(DATA_FOLDER.joinpath(FLAC_FILE_NAME + ".flac"))

    # clean after test - if the file wasn't created this would fail
    os.remove(DATA_FOLDER.joinpath(FLAC_FILE_NAME + ".mp3"))


def test_main_crash_no_api_key(monkeypatch):
    monkeypatch.delenv('API_KEY')
    with pytest.raises(KeyError) as excinfo:
        main('/mnt/e/CarMusic/*.flac')
    assert "API_KEY" in str(excinfo)


@pytest.mark.parametrize("sandbox_environ", ["True", "1", "true"])
def test_main_use_sandbox(monkeypatch, mocker, sandbox_environ):
    # mocked dependencies
    monkeypatch.setenv('API_KEY', 'made_up')
    monkeypatch.setenv('USE_SANDBOX', sandbox_environ)
    mock_configure = mocker.MagicMock(name='configure')
    mocker.patch('flac_converter.main.cloudconvert.configure', new=mock_configure)
    mock_glob = mocker.MagicMock(name='glob')
    mocker.patch('flac_converter.main.glob.glob', new=mock_glob)

    main('/mnt/e/CarMusic/*.flac')
    mock_configure.assert_called_once_with(api_key='made_up', sandbox=True)


@pytest.mark.parametrize("sandbox_environ", ["", "0", "false", "FALSE"])
def test_main_use_production(monkeypatch, mocker, sandbox_environ):
    # mocked dependencies
    monkeypatch.setenv('API_KEY', 'made_up')
    monkeypatch.setenv('USE_SANDBOX', sandbox_environ)
    mock_configure = mocker.MagicMock(name='configure')
    mocker.patch('flac_converter.main.cloudconvert.configure', new=mock_configure)
    mock_glob = mocker.MagicMock(name='glob')
    mocker.patch('flac_converter.main.glob.glob', new=mock_glob)

    main('/mnt/e/CarMusic/*.flac')
    mock_configure.assert_called_once_with(api_key='made_up', sandbox=False)


def test_main_some_files_ignored(monkeypatch, mocker):
    # mocked dependencies
    monkeypatch.setenv('API_KEY', 'made_up')
    mock_configure = mocker.MagicMock(name='configure')
    mocker.patch('flac_converter.main.cloudconvert.configure', new=mock_configure)

    all_flac_files = ['/mnt/e/CarMusic/Johnny Cash - The Man Comes Around.flac',
                      '/mnt/e/CarMusic/Johnny Cash - The Ways Of A Woman In Love.flac',
                      '/mnt/e/CarMusic/Johnny Cash - There You Go.flac',
                      '/mnt/e/CarMusic/Johnny Cash - Train Of Love.flac',
                      '/mnt/e/CarMusic/Johnny Cash - Wanted Man.flac']
    mock_glob = mocker.MagicMock(name='glob')
    mock_glob.return_value = iter(all_flac_files)
    mocker.patch('flac_converter.main.glob.glob', new=mock_glob)

    all_mp3_files = ['/mnt/e/CarMusic/Johnny Cash - The Man Comes Around.mp3',
                     '/mnt/e/CarMusic/Johnny Cash - The Ways Of A Woman In Love.mp3',
                     '/mnt/e/CarMusic/Johnny Cash - There You Go.mp3',
                     '/mnt/e/CarMusic/Johnny Cash - Train Of Love.mp3',
                     '/mnt/e/CarMusic/Johnny Cash - Wanted Man.mp3']
    mock_isfile = mocker.MagicMock(name='isfile')
    mock_isfile.side_effect = [False, True, False, False, True]
    mocker.patch('flac_converter.main.os.path.isfile', new=mock_isfile)

    mock_convert_file_to_mp3 = mocker.MagicMock(name='convert_file_to_mp3')
    mocker.patch('flac_converter.main.convert_file_to_mp3',
                 new=mock_convert_file_to_mp3)

    # act
    main('/mnt/e/CarMusic/*.flac')

    # asserts
    assert 5 == mock_isfile.call_count
    mock_isfile.assert_has_calls(calls=[call(file) for file in all_mp3_files])

    assert 3 == mock_convert_file_to_mp3.call_count
    mock_convert_file_to_mp3.assert_has_calls(
        calls=[call(all_flac_files[0]), call(all_flac_files[2]),
               call(all_flac_files[3]), ])
