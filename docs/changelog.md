# changelog

* **`0.4.3` API overhaul**
  * Add frontend tests
    * And also some general clean-up and fixes in the process
  * Deprecate caching contexts and related functionality
    * We’re assuming that caching will never be performed *in advance* of an analysis. Instead, we rely on caching during an analysis to speed up any subsequent analyses.
  * Separate internal routing from general Flask routing
    * API routes are organised based on `Dispatcher` 
    * `Dispatcher` instances map addresses to `Endpoint` instances
    * Nested `Dispatcher` include the addresses of any child `Dispatcher` instances in their own address space
    * The top-level `Dispatcher` has a flat address space of all endpoints, which it uses to resolve requests
    * The Flask server delegates requests to this top-level `Dispatcher` for addresses starting with `/api/` 
  * Expose `Endpoint` instances with own `expose()` method instead of global function
  * Deprecate `RootInstance`
    * Implementation should not care about routing
    * *Note: this means that methods of `BackendInstance` subclass instances nested in `VideoAnalyzer` can no longer be exposed at `Endpoint` instances. Only methods of objects associated with `Dispatcher` instances can be exposed.*
  * More sensible API structure
    * Global top-level API at `api`
    * Group related functionality
      * `api`: general stuff
      * `api.fs`: dealing with files and directories
      * `api.cache`: dealing with the cache
      * `api.db`: dealing with the database
      * `api.va`: dealing with analyzers
      * `api.va.<id>`: dealing with a specific analyzer
  * Open analyzers are handled by new `Dispatcher` instances
    * Analyzer methods should be exposed with the placeholder `Dispatcher` at `api.va.__id__`
      * By themselves, methods exposed in this way can’t be invoked since they don’t have an instance yet
    * New analyzers are opened from `main._VideoAnalyzerManager` and given an `id`
      * Use shorter `id` strings for URL readability
      * Associate newly instantiated `VideoAnalyzer` with a new `Dispatcher` instance at `api.va.<id>`
      * This `Dispatcher`, binds methods exposed in `api.va.__id__` to the `VideoAnalyzer` instance
      * *Now* these methods can be invoked when requested by `/api/va/<id>/<endpoint>`
    * Included in top-level address space at launch to reduce address resolution overhead
  * Mirror API structure in frontend `api.js`
* **`0.4.2`  CLI overhaul**
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
* **[`0.4.1`](https://github.com/ybnd/shapeflow/releases/tag/0.4.1) Useability improvements and tutorial**
  * Tutorials and high-level documentation
* **`0.4.0` Rebranding**


* 

A short summary of the major changes in the older versions will be added soon.

