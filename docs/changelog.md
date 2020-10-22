# changelog

* **`0.4.2`  CLI overhaul **
  * Subcommands to divide up the functionality of the library. 
    * Implemented to make accessing backend schemas easier when testing the frontend; instead of starting the whole server, run `sf.py dump <path>`. The server is now a subcommand, `serve`. 
    * Potentially useful commands to add in the future
      * `analyze` could run a single analysis as specified in a .json file
      * `checkout` could set the repository to a specific version
      * `setup` could replace in-repo setup scripts
    * It may also be interesting to make the commands accessible from the frontend
  * Some major naming changes
    * Entry point script `shapeflow.py` becomes `sf.py`
    * Server-related stuff renamed from `main` to `server`
* **[`0.4.1`](https://github.com/ybnd/shapeflow/releases/tag/0.4.1) Useability improvements and tutorial **
  * Tutorials and high-level documentation
* **`0.4.0` Rebranding**

A short summary of the major changes in the older versions will be added soon.

