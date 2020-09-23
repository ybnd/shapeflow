# generating deployment scripts

Deployment scripts are generated with [`gitploy`](https://github.com/ybnd/gitploy).

1. Tag the release in `git`
2. Create a release on Github
3. Compile `ui/dist/`, compress it to a `.tar.gz` and upload to that release as a binary
4. Create or update your .ploy file in `shapeflow`‘s root directory:
   1. Start from [ploy](ploy)
   2. Add the tag of your release
   3. Double check that the check / setup script paths are still correct
5. Run `python -m gitploy` in `shapeflow`‘s root directory.

