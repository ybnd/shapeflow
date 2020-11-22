from typing import Dict, Optional, List, Callable, Tuple, Type, Any
import numpy as np
import shortuuid

from shapeflow.core import Dispatcher, Endpoint, stream_image, stream_json, stream_plain
from shapeflow.util.meta import bind
from shapeflow.maths.colors import HsvColor
from shapeflow.core.streaming import BaseStreamer, EventStreamer, PlainFileStreamer


# todo: also specify http methods maybe?
class _VideoAnalyzerDispatcher(Dispatcher):
    """Dispatches ``/api/va/<id>/<endpoint>``
    """
    status = Endpoint(Callable[[], dict], stream_json)
    """Get the analyzer's status
    
    :func:`shapeflow.core.backend.BaseAnalyzer.status`
    """
    state_transition = Endpoint(Callable[[bool], int])
    """Trigger a state transition
    
    :func:`shapeflow.core.backend.BaseAnalyzer.state_transition`
    """
    can_launch = Endpoint(Callable[[], bool])
    """Returns ``True`` if the analyzer has enough of its configuration set up to launch
            
    :func:`shapeflow.video.VideoAnalyzer.can_launch`
    """
    can_analyze = Endpoint(Callable[[], bool])
    """Returns ``True`` if the analyzer has enough of its configuration set up to analyze
            
    :func:`shapeflow.video.VideoAnalyzer.can_analyze`
    """
    launch = Endpoint(Callable[[], bool])
    """Launch the analyzer
    
    :func:`shapeflow.core.backend.BaseAnalyzer.launch`
    """
    commit = Endpoint(Callable[[], bool])
    """Commit the analyzer to the database

    :func:`shapeflow.core.backend.BaseAnalyzer.commit`
    """
    analyze = Endpoint(Callable[[], bool])
    """Run an analysis
        
    :func:`shapeflow.video.VideoAnalyzer.analyze`
    """
    cancel = Endpoint(Callable[[], None])
    """Cancel an analysis
        
    :func:`shapeflow.core.backend.BaseAnalyzer.cancel`
    """
    get_config = Endpoint(Callable[[], dict], stream_json)
    """Return the analyzer's configuration
    
    :func:`shapeflow.core.backend.BaseAnalyzer.get_config`
    """
    set_config = Endpoint(Callable[[dict, bool], dict])
    """Set the analyzer's configuration
    
    :func:`shapeflow.video.VideoAnalyzer.set_config`
    """
    undo_config = Endpoint(Callable[[Optional[str]], dict])
    """Undo the latest change to the analyzer's configuration
    
    :func:`shapeflow.video.VideoAnalyzer.undo_config`
    """
    redo_config = Endpoint(Callable[[Optional[str]], dict])
    """Redo the latest undone change to the analyzer's configuration
    
    :func:`shapeflow.video.VideoAnalyzer.redo_config`
    """
    estimate_transform = Endpoint(Callable[[Optional[dict]], Optional[dict]])
    """Estimate a transform based on the provided ROI
    
    :func:`shapeflow.video.VideoAnalyzer.estimate_transform`
    """
    turn_cw = Endpoint(Callable[[], None])
    """Turn the ROI clockwise
    
    :func:`shapeflow.video.VideoAnalyzer.turn_cw`
    """
    turn_ccw = Endpoint(Callable[[], None])
    """Turn the ROI counter-clockwise
    
    :func:`shapeflow.video.VideoAnalyzer.turn_ccw`
    """
    flip_h = Endpoint(Callable[[], None])
    """Flip the ROI horizontally
    
    :func:`shapeflow.video.VideoAnalyzer.flip_h`
    """
    flip_v = Endpoint(Callable[[], None])
    """Flip the ROI vertically
    
    :func:`shapeflow.video.VideoAnalyzer.flip_v`
    """
    clear_roi = Endpoint(Callable[[], None])
    """Clear the ROI
    
    :func:`shapeflow.video.VideoAnalyzer.clear_roi`
    """
    get_overlay_png = Endpoint(Callable[[], bytes])
    """Return the overlay image
    
    :func:`shapeflow.video.VideoAnalyzer.get_overlay_png`
    """
    get_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    """Return the transformed frame at the provided frame number 
    (or the current frame number if ``None``)
    
    :func:`shapeflow.video.VideoAnalyzer.get_transformed_frame`
    """
    set_filter_click = Endpoint(Callable[[float, float], None])
    """Configure a filter based on a click position 
    (in ROI-relative coordinates)
    
    :func:`shapeflow.video.VideoAnalyzer.set_filter_click`
    """
    get_inverse_transformed_overlay = Endpoint(Callable[[], np.ndarray], stream_image)
    """Return the inverse transformed overlay image
    
    :func:`shapeflow.video.VideoAnalyzer.get_inverse_transformed_overlay`
    """
    get_inverse_overlaid_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    """Return the inverse overlaid frame at the provided frame number 
    (or the current frame number if ``None``)
    
    :func:`shapeflow.video.VideoAnalyzer.get_inverse_overlaid_frame`
    """
    get_state_frame = Endpoint(Callable[[Optional[int], Optional[int]], np.ndarray], stream_image)
    """Return the state frame at the provided frame number 
    (or the current frame number if ``None``)
    
    :func:`shapeflow.video.VideoAnalyzer.get_state_frame`
    """
    get_colors = Endpoint(Callable[[], Tuple[str, ...]])
    """Return the color list
    
    :func:`shapeflow.video.VideoAnalyzer.get_colors`
    """
    get_db_id = Endpoint(Callable[[], int])
    """Return the database ID associated with this analyzer
    
    :func:`shapeflow.core.backend.BaseAnalyzer.get_db_id`
    """
    clear_filters = Endpoint(Callable[[], bool])
    """Clear all filter configuration
    
    :func:`shapeflow.video.VideoAnalyzer.clear_filters`
    """
    seek = Endpoint(Callable[[Optional[float]], float])
    """Seek to the provided position (relative, 0-1)
    
    :func:`shapeflow.video.VideoAnalyzer.seek`
    """

    get_relative_roi = Endpoint(Callable[[], dict])  # todo: ROI should always be relative, redundant
    """Return the current ROI in relative coordinates
    
    :func:`shapeflow.video.VideoAnalyzer.get_relative_roi`
    """
    get_coordinates = Endpoint(Callable[[], Optional[list]])  # todo: deprecated?
    """Return the current relative coordinates
    
    :func:`shapeflow.video.VideoAnalyzer.get_coordinates`
    """

    get_time = Endpoint(Callable[[Optional[int]], float])
    """Return the current time in the video in seconds
    
    :func:`shapeflow.video.VideoAnalyzer.get_time`
    """
    get_total_time = Endpoint(Callable[[], float])
    """Return the total time of the video file in seconds
    
    :func:`shapeflow.video.VideoAnalyzer.get_total_time`
    """
    get_fps = Endpoint(Callable[[], float])
    """Return the framerate of the video file
    
    :func:`shapeflow.video.VideoAnalyzer.get_fps`
    """
    get_raw_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    """Return the raw frame at the provided frame number 
    (or the current frame number if ``None``)
    
    :func:`shapeflow.video.VideoAnalyzer.read_frame`
    """
    get_seek_position = Endpoint(Callable[[], float])
    """Return the current seek position (relative, 0-1)
    
    :func:`shapeflow.video.VideoAnalyzer.get_seek_position`
    """


class _VideoAnalyzerManagerDispatcher(Dispatcher):
    """Dispatches ``/api/va/<endpoint>``, active analyzers are handled by dispatchers at ``/api/va/<id>``
    """

    init = Endpoint(Callable[[], str])
    """Initialize a new analyzer
    
    :func:`shapeflow.main._VideoAnalyzerManager.init`
    """
    close = Endpoint(Callable[[str], bool])
    """Close an analyzer
    
    :func:`shapeflow.main._VideoAnalyzerManager.close`
    """

    start = Endpoint(Callable[[List[str]], bool])  # todo: these should respond with state?
    """Start analyzing the queue provided as a list of ID strings
    
    :func:`shapeflow.main._VideoAnalyzerManager.q_start`
    """
    stop = Endpoint(Callable[[], None])
    """Stop the queue
    
    :func:`shapeflow.main._VideoAnalyzerManager.q_stop`
    """
    cancel = Endpoint(Callable[[], None])
    """Cancel the queue
    
    :func:`shapeflow.main._VideoAnalyzerManager.q_cancel`
    """

    state = Endpoint(Callable[[], dict])
    """Return the application state
    
    :func:`shapeflow.main._VideoAnalyzerManager.state`
    """
    save_state = Endpoint(Callable[[], None])
    """Save the application state to disk
    
    :func:`shapeflow.main._VideoAnalyzerManager.save_state`
    """
    load_state = Endpoint(Callable[[], None])
    """Load the application state from disk
    
    :func:`shapeflow.main._VideoAnalyzerManager.load_state`
    """

    stream = Endpoint(Callable[[str, str], BaseStreamer])
    """Open a new stream for a given analyzer ID and endpoint
    
    :func:`shapeflow.main._VideoAnalyzerManager.stream`
    """
    stream_stop = Endpoint(Callable[[str, str], None])
    """Close the stream for a given analyzer ID and endpoint
    
    :func:`shapeflow.main._VideoAnalyzerManager.stream_stop`
    """

    __id__ = _VideoAnalyzerDispatcher()
    """Prototype :class:`~shapeflow.api._VideoAnalyzerDispatcher` instance.
    
    :class:`~shapeflow.core.Endpoint` instances exposed against this object 
    will be propagated to all analyzers and bound to their respective instances.
    """


class _DatabaseDispatcher(Dispatcher):
    """Dispatches ``/api/db/<endpoint>``
    """
    get_recent_paths = Endpoint(Callable[[], Dict[str, List[str]]])
    """Get a list of recent video and design files
    
    :func:`shapeflow.db.History.get_paths`
    """

    get_result_list = Endpoint(Callable[[int], dict])
    """Get a list of result IDs for a given analyzer ID
    
    :func:`shapeflow.db.History.get_result_list`
    """
    get_result = Endpoint(Callable[[int, int], dict])
    """Get the result for a given analyzer ID and result ID
    
    :func:`shapeflow.db.History.get_result`
    """
    export_result = Endpoint(Callable[[int, int], bool])
    """Export the result for a given analyzer ID and result ID
    
    :func:`shapeflow.db.History.export_result`
    """
    clean = Endpoint(Callable[[], None])
    """Clean the database
    
    :func:`shapeflow.db.History.clean`
    """
    forget = Endpoint(Callable[[], None])
    """Remove all entries from the database
    
    :func:`shapeflow.db.History.forget`
    """


class _FilesystemDispatcher(Dispatcher):
    """Dispatches ``/api/fs/<endpoint>``
    """
    select_video = Endpoint(Callable[[], Optional[str]])
    """Open a dialog to select a video file
    
    :func:`shapeflow.main._Filesystem.select_video`
    """
    select_design = Endpoint(Callable[[], Optional[str]])
    """Open a dialog to select a design file
    
    :func:`shapeflow.main._Filesystem.select_design`
    """

    check_video = Endpoint(Callable[[str], bool])
    """Check whether the given video file is valid
    
    :func:`shapeflow.main._Filesystem.check_video`
    """
    check_design = Endpoint(Callable[[str], bool])
    """Check whether the given video file is valid
    
    :func:`shapeflow.main._Filesystem.check_design`
    """

    open_root = Endpoint(Callable[[], None])
    """Open the application's root directory in a file explorer window
    
    :func:`shapeflow.main._Filesystem.open_root`
    """


class _CacheDispatcher(Dispatcher):
    """Dispatches ``/api/cache/<endpoint>``
    """
    clear = Endpoint(Callable[[], None])
    """Clear the cache
    
    :func:`shapeflow.main._cache.clear`
    """
    size = Endpoint(Callable[[], str])
    """Get the size of the cache on disk
    
    :func:`shapeflow.main._Cache.size`
    """


class ApiDispatcher(Dispatcher):
    """Invoked by ``Flask`` server for requests to ``/api/``
    """

    ping = Endpoint(Callable[[], bool])
    """Ping the backend
    
    :func:`shapeflow.main._Main.ping`
    """
    map = Endpoint(Callable[[], Dict[str, List[str]]])
    """Get API map
    
    :func:`shapeflow.main._Main.map`
    """
    schemas = Endpoint(Callable[[], dict])
    """Get all schemas
    
    :func:`shapeflow.main._Main.schemas`
    """
    normalize_config = Endpoint(Callable[[dict], dict])  # todo: deprecate this
    """Normalize the given config to the current version of the application
    
    :func:`shapeflow.main._Main.normalize_config`
    """
    get_settings = Endpoint(Callable[[], dict])
    """Get the application settings
    
    :func:`shapeflow.main._Main.get_settings`
    """
    set_settings = Endpoint(Callable[[dict], dict])
    """Set the application settings
    
    :func:`shapeflow.main._Main.set_settings`
    """
    events = Endpoint(Callable[[], EventStreamer], stream_json)
    """Open an event stream
    
    :func:`shapeflow.main._Main.events`
    """
    stop_events = Endpoint(Callable[[], None])
    """Stop the event stream
    
    :func:`shapeflow.main._Main.stop_events`
    """
    log = Endpoint(Callable[[], PlainFileStreamer], stream_plain)
    """Open a log stream
    
    :func:`shapeflow.main._Main.log`
    """
    stop_log = Endpoint(Callable[[], None])
    """Stop the log stream
    
    :func:`shapeflow.main._Main.stop_log`
    """
    unload = Endpoint(Callable[[], bool])
    """Unload the application. In order to support page reloading, the backend 
    will wait for some time and quit if no further requests come in.
    
    :func:`shapeflow.main._Main.unload`
    """
    quit = Endpoint(Callable[[], bool])
    """Quit without waiting for incoming requests
    
    :func:`shapeflow.main._Main.quit`
    """
    restart = Endpoint(Callable[[], bool])
    """Restart the server
    
    :func:`shapeflow.main._Main.restart`
    """
    pid_hash = Endpoint(Callable[[], str])
    """Get the hashed process ID. Used to confirm server restart without
    exposing the actual PID.
    
    :func:`shapeflow.main._Main.pid_hash`
    """

    fs = _FilesystemDispatcher()
    """Nested :class:`~shapeflow.api._FilesystemDispatcher`
    """
    db = _DatabaseDispatcher()
    """Nested :class:`~shapeflow.api._DatabaseDispatcher`
    """
    va = _VideoAnalyzerManagerDispatcher()
    """Nested :class:`~shapeflow.api._VideoAnalyzerManagerDispatcher`
    """
    cache = _CacheDispatcher()
    """Nested :class:`~shapeflow.api._CacheDispatcher`
    """


api = ApiDispatcher()
"""Global :class:`~shapeflow.api.ApiDispatcher` instance. 
Endpoints should be exposed against this object. 
API calls should be dispatched from this object.

URLs match object structure: ``"/api/va/abc123/analyze"`` is equivalent to
``api.va.abc123.analyze``.
"""
