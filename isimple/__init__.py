import os
import sys
import time
import json


__update_interval__ = 30
__last_update__ = os.path.join(os.path.dirname(__file__), '.last-update')
__isimple__ = os.path.dirname(__file__)


class HistoryApp:
    __history_path__ = os.path.join(__isimple__, '.history')

    def __init__(self, file):
        self.full_history = {}
        self.history = {}

        self.key = __file__
        self.load_history()

    def reset_history(self):
        pass

    def load_history(self):
        try:
            with open(self.__history_path__, 'r') as f:
                self.full_history = json.load(f)

        except (json.decoder.JSONDecodeError, FileNotFoundError, KeyError) as e:
            self.reset_history()
            if e is KeyError:
                self.full_history[self.key] = self.history
            else:
                self.full_history = {self.key: self.history}
        self.get_own_history()
        self.unpack_history()

    def save_history(self):
        self.pack_history()
        with open(self.__history_path__, 'w+') as f:
            json.dump(self.full_history, f, indent=2)

    def get_own_history(self):
        self.history = self.full_history[self.key]

    def unpack_history(self):
        pass

    def pack_history(self):
        pass


def update(force=False):
    """
    Auto-updating method for applications intended for "end-users".

    Usage:
        Include
            ``` import isimple
                isimple.update() ```
            in scripts to check for updates before running.

        :param force:
        :return:
    """

    try:
        with open(__last_update__, 'r') as f:
            last_update = float(f.read())
    except FileNotFoundError:
        last_update = 0

    if time.time() - last_update > __update_interval__ or force:
        import git
        import warnings
        from distutils.util import strtobool

        def find_repo() -> git.Repo:

            folder = os.path.dirname(__file__)  # Start looking in folder containing __file__
            steps_back = 0

            while steps_back < 20:
                try:
                    return git.Repo(folder)
                except git.exc.InvalidGitRepositoryError:
                    steps_back += 1
                    folder = os.path.dirname(folder)  # If this folder doesn't contain a repo, step back and retry

        # Start a tkinter window & hide it, otherwise messagebox spawns one anyway (annoying)
        # root = Tk()
        # root.withdraw()

        # Open an interface to the git repository at cwd
        # Will fail if called from a file outside of the repository
        repo = find_repo()

        # Check if on master branch -> if not, return.
        # ASSUMES THAT master BRANCH IS NAMED MASTER!
        if repo.active_branch.name == 'master' or force:
            # Check if origin/master is ahead -> dialog: update?
            # https://stackoverflow.com/questions/17224134/check-status-of-local-python-relative-to-remote-with-gitpython
            # ASSUMES THAT origin IS SET CORRECTLY!


            try:
                repo.remote('origin').fetch()   # Fetch remote changes
                commits_behind = len([commit for commit in repo.iter_commits('master..origin/master')])
            except git.exc.GitCommandError as e:
                commits_behind = 0
                warnings.warn(f"Failed to fetch: {e.stderr} \n", stacklevel=3)

            if commits_behind > 0 or force:
                # Check if any changes have been made -> dialog: discard changes?
                changes = [item.a_path for item in repo.index.diff(None)] + repo.untracked_files
                changes = [change for change in changes if os.path.isfile(os.path.join(repo.working_dir, change))]  # todo: is this necessary?

                if len(changes) > 0 or force:
                    changes = ' \n '.join(changes)  # Format changes line-per-line
                    discard_changes = strtobool(input(
                        f"Changes to the following files will be discarded in order to update: \n \n {changes} \n \n Continue? "
                    ))

                    if discard_changes:
                        # Hard reset head to discard changes
                        repo.git.reset('--hard')
                    else:
                        return

                if strtobool(input('\n Update the isimple repository? ')):
                    # Pull from default remote
                    # ASSUMES THAT origin IS SET CORRECTLY, AND AS THE DEFAULT REMOTE!
                    repo.git.pull()
                    sys.exit()

    # Abort caller script (i.e. don't try to execute a script if it's out of date)


if __name__ == '__main__':
    update(True)  # For debugging purposes
