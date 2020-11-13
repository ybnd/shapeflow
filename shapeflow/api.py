from typing import Dict, Optional, List, Callable, Tuple, Type, Any
import numpy as np
import shortuuid

from shapeflow.core import Dispatcher, Endpoint, stream_image, stream_json, stream_plain
from shapeflow.util.meta import bind
from shapeflow.maths.colors import HsvColor
from shapeflow.core.streaming import BaseStreamer, EventStreamer, PlainFileStreamer


# todo: also specify http methods maybe?
class _VideoAnalyzerDispatcher(Dispatcher):
    """| Video analyzer endpoints
       | Dispatches ``/api/va/<id>/<endpoint>``
    """

    state_transition = Endpoint(Callable[[bool], int])
    """| Trigger a state transition
       | :meth:`shapeflow.core.backend.BaseVideoAnalyzer.state_transition`
    """
    can_launch = Endpoint(Callable[[], bool])
    """| Returns ``True`` if the analyzer has enough of its configuration set up to launch
       | :meth:`shapeflow.video.VideoAnalyzer.can_launch`
    """
    can_analyze = Endpoint(Callable[[], bool])
    """| Returns ``True`` if the analyzer has enough of its configuration set up to analyze
       | :meth:`shapeflow.video.VideoAnalyzer.can_analyze`
    """
    launch = Endpoint(Callable[[], bool])
    """| Launch the analyzer
       | :meth:`shapeflow.core.backend.BaseVideoAnalyzer.launch`
    """
    commit = Endpoint(Callable[[], bool])
    """| Commit the analyzer to the database
       | :meth:`shapeflow.core.backend.BaseVideoAnalyzer.commit`
    """
    analyze = Endpoint(Callable[[], bool])
    """| Run an analysis
       | :meth:`shapeflow.video.VideoAnalyzer.analyze`
    """
    cancel = Endpoint(Callable[[], None])
    """| Cancel an analysis
       | :meth:`shapeflow.core.backend.BaseVideoAnalyzer.cancel`
    """
    get_config = Endpoint(Callable[[], dict], stream_json)
    """| Return the analyzer's configuration
       | :meth:`shapeflow.core.backend.BaseVideoAnalyzer.get_config`
    """
    set_config = Endpoint(Callable[[dict, bool], dict])
    """Set the analyzer's configuration
    """
    undo_config = Endpoint(Callable[[str], dict])
    """Undo the latest change to the analyzer's configuration
    """
    redo_config = Endpoint(Callable[[str], dict])
    """Redo the latest undone change to the analyzer's configuration
    """
    estimate_transform = Endpoint(Callable[[dict], Optional[dict]])
    """Estimate a transform based on the provided ROI
    """
    turn_cw = Endpoint(Callable[[], None])
    """Turn the ROI clockwise
    """
    turn_ccw = Endpoint(Callable[[], None])
    """Turn the ROI counter-clockwise
    """
    flip_h = Endpoint(Callable[[], None])
    """Flip the ROI horizontally
    """
    flip_v = Endpoint(Callable[[], None])
    """Flip the ROI vertically
    """
    clear_roi = Endpoint(Callable[[], None])
    """Clear the ROI
    """
    get_overlay_png = Endpoint(Callable[[], bytes])
    """Return the overlay image
    """
    get_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    """Return the transformed frame at the provided frame number 
    (or the current frame number if ``None``)
    """
    set_filter_click = Endpoint(Callable[[float, float], None])
    """Configure a filter based on a click position 
    (in ROI-relative coordinates)
    """
    get_inverse_transformed_overlay = Endpoint(Callable[[], np.ndarray], stream_image)
    """Return the inverse transformed overlay image
    """
    get_inverse_overlaid_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    """Return the inverse overlaid frame at the provided frame number 
    (or the current frame number if ``None``)
    """
    get_state_frame = Endpoint(Callable[[Optional[int], Optional[int]], np.ndarray], stream_image)
    """Return the state frame at the provided frame number 
    (or the current frame number if ``None``)
    """
    get_colors = Endpoint(Callable[[], Tuple[str, ...]])
    """Return the color list
    """
    get_db_id = Endpoint(Callable[[], int])
    """Return the database ID associated with this analyzer
    """
    clear_filters = Endpoint(Callable[[], bool])
    """Clear all filter configuration
    """
    seek = Endpoint(Callable[[float], float])
    """Seek to the provided position (relative, 0-1)
    """

    get_relative_roi = Endpoint(Callable[[], dict])
    """Return the current ROI in relative coordinates
    """
    get_coordinates = Endpoint(Callable[[], Optional[list]])  # todo: deprecated?
    """Return the current relative coordinates
    """

    get_time = Endpoint(Callable[[int], float])
    """Return the current video timestamp
    """
    get_total_time = Endpoint(Callable[[], float])
    """Return the total time of the video file
    """
    get_fps = Endpoint(Callable[[], float])
    """Return the framerate of the video file
    """
    get_raw_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    """Return the raw frame at the provided frame number 
    (or the current frame number if ``None``)
    """
    get_seek_position = Endpoint(Callable[[], float])
    """Return the current seek position (relative, 0-1)
    """


class _VideoAnalyzerManagerDispatcher(Dispatcher):
    """| Video analyzer management endpoints
       | Dispatches ``/api/va/<endpoint>``
       | Active analyzers are handled by dispatchers at ``/api/va/<id>``
    """

    init = Endpoint(Callable[[], str])
    """Initialize a new analyzer
    """
    close = Endpoint(Callable[[str], bool])
    """Close an analyzer
    """

    start = Endpoint(Callable[[List[str]], bool])  # todo: these should respond with state?
    """Start analyzing the queue provided as a list of ID strings
    """
    stop = Endpoint(Callable[[], None])
    """Stop the queue
    """
    cancel = Endpoint(Callable[[], None])
    """Cancel the queue
    """

    state = Endpoint(Callable[[], dict])
    """Return the application state
    """
    save_state = Endpoint(Callable[[], None])
    """Save the application state to disk
    """
    load_state = Endpoint(Callable[[], None])
    """Load the application state from disk"""

    stream = Endpoint(Callable[[str, str], BaseStreamer])
    """Open a new stream for a given analyzer ID and endpoint
    """
    stream_stop = Endpoint(Callable[[str, str], None])
    """Close the stream for a given analyzer ID and endpoint
    """

    __id__ = _VideoAnalyzerDispatcher()
    """Prototype ``_VideoAnalyzerDispatcher`` instance.
    ``Endpoint`` instances exposed against this object will be propagated to
    all analyzers and bound to their respective instances."""


class _DatabaseDispatcher(Dispatcher):
    """| Database endpoints
       | Dispatches ``/api/db/<endpoint>``
    """
    get_recent_paths = Endpoint(Callable[[], Dict[str, List[str]]])
    """Get a list of recent video and design files
    """

    get_result_list = Endpoint(Callable[[int], dict])
    """Get a list of result IDs for a given analyzer ID
    """
    get_result = Endpoint(Callable[[int, int], dict])
    """Get the result for a given analyzer ID and result ID
    """
    export_result = Endpoint(Callable[[int, int], bool])
    """Export the result for a given analyzer ID and result ID"""

    clean = Endpoint(Callable[[], None])
    """Clean the database
    """
    forget = Endpoint(Callable[[], None])
    """Remove all entries from the database
    """


class _FilesystemDispatcher(Dispatcher):
    """| Filesystem endpoints
       | Dispatches ``/api/fs/<endpoint>``
    """
    select_video = Endpoint(Callable[[], Optional[str]])
    """Open a dialog to select a video file
    """
    select_design = Endpoint(Callable[[], Optional[str]])
    """Open a dialog to select a design file
    """

    check_video = Endpoint(Callable[[str], bool])
    """Check whether the given video file is valid
    """
    check_design = Endpoint(Callable[[str], bool])
    """Check whether the given video file is valid
    """

    open_root = Endpoint(Callable[[], None])
    """Open the application's root directory in a file explorer window
    """


class _CacheDispatcher(Dispatcher):
    """| Cache endpoints
       | Dispatches ``/api/cache/<endpoint>``
    """
    clear = Endpoint(Callable[[], None])
    """Clear the cache
    """
    size = Endpoint(Callable[[], str])
    """Get the size of the cache on disk
    """


class ApiDispatcher(Dispatcher):
    """| Root dispatcher
       | Invoked by ``Flask`` server for requests to ``/api/``
    """

    ping = Endpoint(Callable[[], bool])
    """Ping the backend
    """

    map = Endpoint(Callable[[], Dict[str, List[str]]])
    """Get API map
    """
    schemas = Endpoint(Callable[[], dict])
    """Get all schemas
    """
    normalize_config = Endpoint(Callable[[dict], dict])  # todo: deprecate this
    """Normalize the given config to the current version of the application
    """

    get_settings = Endpoint(Callable[[], dict])
    """Get the application settings
    """
    set_settings = Endpoint(Callable[[dict], dict])
    """Set the application settings
    """

    events = Endpoint(Callable[[], EventStreamer], stream_json)
    """Open an event stream
    """
    stop_events = Endpoint(Callable[[], None])
    """Stop the event stream
    """
    log = Endpoint(Callable[[], PlainFileStreamer], stream_plain)
    """Open a log stream
    """
    stop_log = Endpoint(Callable[[], None])
    """Stop the log stream
    """

    unload = Endpoint(Callable[[], bool])
    """Unload the application. In order to support page reloading, the backend 
    will wait for some time and quit if no further requests come in.
    """
    quit = Endpoint(Callable[[], bool])
    """Quit without waiting for incoming requests
    """
    restart = Endpoint(Callable[[], bool])
    """Restart the server
    """
    pid_hash = Endpoint(Callable[[], str])
    """Get the hashed process ID. Used to confirm server restart without
    exposing the actual PID.
    """

    fs = _FilesystemDispatcher()
    """
    """
    db = _DatabaseDispatcher()
    va = _VideoAnalyzerManagerDispatcher()
    cache = _CacheDispatcher()

api = ApiDispatcher()
"""Global :class:`~shapeflow.api.ApiDispatcher` instance. 
Endpoints should be exposed against this object. 
API calls should be dispatched from this object.
"""
