# dbcore

Lifted from [beets](https://github.com/beetbox/beets/) with love
* Commit 545c65d903e38d37fd2c1734ec69eac609bea035 (March 2, 2020)
    - [Original files](https://github.com/beetbox/beets/tree/545c65d903e38d37fd2c1734ec69eac609bea035/beets/dbcore)
    
* Modifications
    - Remove references to `beets` modules
        - `beets.util`: try to remove functionality where possible, otherwise include in `isimple.core.util`.
        - `beets.config`: replace with global defaults; we don't need the same level of flexibility as the `beets` library.
    - Remove unnecessary Python 2.7 support
        - `from __future__ import ...`
        - `beets.util.py3_path`
    - Remove templating (`beets.util.functemplate`), if possible!
    - Make `isimple.dbcore.query` much leaner, we don't need *nearly* as much functionality!
