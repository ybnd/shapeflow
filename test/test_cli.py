import abc
import sys
import io
import shutil
import unittest
from typing import List, Type, Callable, Any
from unittest.mock import patch, Mock, PropertyMock, call
from pathlib import Path

import git
import requests
import urllib
import tarfile

import shapeflow.cli
import shapeflow.server
import shapeflow.config


def noop(*_, **__):
    pass


@patch('shapeflow.server.ShapeflowServer.serve', Mock('serve'))
@patch('argparse.ArgumentParser.exit', noop)
class SfTest(unittest.TestCase):
    def test_no_arguments(self):
        shapeflow.cli.Sf()

        self.assertEqual(1, shapeflow.server.ShapeflowServer.serve.call_count)

    def test_version(self):
        with patch('sys.stdout', io.StringIO()) as stdout:
            shapeflow.cli.Sf(['--version'])
            self.assertIn(shapeflow.__version__, stdout.getvalue())

    def test_valid_commands(self):
        for command in shapeflow.cli.Command:
            shapeflow.cli.Sf([str(command)])

    def test_invalid_commands(self):
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, ['sevre'])
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, [''])
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, ['dmp'])
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, ['nope'])

    def test_help_global(self):
        with patch('sys.stdout', io.StringIO()) as stdout:
            shapeflow.cli.Sf(['--help'])
            out = stdout.getvalue()

            self.assertIn(shapeflow.cli.Sf.parser.description.strip(), out)
            self.assertIn(shapeflow.cli.Sf.__help__().strip(), out)
            for c in shapeflow.cli.Command:
                self.assertIn(str(c).strip(), out)
                self.assertIn(c.__usage__().strip(), out)

    def test_all_commands_help_command(self):
        for c in shapeflow.cli.Command:
            with patch('sys.stdout', io.StringIO()) as stdout:
                shapeflow.cli.Sf(['--help', str(c)])
                out = stdout.getvalue()

                self.assertIn(str(c).strip(), out)
                self.assertIn(c.__usage__().strip(), out)


class CommandTest(abc.ABC, unittest.TestCase):
    command: Type[shapeflow.cli.Command]
    instance: shapeflow.cli.Command
    mocks: List[Mock] = []

    def tearDown(self) -> None:
        for mock in self.mocks:
            mock.reset_mock()

    def test_valid_command(self):
        self.assertTrue(self.command in shapeflow.cli.Command)


class MockServerInstance():
    serve = Mock(name='shapeflow.server.serve')


class MockServer():
    __new__ = Mock(name='__new__', return_value=MockServerInstance)


class MockSockInstance():
    connect_ex = Mock(name='connect_ex', side_effect=[0, 0, 1])


class MockSock():
    __init__ = noop
    __enter__ = Mock(name='__enter__', return_value=MockSockInstance)
    __exit__ = noop


class MockRequests():
    post = Mock(name='post', return_value=None)


@patch('shapeflow.server.ShapeflowServer', MockServer)
@patch('socket.socket', MockSock)
@patch('requests.post', MockRequests.post)
class ServeTest(CommandTest):
    command = shapeflow.cli.Serve
    mocks = [
        MockServerInstance.serve,
        MockSockInstance.connect_ex,
        MockRequests.post,
    ]

    def tearDown(self) -> None:
        super().tearDown()
        MockSockInstance.connect_ex.side_effect = [0, 0, 1]  # explicitly :(

    def test_no_arguments(self):
        self.instance = self.command()

        self.assertEqual(3, MockSockInstance.connect_ex.call_count)
        self.assertEqual(1, MockRequests.post.call_count)

        self.assertEqual(1, MockServerInstance.serve.call_count)
        self.assertEqual(
            call(host='127.0.0.1', port=7951, open=True),
            MockServerInstance.serve.call_args,
        )

    def test_valid_arguments(self):
        self.command(['--host', 'localhost', '--port', '1234', '--background'])

        self.assertEqual(3, MockSockInstance.connect_ex.call_count)
        self.assertEqual(1, MockRequests.post.call_count)

        self.assertEqual(1, MockServerInstance.serve.call_count)
        self.assertEqual(
            call(host='localhost', port=1234, open=False),
            MockServerInstance.serve.call_args,
        )


class DumpTest(CommandTest):
    command = shapeflow.cli.Dump

    def test_no_arguments(self):
        self.instance = self.command()

        self.assertTrue(Path('schemas.json').is_file())
        self.assertTrue(Path('settings.json').is_file())

        Path('schemas.json').unlink()
        Path('settings.json').unlink()

    def test_dir(self):
        self.command(['--dir', 'stuff'])

        self.assertTrue(Path('stuff').is_dir())
        self.assertTrue(Path('stuff/schemas.json').is_file())
        self.assertTrue(Path('stuff/settings.json').is_file())
        shutil.rmtree('stuff')


class GeneralMock(object):
    call_count: int
    return_value: Any

    def __init__(self, return_value: Any = None):
        self.call_count = 0
        self.return_value = return_value

    def __getattr__(self, item):
        if not item in self.__annotations__:
            if not (item in self.__dict__):
                self.__dict__[item] = GeneralMock(return_value=GeneralMock())
            return self.__dict__[item]
        else:
            return self.__dict__[item]

    def __setattr__(self, item, value: Any):
        if not item in self.__annotations__:
            self.__dict__[item] = value
        else:
            self.__dict__[item] = value

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        if self.return_value is not None:
            return self.return_value
        else:
            return GeneralMock()

    def reset_mock(self) -> None:
        self.call_count = 0
        self.return_value = None
        for key in self.__dict__.keys():
            if not key in self.__annotations__:
                self.__dict__.pop(key)


mock_repo = GeneralMock()


@patch('git.Repo', mock_repo)
class UpdateTest(CommandTest):
    command = shapeflow.cli.Update
    instance: shapeflow.cli.Update

    def test_no_arguments(self):
        self.command.is_up_to_date = Mock('is_up_to_date', return_value=False)
        self.command._handle_local_changes = Mock('_handle_local_changes', return_value=False)

        with patch('shapeflow.cli.Update._update', Mock('_update', noop)):
            self.instance = self.command()
            self.assertEqual(0, self.instance._update.call_count)

    def test_no_arguments_confirm_prompt(self):
        self.command.is_up_to_date = Mock('is_up_to_date', return_value=False)
        self.command._handle_local_changes = Mock('_handle_local_changes', return_value=True)

        with patch('shapeflow.cli.Update._update', Mock('_update', noop)):
            self.instance = self.command()
            self.assertEqual(1, self.instance._update.call_count)

    def test_no_arguments_up_to_date(self):
        self.command.is_up_to_date = Mock('is_up_to_date', return_value=True)

        with patch('shapeflow.cli.Update._update', Mock('_update', noop)):
            self.instance = self.command()

            self.assertEqual(0, self.instance._update.call_count)

    def test_force(self):
        self.command.is_up_to_date = Mock('is_up_to_date', return_value=False)

        with patch('shapeflow.cli.Update._update', Mock('_update', noop)):
            self.instance = self.command(['--discard-changes'])
            self.assertEqual(1, self.instance._update.call_count)

    def test_up_to_date_force(self):
        self.command.is_up_to_date = Mock('is_up_to_date', return_value=True)

        with patch('shapeflow.cli.Update._update', Mock('_update', noop)):
            self.instance = self.command(['--discard-changes'])
            self.assertEqual(0, self.instance._update.call_count)

    def _silent_init(self):
        self.command.is_up_to_date = Mock('is_up_to_date', return_value=True)
        self.instance = self.command()

    def test_update_at_tag(self):
        self._silent_init()

        self.instance.repo.head.is_detached = True
        self.instance._latest = '0.0.0'
        self.instance.repo.git.checkout = Mock('checkout', noop)
        self.instance._get_compiled_ui = Mock('_get_compiled_ui', noop)
        self.instance._update()

        self.assertEqual(1, self.instance.repo.git.checkout.call_count)
        self.assertEqual(
            call(self.instance.latest),
            self.instance.repo.git.checkout.call_args
        )
        self.assertEqual(1, self.instance._get_compiled_ui.call_count)


    def test_update_at_branch(self):
        self._silent_init()

        self.instance.repo.head.is_detached = False
        self.instance.repo.git.pull = Mock('checkout', noop)
        self.instance._update()

        self.assertEqual(1, self.instance.repo.git.pull.call_count)


@patch('git.Repo', mock_repo)
class CheckoutTest(CommandTest):
    command = shapeflow.cli.Checkout
    instance: shapeflow.cli.Checkout

    def test_raise_on_invalid_ref(self):
        self.assertRaises(shapeflow.cli.CliError, self.command, ['not-a-ref'])

    def test_after_0_4_4(self):
        self.command._is_a_ref = Mock('_is_a_ref', return_value=True)
        self.command._handle_local_changes = Mock(
            '_handle_local_changes', return_value=True
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)

        self.instance = self.command(['0.4.5'])

        self.assertEqual(1, self.command._handle_local_changes.call_count)
        self.assertEqual(1, self.command._get_compiled_ui.call_count)
        self.assertEqual(1, self.instance.repo.git.checkout.call_count)

    def test_before_0_4_4(self):
        self.command._is_a_ref = Mock('_is_a_ref', return_value=True)
        self.command._checkout_anyway = Mock(
            '_checkout_anyway', return_value=False
        )
        self.command._handle_local_changes = Mock(
            '_handle_local_changes', return_value=True
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)

        self.instance = self.command(['0.4.2'])

        self.assertEqual(0, self.command._handle_local_changes.call_count)
        self.assertEqual(0, self.command._get_compiled_ui.call_count)
        self.assertEqual(0, self.instance.repo.git.checkout.call_count)

    def test_before_0_4_4_checkout_anyway(self):
        self.command._is_a_ref = Mock('_is_a_ref', return_value=True)
        self.command._checkout_anyway = Mock(
            '_checkout_anyway', return_value=True
        )
        self.command._handle_local_changes = Mock(
            '_handle_local_changes', return_value=True
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)

        self.instance = self.command(['0.4.2'])

        self.assertEqual(1, self.command._handle_local_changes.call_count)
        self.assertEqual(1, self.command._get_compiled_ui.call_count)
        self.assertEqual(1, self.instance.repo.git.checkout.call_count)


class GetCompiledUiTest(CommandTest):
    command = shapeflow.cli.GetCompiledUi
    instance: shapeflow.cli.GetCompiledUi

    def _clear(self):
        for path in [Path('ui/dist/somefile'), Path('ui/dist'), Path('ui')]:
            if path.exists():
                if path.is_dir():
                    path.rmdir()
                elif path.is_file():
                    path.unlink()

    def setUp(self) -> None:
        self._clear()

    def tearDown(self) -> None:
        self._clear()

    def test_no_ui_dir(self):
        self.command._prompt_replace_ui = Mock(
            '_prompt_replace_ui', return_value=False
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)
        self.instance = self.command()

        self.assertEqual(0, self.command._prompt_replace_ui.call_count)
        self.assertEqual(1, self.command._get_compiled_ui.call_count)

    def test_empty_ui_dir(self):
        Path('ui').mkdir()
        Path('ui/dist').mkdir()

        self.command._prompt_replace_ui = Mock(
            '_prompt_replace_ui', return_value=False
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)
        self.instance = self.command()

        self.assertEqual(0, self.command._prompt_replace_ui.call_count)
        self.assertEqual(1, self.command._get_compiled_ui.call_count)

    def test_nonempty_ui_dir_prompt_no(self):
        Path('ui').mkdir()
        Path('ui/dist').mkdir()
        Path('ui/dist/somefile').touch()

        self.command._prompt_replace_ui = Mock(
            '_prompt_replace_ui', return_value=False
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)
        self.instance = self.command()

        self.assertEqual(1, self.command._prompt_replace_ui.call_count)
        self.assertEqual(0, self.command._get_compiled_ui.call_count)

    def test_nonempty_ui_dir_prompt_yes(self):
        Path('ui').mkdir()
        Path('ui/dist').mkdir()
        Path('ui/dist/somefile').touch()

        self.command._prompt_replace_ui = Mock(
            '_prompt_replace_ui', return_value=True
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)
        self.instance = self.command()

        self.assertEqual(1, self.command._prompt_replace_ui.call_count)
        self.assertEqual(1, self.command._get_compiled_ui.call_count)

    def test_nonempty_ui_dir_replace(self):
        Path('ui').mkdir()
        Path('ui/dist').mkdir()
        Path('ui/dist/somefile').touch()

        self.command._prompt_replace_ui = Mock(
            '_prompt_replace_ui', return_value=True
        )
        self.command._get_compiled_ui = Mock('_get_compiled_ui', noop)
        self.instance = self.command(['--replace'])

        self.assertEqual(0, self.command._prompt_replace_ui.call_count)
        self.assertEqual(1, self.command._get_compiled_ui.call_count)


class MockResponse(object):
    headers: dict
    status_code: int

    def __init__(self, url: str = '', status_code = 200):
        self.headers = {'location': url}
        self.status_code = status_code


latest_release_page = MockResponse(url='doesn\'t matter/but/this/does/1.2.3')
github_404_page = MockResponse(status_code=404)


@patch('git.Repo', GeneralMock)
class GitMixinTest(unittest.TestCase):
    class SomeGitCommand(shapeflow.cli.Command, shapeflow.cli.GitMixin):
        def __init__(self):
            pass

        def command(self) -> None:
            pass

    gc: SomeGitCommand

    def setUp(self) -> None:
        GeneralMock.call_count = 0
        self.gc = self.SomeGitCommand()

    def test_inits_repo(self):
        repo = self.gc.repo
        self.assertIsInstance(repo, GeneralMock)

        self.assertEqual(1, repo.remote.call_count)
        self.assertEqual(1, repo.remote().fetch.call_count)

    @patch('requests.head', Mock('head', return_value=latest_release_page))
    def test_gets_latest_tag(self):

        latest = self.gc.latest

        self.assertEqual(1, requests.head.call_count)
        self.assertEqual(
            call(self.gc.URL + 'releases/latest'),
            requests.head.call_args
        )
        self.assertEqual('1.2.3', latest)

    def test_tag_passes_if_at_tag(self):
        self.gc.repo.git.describe = Mock('describe', return_value='1.2.3')

        tag = self.gc.tag
        self.assertEqual('1.2.3', tag)

    def test_tag_empty_string_if_not_at_tag(self):
        self.gc.repo.git.describe = Mock(
            'describe',
            side_effect=[git.GitCommandError('describe', '1')]
        )

        self.assertEqual('',  self.gc.tag)

    @patch('requests.head', Mock('get', return_value=latest_release_page))
    def test_checks_if_at_release_and_ok(self):
        ok = self.gc.is_at_release('0.1.2')

        self.assertEqual(1, requests.head.call_count)
        self.assertEqual(
            call(self.gc.URL + 'releases/tag/0.1.2'),
            requests.head.call_args
        )

        self.assertTrue(ok)

    @patch('requests.head', Mock('head', return_value=github_404_page))
    def test_checks_if_at_release_and_nope(self):
        ok = self.gc.is_at_release('0.1.2')

        assert isinstance(requests.head, Mock)
        self.assertEqual(1, requests.head.call_count)
        self.assertEqual(
            call(self.gc.URL + 'releases/tag/0.1.2'),
            requests.head.call_args
        )

        self.assertFalse(ok)


    def test_checks_if_up_to_date_at_tag_and_it_is(self):
        self.gc._latest = '1.2.3'
        self.gc.is_at_release = Mock('is_at_release', return_value=True)

        ok = self.gc.is_up_to_date('1.2.3')
        self.assertTrue(ok)

    def test_checks_if_up_to_date_at_tag_and_it_isnt(self):
        self.gc._latest = '1.2.3'
        self.gc.is_at_release = Mock('is_at_release', return_value=True)

        ok = self.gc.is_up_to_date('0.1.2')
        self.assertFalse(ok)

    @patch('tarfile.open', Mock('tarfile.open'))
    @patch('urllib.request.urlopen', Mock('urlopen'))
    @patch('requests.head', Mock('head', return_value=github_404_page))
    def test_get_ui_not_at_release(self):
        self.gc.repo.git.describe = Mock('describe', return_value='0.0.0')
        self.gc.is_at_release = Mock('is_at_release', return_value=False)

        self.assertRaises(shapeflow.cli.CliError, self.gc._get_compiled_ui)
        self.assertEqual(0, tarfile.open.call_count)
        self.assertEqual(0, urllib.request.urlopen.call_count)

    @patch('tarfile.open', Mock('tarfile.open'))
    @patch('urllib.request.urlopen', Mock('urlopen'))
    def test_get_ui_at_pre_ui_release(self):
        self.gc.repo.git.describe = Mock('describe', return_value='0.2.0')
        self.gc.is_at_release = Mock('is_at_release', return_value=True)

        self.gc._get_compiled_ui()
        self.assertEqual(0, tarfile.open.call_count)
        self.assertEqual(0, urllib.request.urlopen.call_count)

    @patch('tarfile.open', Mock('tarfile.open'))
    @patch('urllib.request.urlopen', Mock('urlopen', side_effect=Exception))
    def test_get_ui_at_broken_release_problem_with_page(self):
        self.gc.repo.git.describe = Mock('describe', return_value='0.4.0')
        self.gc.is_at_release = Mock('is_at_release', return_value=True)

        self.assertRaises(shapeflow.cli.CliError, self.gc._get_compiled_ui)
        self.assertEqual(0, tarfile.open.call_count)
        self.assertEqual(1, urllib.request.urlopen.call_count)

    @patch('tarfile.open', Mock('tarfile.open', side_effect=Exception))
    @patch('urllib.request.urlopen', Mock('urlopen'))
    def test_get_ui_at_broken_release_problem_with_archive(self):
        self.gc.repo.git.describe = Mock('describe', return_value='0.4.0')
        self.gc.is_at_release = Mock('is_at_release', return_value=True)

        self.assertRaises(shapeflow.cli.CliError, self.gc._get_compiled_ui)
        self.assertEqual(1, tarfile.open.call_count)
        self.assertEqual(1, urllib.request.urlopen.call_count)

    @patch('tarfile.open', Mock('tarfile.open'))
    @patch('urllib.request.urlopen', Mock('urlopen'))
    def test_get_ui_at_release_all_ok(self):
        self.gc.repo.git.describe = Mock('describe', return_value='0.4.0')
        self.gc.is_at_release = Mock('is_at_release', return_value=True)

        self.gc._get_compiled_ui()
        self.assertEqual(1, tarfile.open.call_count)
        self.assertEqual(1, urllib.request.urlopen.call_count)

    @patch('builtins.input', Mock('input'))
    def test_handle_local_changes_no_changes(self):
        self.gc.repo.is_dirty = Mock('is_dirty', return_value=False)
        self.gc.repo.head.reset = Mock('head.reset')

        self.assertTrue(self.gc._handle_local_changes(False))
        self.assertEqual(0, self.gc.repo.head.reset.call_count)
        self.assertEqual(0, input.call_count)

    @patch('builtins.input', Mock('input'))
    def test_handle_local_changes_no_changes_force(self):
        self.gc.repo.is_dirty = Mock('is_dirty', return_value=False)
        self.gc.repo.head.reset = Mock('head.reset')

        self.assertTrue(self.gc._handle_local_changes(True))
        self.assertEqual(0, self.gc.repo.head.reset.call_count)
        self.assertEqual(0, input.call_count)

    @patch('builtins.input', Mock('input', return_value='n'))
    def test_handle_local_changes_force(self):
        self.gc.repo.is_dirty = Mock('is_dirty', return_value=True)
        self.gc.repo.head.reset = Mock('head.reset')

        self.assertTrue(self.gc._handle_local_changes(True))
        self.assertEqual(1, self.gc.repo.head.reset.call_count)
        self.assertEqual(0, input.call_count)

    @patch('builtins.input', Mock('input', return_value='y'))
    def test_handle_local_changes_discard(self):
        self.gc.repo.is_dirty = Mock('is_dirty', return_value=True)
        self.gc.repo.head.reset = Mock('head.reset')
        self.gc.repo.index.diff = Mock('index.diff', return_value=[])
        self.gc.repo.untracked_files = []

        self.assertTrue(self.gc._handle_local_changes(False))
        self.assertEqual(1, self.gc.repo.head.reset.call_count)
        self.assertEqual(1, input.call_count)

    @patch('builtins.input', Mock('input', return_value='n'))
    def test_handle_local_changes_cancel(self):
        self.gc.repo.is_dirty = Mock('is_dirty', return_value=True)
        self.gc.repo.head.reset = Mock('head.reset')
        self.gc.repo.index.diff = Mock('index.diff', return_value=[])
        self.gc.repo.untracked_files = []

        self.assertFalse(self.gc._handle_local_changes(False))
        self.assertEqual(0, self.gc.repo.head.reset.call_count)
        self.assertEqual(1, input.call_count)


class GithubUrlTest(unittest.TestCase):
    BASE = shapeflow.cli.GitMixin.URL

    def test_latest_releases_page_redirect_to_latest_tag_page(self):
        URL = self.BASE + 'releases/latest'

        response = requests.head(URL)
        self.assertEqual(302, response.status_code)
        self.assertIn('releases/tag', response.headers['location'])

    def test_existing_release_tag_page_should_exist(self):
        URL = self.BASE + 'releases/tag/0.4.1'

        response = requests.head(URL)
        self.assertEqual(200, response.status_code)

    def test_not_a_release_tag_page_should_not_exist(self):
        URL = self.BASE + 'releases/tag/0.0.0'

        response = requests.head(URL)
        self.assertEqual(404, response.status_code)

    def test_existing_release_ui_dist_should_exist(self):
        URL = self.BASE + 'releases/download/0.4.1/dist-0.4.1.tar.gz'

        response = requests.head(URL)
        self.assertEqual(302, response.status_code)

    def test_not_a_release_ui_dist_should_not_exist(self):
        URL = self.BASE + 'releases/download/0.0.0/dist-0.0.0.tar.gz'

        response = requests.head(URL)
        self.assertEqual(404, response.status_code)


del CommandTest
