import os
import sys
import time
import json

__update_interval__ = 60 * 60 * 24
__last_update__ = os.path.join(os.path.dirname(__file__), '.last-update')
__isimple__ = os.path.dirname(__file__)
__history_path__ = os.path.join(__isimple__, '.history')


class HistoryApp(object):
    """Applications with history stored in JSON format in isimple/.history
    """
    def __init__(self, file):
        self.full_history = {}  # todo: should interact with isimple.video.VideoAnalysisElement._config
        self.history = {}

        self.key = file or __file__
        self.load_history()

    def reset_history(self):
        pass

    def load_history(self):
        try:
            with open(__history_path__, 'r') as f:
                self.full_history = json.load(f)

        except (
                json.decoder.JSONDecodeError, FileNotFoundError, KeyError
        ) as e:
            self.reset_history()
            if e is KeyError:
                self.full_history[self.key] = self.history
            else:
                self.full_history = {self.key: self.history}
        self.get_own_history()
        self.unpack_history()

    def save_history(self):
        self.pack_history()
        with open(__history_path__, 'w+') as f:
            json.dump(self.full_history, f, indent=2)

    def get_own_history(self):
        try:
            self.history = self.full_history[self.key]
        except KeyError:
            self.reset_history()
            self.full_history[self.key] = self.history

    def unpack_history(self):
        pass

    def pack_history(self):
        pass


def read_last_update_time():
    try:
        with open(__last_update__, 'r') as f:
            return float(f.read())
    except FileNotFoundError:
        write_last_update_time(0.0)
        return 0.0


def write_last_update_time(t=None):
    if t is None:
        t = time.time()
    with open(__last_update__, 'w+') as f:
        f.write(str(t))


def update(force=False, discard=None, pull=None, install=None):
    """Auto-updating method for applications intended for "end-users".

        Usage:
            Include
                ``` import isimple
                    isimple.update() ```
                in scripts to check for updates before running.

    :param force:
    :return:
    """

    time_since_update = time.time() - read_last_update_time()
    if time_since_update > __update_interval__ or force:

        import git
        import subprocess
        import warnings
        from distutils.util import strtobool

        def find_repo() -> git.Repo:
            # Start looking in folder containing __file__
            folder = os.path.dirname(__file__)
            steps_back = 0

            while steps_back < 20:
                try:
                    return git.Repo(folder)
                except git.exc.InvalidGitRepositoryError:
                    # If this folder is not a git repo, step back and retry
                    steps_back += 1
                    folder = os.path.dirname(folder)

            raise git.exc.InvalidGitRepositoryError

        # Start a tkinter window & hide it,
        #  otherwise messagebox spawns one anyway (annoying)
        # root = Tk()
        # root.withdraw()  # todo: is this a Windows thing?

        # Open an interface to the git repository at cwd
        # Will fail if called from a file outside of the repository
        repo = find_repo()

        # Check if on master branch -> if not, return.
        # ASSUMES THAT master BRANCH IS NAMED master!
        if repo.active_branch.name == 'master' or force:
            print(f"Last update was {round(time_since_update/3600)} "
                  f"hours ago. Checking for updates...")
            # Check if origin/master is ahead -> dialog: update?
            # https://stackoverflow.com/questions/17224134/
            # ASSUMES THAT `origin` IS SET CORRECTLY!

            try:
                repo.remote('origin').fetch()   # Fetch remote changes

                commits_to_pull = [
                    commit for commit
                    in repo.iter_commits('master..origin/master')
                ]
                commits_behind = len(commits_to_pull)
            except git.exc.GitCommandError as e:
                commits_to_pull = []
                commits_behind = 0
                repo = None
                warnings.warn(f"Failed to fetch: {e.stderr} \n", stacklevel=3)
            except UserWarning as w:
                warnings.warn('FAILED TO FETCH YO')

            if (repo is not None and commits_behind > 0) or force:
                print(f"You are {commits_behind} "
                      f"{'commit' if commits_behind == 1 else 'commits'} "
                      f"behind.")

                # Check if any changes have been made
                #  -> dialog: discard changes?
                changes = [item.a_path for item in repo.index.diff(None)] \
                          + repo.untracked_files
                changes = [
                    change for change
                    in changes
                    if os.path.isfile(os.path.join(repo.working_dir, change))
                ]

                if len(changes) > 0 or force:
                    # Format changes line-per-line
                    changes = ' \n '.join(changes)

                    print(f"Changes to the following files will be discarded "
                            f"in order to update: \n \n {changes} \n \n")
                    if discard is None:
                        discard = strtobool(input(f"\tDiscard? (y/n)"))

                    if discard:
                        # Hard reset head to discard changes
                        repo.git.reset('--hard')
                    else:
                        return

                if pull is None:
                    pull = strtobool(input('\nUpdate? (y/n) '))

                if pull:
                    # Pull from default remote
                    # ASSUMES THAT `origin` IS SET CORRECTLY,
                    # AND AS THE DEFAULT REMOTE! todo: need additional checks?
                    print(f"\nUpdating...")
                    repo.git.pull()
                    write_last_update_time()

                    changed_files = [
                        file for commit in commits_to_pull
                        for file in commit.stats.files.keys()
                    ]

                    if 'requirements.txt' in changed_files:
                        print(f"Project requirements have been updated.")
                        if install is None:
                            install = strtobool(input(f"\tInstall? (y/n)"))

                        if install:
                            print(f"Installing...")
                            cwd = os.getcwd()  # todo: this can be a context, maybe?
                            os.chdir(repo.working_dir)
                            # https://stackoverflow.com/questions/12332975
                            subprocess.check_call(
                                [
                                    sys.executable, '-m', 'pip',
                                    'install', '--upgrade',
                                    '-r', 'requirements.txt'
                                ]
                            )
                            os.chdir(cwd)

                    repo.close()

                    print(f"Done.")
                    sys.exit()
            else:
                print(f"You are up to date.")
                write_last_update_time()

    # todo: if out of date, maybe abort caller script
    #  (i.e. don't try to execute a script if it's out of date)


if __name__ == '__main__':
    update(True)  # For debugging purposes
