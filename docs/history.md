# history

The first year of development was at https://github.com/ybnd/isimple, named after the technology/the team that used it for some reason. 

Because the original repository was a bit too large, its git history was rewritten after moving to https://github.com/ybnd/shapeflow. The old repository is still up to preserve this history and to support legacy deployment scripts.

### The purge

[git-sizer](https://github.com/github/git-sizer/) and [bfg](https://rtyley.github.io/bfg-repo-cleaner/) are nifty tools.

* Removed compiled Javascript from `ui/dist/`

* [An accidentally huge screenshot](https://github.com/ybnd/isimple/commit/b65a0fe914a44bff6b2bba4ed155a9cd24d54e10)
* [An accidentally huge BMP file](https://github.com/ybnd/isimple/commit/af1b251b90efcd670d220de8f25975ff7bc8321d)

```shell
bfg --delete-folders dist .
bfg --delete-files datetime .
bfg --delete-files img.bmp .

git reflow expire --expire=now --all
git --prune=now --aggressive
```

All in all, the repo went from almost 30MB to about 6MB.