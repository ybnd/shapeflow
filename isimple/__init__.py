import os
import sys
import git
from tkinter import messagebox, Tk


def find_repo() -> git.Repo:
    folder = os.path.dirname(__file__)  # Start looking in folder containing __file__
    steps_back = 0

    while steps_back < 20:
        try:
            return git.Repo(folder)
        except git.exc.InvalidGitRepositoryError:
            steps_back += 1
            folder = os.path.dirname(folder)  # If this folder doesn't contain a repo, step back and retry


def update(force=False):
    '''
    Auto-updating method for applications intended for "end-users".

    Usage:
        Include
            ```
                import isimple
                isimple.update()
            ```
            in script to check for updates before running.

        :param force:
        :return:
    '''

    # Start a tkinter window & hide it, otherwise messagebox spawns one anyway (annoying)
    root = Tk()
    root.withdraw()

    # Open an interface to the git repository at cwd
    # Will fail if called from a file outside of the repository
    repo = find_repo()

    # Check if on master branch -> if not, return.
    # ASSUMES THAT master BRANCH IS NAMED MASTER!
    if repo.active_branch.name == 'master' or force:
        # Check if origin/master is ahead -> dialog: update?
        # https://stackoverflow.com/questions/17224134/check-status-of-local-python-relative-to-remote-with-gitpython

        # ASSUMES THAT origin IS SET CORRECTLY!
        commits_behind = len([commit for commit in repo.iter_commits('master..origin/master')])
        if commits_behind > 0 or force:
            # Check if any changes have been made -> dialog: discard changes?
            changes = [item.a_path for item in repo.index.diff(None)] + repo.untracked_files
            changes = [change for change in changes if os.path.isfile(os.path.join(repo.working_dir, change))]  # todo: is this necessary?

            if len(changes) > 0 or force:
                changes = ' \n '.join(changes)  # Format changes line-per-line
                discard_changes = messagebox.askokcancel(
                    'Discard changes to isimple/master',
                    f"Changes to the following files will be discarded in order to update: \n \n {changes}"
                )

                if discard_changes:
                    # Hard reset head to discard changes
                    repo.git.reset('--hard')
                else:
                    return

            if messagebox.askokcancel('Update', 'Update the isimple repository?'):
                # Pull from default remote
                # ASSUMES THAT origin IS SET CORRECTLY, AND AS THE DEFAULT REMOTE!
                repo.git.pull()

                messagebox.showinfo("You'll have to run the script again, sorry.")

                sys.exit()  # Abort caller script (i.e. don't try to execute a script if it's out of date)


if __name__ == '__main__':
    update(True)  # Force checks (but not repo-level changes) - for debugging purposes