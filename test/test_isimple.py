import unittest
import sys
import os
import shutil
import subprocess
from typing import List
import warnings

import isimple


# class HistoryAppTest(unittest.TestCase):
#     def test_load_save(self):  # todo: implement after refactoring isimple.HistoryApp
#         pass

class updateTest(unittest.TestCase):
    # step back twice to make sure that we're out of the repo
    branch: str = 'master'
    changes: bool = False
    requirements_changes: bool = False

    _commit_messages: List[str]
    _new_requirements: List[str]

    root: str = ''
    origin: str = os.path.abspath('../../mock-origin')

    original_url: str = ''
    original_branch: str = ''
    original_branch_original_commit: str = ''
    original_commit: str = ''


    @classmethod
    def setUpClass(cls) -> None:
        """Remember repo setup
            ! this is crucial, since these test will work with the actual repo
              and need to reset it to its original state each time
        """
        super(updateTest, cls).setUpClass()
        cls.root = os.getcwd()
        if cls.root.split('/')[-1] == 'test':  # handle call from PyCharm
            cls.root = '/'.join(os.getcwd().split('/')[:-1])

        # Remember our actual origin url, if we have one
        try:
            cls.original_url = cls.get_output(
                ['git', 'config', '--get', 'remote.origin.url']
            )
        except subprocess.CalledProcessError:
            cls.original_url = ''

        # Remember our actual branch
        cls.original_branch = cls.get_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
        )

        # Remember our actual commit
        cls.original_branch_original_commit = cls.get_output(
            ['git', 'rev-parse', 'HEAD']
        )

    def setUp(self) -> None:
        """Set up a mock remote repository
        """
        super(updateTest, self).setUp()

        # Remove our real remote, if it exists
        try:
            subprocess.check_call(['git', 'remote', 'remove', 'origin'])
        except subprocess.CalledProcessError as e:
            pass

        # If original branch is not master, try to check out the master branch
        if self.original_branch != 'master':
            try:
                subprocess.check_call(['git', 'checkout', 'master'])
            except subprocess.CalledProcessError:
                # If it doesn't exist, make it
                subprocess.check_call(['git', 'checkout', '-b', 'master'])

        # Remember what commit the master branch was on
        self.original_commit = self.get_output(
            ['git', 'rev-parse', 'HEAD']
        )

        # Clone this repo to a mock remote
        subprocess.check_call(['git', 'clone', self.root, self.origin])

        # Remove this remote as the mock remote's origin
        cwd = os.getcwd()
        os.chdir(self.origin)
        subprocess.check_call(['git', 'remote', 'remove', 'origin'])
        os.chdir(cwd)

        # Add the mock remote as this repo's origin
        subprocess.check_call(['git', 'remote', 'add', 'origin', self.origin])

        # Fetch
        subprocess.check_call(['git', 'fetch', 'origin'])

        # Track the master branch of the mock remote
        subprocess.check_call(
            ['git', 'branch', '-u', 'origin/master', 'master']
        )

        # Set name & email if not specified (e.g. on CI server)
        if not self.get_output(['git', 'config', '--get', 'user.name']):
            subprocess.check_call(
                ['git', 'config', 'user.name', 'temp']
            )
            subprocess.check_call(
                ['git', 'config', 'user.email', 'temp@temp.temp']
            )

        cwd = os.getcwd()
        os.chdir(self.origin)
        if not self.get_output(['git', 'config', '--get', 'user.name']):
            subprocess.check_call(
                ['git', 'config', 'user.name', 'temp']
            )
            subprocess.check_call(
                ['git', 'config', 'user.email', 'temp@temp.temp']
            )
        os.chdir(cwd)

    def tearDown(self) -> None:
        """Remove mock remote and reset repo to original state
        """
        super(updateTest, self).tearDown()

        self._commit_messages = []
        self._new_requirements = []

        # Delete the clone
        shutil.rmtree(self.origin)
        print(f"Deleted {self.origin}")

        # Remove mock origin from repo
        subprocess.check_call(['git', 'remote', 'remove', 'origin'])

        # Set our actual origin back to what it should be, if we had one
        if self.original_url:
            subprocess.check_call(
                ['git', 'remote', 'add', 'origin', self.original_url]
            )

            # Fetch
            subprocess.check_call(
                ['git', 'fetch', 'origin']
            )

        # Reset to our actual commit
        subprocess.check_call(
            ['git', 'reset', '--hard', self.original_commit]
        )

        # Reset to our actual branch
        subprocess.check_call(
            ['git', 'checkout', self.original_branch]
        )

        # Reset to our actual commit on our original branch
        subprocess.check_call(
            ['git', 'reset', '--hard', self.original_branch_original_commit]
        )

        # Set up our original branch to track origin, if we had one
        if self.original_url:
            subprocess.check_call(
                ['git', 'branch', '-u', 'origin/master', 'master']
            )

    def test(self):
        try:
            isimple.update(
                force=False, discard=False, pull=False, install=False
            )
        except SystemExit:
            pass
        self.assertRepoState(
            force=False, discard=False, pull=False, install=False
        )

    def test_force(self):
        try:
            isimple.update(
                force=True, discard=False, pull=False, install=False
            )
        except SystemExit:
            pass
        self.assertRepoState(
            force=False, discard=False, pull=False, install=False
        )

    def test_force_pull_reqs(self):
        try:
            isimple.update(
                force=True, discard=False, pull=True, install=True
            )
        except SystemExit:
            pass
        self.assertRepoState(
            force=False, discard=False, pull=False, install=False
        )

    def test_force_discard_pull(self):
        try:
            isimple.update(
                force=True, discard=True, pull=True, install=False
            )
        except SystemExit:
            pass
        self.assertRepoState(
            force=False, discard=False, pull=False, install=False
        )

    def test_force_discard_pull_reqs(self):
        try:
            isimple.update(
                force=True, discard=True, pull=True, install=True
            )
        except SystemExit:
            pass
        self.assertRepoState(
            force=False, discard=False, pull=False, install=False
        )

    def commit_origin(self, message: str):
        """Commit changes to mock upstream repository
        """
        # https://stackoverflow.com/questions/21406887/
        cwd = os.getcwd()
        os.chdir(self.origin)
        subprocess.check_call(['git', 'add', '-A'])
        subprocess.check_call(['git', 'commit', '-m', message])
        os.chdir(cwd)

        if not hasattr(self, '_commit_massages'):
            self._commit_messages = []  # todo: for some reason, updateTestChanges has no _commit_messages?

        self._commit_messages.append(message)

    @classmethod  # todo: maybe put a more general version of this in isimple.utility instead?
    def get_output(self, command: List[str]):
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE
        ).communicate()[0].decode('utf-8').strip(' \t\n\r')

    def assertRepoState(self, force=True, discard=True, pull=True, install=True):
        # Assert that the correct changes have been made
        if len(self._commit_messages):
            pass  # todo: assert that changes have been made

        # Assert that the correct packages have been installed
        if len(self._new_requirements):
            if install:
                freeze = self.get_output(
                    [sys.executable, '-m', 'pip', 'freeze']
                )
                self.assertTrue(
                    all([req in freeze for req in self._new_requirements])
                )


class updateTestChanges(updateTest):
    changes = True

    def setUp(self) -> None:
        super(updateTestChanges, self).setUp()

        # In the mock remote repository...
        # ...add a new file & commit
        with open(self.origin + '/new_file', 'w+') as f:
            f.write('new file contents')
            self.commit_origin('Add a file')

        # ...append to an existing file & commit
        with open(self.origin + '/README.md', 'a+') as f:
            f.write('\n New line in README')
            self.commit_origin('Append to a file')

        # ...remove a file & commit
        os.remove(self.origin + '/isimple/env.bat')
        self.commit_origin('Remove a file')

        # ...remove from a file & commit
        with open(self.origin + '/README.md', 'r+') as f:
            f.seek(0)
            for line in f.readlines():
                if not 'isimple' in line.lower():
                    f.write(line)
            f.truncate()
            self.commit_origin('Remove from a file')


class updateTestReqs(updateTest):
    changes = True
    # choose packages that are small, pure-python and well-maintained
    #  and *not* in requirements.txt
    _new_requirements = ['uncertainties']

    def setUp(self) -> None:
        """Modify requirements.txt
        """
        super(updateTestReqs, self).setUp()

        # In the mock remote repository...
        os.remove(self.origin + '/requirements.txt')

        # ...and add some new requirements to requirements.txt & commit
        with open(self.origin + '/requirements.txt', 'w+') as f:
            for req in self._new_requirements:
                f.write(req + '\n')
        self.commit_origin('Add requirements')

    def tearDown(self) -> None:
        """Uninstall self._new_requirements
        """
        super(updateTestReqs, self).tearDown()

        subprocess.check_call(
            ['pip', 'uninstall', *self._new_requirements, '-y']
        )


class updateTestDevelop(updateTest):
    branch = 'develop'


class updateTestChangesDevelop(updateTestChanges, updateTestDevelop):
    pass


class updateTestReqsDevelop(updateTestReqs, updateTestDevelop):
    pass


if __name__ == '__main__':
    unittest.main()
