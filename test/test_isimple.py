import unittest
import sys
import os
import shutil
import subprocess
from typing import List

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
        super(updateTest, cls).setUpClass()
        cls.root = os.getcwd()
        if cls.root.split('/')[-1] == 'test':  # handle call from PyCharm
            cls.root = '/'.join(os.getcwd().split('/')[:-1])

        # Remember our actual origin url
        cls.original_url = cls.get_output(
            ['git', 'config', '--get', 'remote.origin.url']
        )

        # Remember our actual branch
        cls.original_branch = cls.get_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
        )

        # Remember our actual commit
        cls.original_branch_original_commit = cls.get_output(
            ['git', 'rev-parse', 'HEAD']
        )

        # Delete the clone
        try:
            shutil.rmtree(cls.origin)
        except FileNotFoundError:
            pass

    def setUp(self) -> None:
        super(updateTest, self).setUp()
        self._commit_messages = []

        # Switch to self.branch
        #  Will abort in case of uncommitted changes
        subprocess.check_call(['git', 'checkout', self.branch])

        # Remember self.branch actual commit
        self.original_commit = self.get_output(['git', 'rev-parse', 'HEAD'])

        # Clone the repo
        subprocess.check_call(['git', 'clone', self.root, self.origin])

        # Set this temporary clone as the url for origin (!)
        subprocess.check_call(
            ['git', 'config', 'remote.origin.url', self.origin]
        )

    def tearDown(self) -> None:
        super(updateTest, self).tearDown()

        # Delete the clone
        shutil.rmtree(self.origin)
        print(f"Deleted {self.origin}")

        # Reset to our actual origin url
        subprocess.check_call(
            ['git', 'config', 'remote.origin.url', self.original_url]
        )

        # Fetch
        try:
            subprocess.check_call(
                ['git', 'fetch']
            )
        except subprocess.CalledProcessError:
            pass

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


    def test(self):
        isimple.update(
            force=False, do_discard=False, do_pull=False, do_reqs=False
        )
        self.assertRepoState()

    def test_force(self):
        isimple.update(
            force=True, do_discard=False, do_pull=False, do_reqs=False
        )
        self.assertRepoState()

    def test_force_pull_reqs(self):
        isimple.update(
            force=True, do_discard=False, do_pull=True, do_reqs=True
        )
        self.assertRepoState()

    def test_force_discard_pull(self):
        isimple.update(
            force=True, do_discard=True, do_pull=True, do_reqs=False
        )
        self.assertRepoState()

    def test_force_discard_pull_reqs(self):
        isimple.update(
            force=True, do_discard=True, do_pull=True, do_reqs=True
        )
        self.assertRepoState()

    def commit_origin(self, message: str):
        """Commit changes to mock upstream repository
        """
        # https://stackoverflow.com/questions/21406887/
        cwd = os.getcwd()
        os.chdir(self.origin)
        subprocess.check_call(['git', 'add', '-A'])
        subprocess.check_call(['git', 'commit', '-m', message])
        os.chdir(cwd)

        self._commit_messages.append(message)

    @classmethod  # todo: maybe put a more general version of this in isimple.utility instead?
    def get_output(self, command: List[str]):
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE
        ).communicate()[0].decode('utf-8').strip(' \t\n\r')

    def assertRepoState(self):
        if self.changes:
            pass  # todo: assert that changes have been made
            # message of HEAD should match self._commits[-1]



        if self.requirements_changes:
            pass  # todo: assert that requirements have been installed
            #


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
    requirements_changes = True
    # use nose & coverage since we already depend on them in CI
    _new_requirements = ['nose', 'coverage']


    def setUp(self) -> None:
        super(updateTestReqs, self).setUp()

        # In the mock remote repository...
        # ...add requirements to requirements.txt & commit
        with open(self.origin + '/requirements.txt', 'a+') as f:
            for req in self._new_requirements:
                f.write('\n' + req + '\n')  # make sure not to mangle lines
        self.commit_origin('Add requirements')


class updateTestDevelop(updateTest):
    branch = 'develop'


class updateTestChangesDevelop(updateTestChanges, updateTestDevelop):
    pass


class updateTestReqsDevelop(updateTestReqs, updateTestDevelop):
    pass


if __name__ == '__main__':
    unittest.main()
