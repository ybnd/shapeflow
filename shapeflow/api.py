from typing import Dict, Optional, List, Callable, Tuple, Type, Any
import numpy as np
import shortuuid

from shapeflow.core import Dispatcher, Endpoint, stream_image, stream_json
from shapeflow.util.meta import bind
from shapeflow.maths.colors import HsvColor

class VideoAnalyzerDispatcher(Dispatcher):  # todo: there's a bunch of deprecated stuff here
    status = Endpoint(Callable[[], dict], stream_json)
    state_transition = Endpoint(Callable[[bool], int])
    can_launch = Endpoint(Callable[[], bool])
    can_analyze = Endpoint(Callable[[], bool])
    launch = Endpoint(Callable[[], bool])
    commit = Endpoint(Callable[[], bool])
    cache = Endpoint(Callable[[], bool])  # todo: deprecated
    analyze = Endpoint(Callable[[], bool])
    cancel = Endpoint(Callable[[], None])
    is_caching = Endpoint(Callable[[], bool])  # todo: deprecated
    cancel_caching = Endpoint(Callable[[], None])  # todo: deprecated
    get_value = Endpoint(Callable[[], dict], stream_json)  # todo: what's this?
    get_state = Endpoint(Callable[[], dict], stream_json)  # todo: what's this?
    get_config = Endpoint(Callable[[], dict], stream_json)
    set_config = Endpoint(Callable[[dict, bool], dict])
    get_results = Endpoint(Callable[[], dict])
    undo_config = Endpoint(Callable[[str], dict])
    redo_config = Endpoint(Callable[[str], dict])
    get_name = Endpoint(Callable[[], str])
    estimate_transform = Endpoint(Callable[[dict], Optional[dict]])
    turn_cw = Endpoint(Callable[[], None])
    turn_ccw = Endpoint(Callable[[], None])
    flip_h = Endpoint(Callable[[], None])
    flip_v = Endpoint(Callable[[], None])
    clear_roi = Endpoint(Callable[[], None])
    get_overlay_png = Endpoint(Callable[[], bytes])
    get_mask_name = Endpoint(Callable[[int], str])
    get_mask_names = Endpoint(Callable[[], tuple])
    get_filter_mean_color = Endpoint(Callable[[], HsvColor])
    get_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_masked_frame = Endpoint(Callable[[int], np.ndarray], stream_image)
    set_filter_click = Endpoint(Callable[[float, float], None])
    filter = Endpoint(Callable[[np.ndarray], np.ndarray])  # todo: deprecated
    mask = Endpoint(Callable[[np.ndarray], np.ndarray])    # todo: deprecated
    get_filtered_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_filtered_masked_frame = Endpoint(Callable[[int], np.ndarray], stream_image)
    overlay_frame = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_overlaid_frame = Endpoint(Callable[[int], np.ndarray], stream_image)
    get_inverse_transformed_overlay = Endpoint(Callable[[], np.ndarray], stream_image)
    get_inverse_overlaid_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_state_frame = Endpoint(Callable[[Optional[int], Optional[int]], np.ndarray], stream_image)
    get_colors = Endpoint(Callable[[], Tuple[str, ...]])
    get_db_id = Endpoint(Callable[[], int])
    clear_filters = Endpoint(Callable[[], bool])
    seek = Endpoint(Callable[[float], float])

    get_relative_roi = Endpoint(Callable[[], dict])
    get_coordinates = Endpoint(Callable[[], Optional[list]])

    get_time = Endpoint(Callable[[int], float])
    get_total_time = Endpoint(Callable[[], float])  # todo: maybe bundle these }
    get_fps = Endpoint(Callable[[], float])  # todo: maybe bundle these }
    get_raw_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_seek_position = Endpoint(Callable[[], float])


class VideoAnalyzerManagerDispatcher(Dispatcher):
    """ Dispatches requests to video analyzer instances. """
    # todo: this one will be a bit special since it also dispatches to id's
    # todo: ids should be a bit shorter for more readable URLs
    init = Endpoint(Callable[[], str])

    __id__ = VideoAnalyzerDispatcher() # todo: so dispatch <id> to a specific one somehow?

    start = Endpoint(Callable[[], None])  # todo: these should respond with state?
    stop = Endpoint(Callable[[], None])
    cancel = Endpoint(Callable[[], None])

    __analyzers__: Dict[str, object] = {}  # todo: analyzer manager should register analyzers with api.va on init

    def _update_endpoint(self, endpoint: Endpoint) -> None:
        self._address_space.update({
            endpoint.name: endpoint.method
        })
        try:
            self._update(self)
        except AttributeError:
            pass

    def _update_dispatcher(self, dispatcher: 'Dispatcher') -> None:
        self._address_space.update({
            "/".join([dispatcher.name, address]): method
            for address, method in dispatcher.address_space.items()
            if method is not None and "__" not in address
        })
        self._address_space.update({
            "/".join([id, address]): bind(instance, method)
            for id, instance in self.__analyzers__.items()
            for address, method in self.__id__.address_space.items()
            if method is not None and "__" not in address
        })
        try:
            self._update(self)
        except AttributeError:
            pass

    def add(self, analyzer: object) -> str:
        LENGTH = 4  # the alphabet used in shortuuid is 57 chars long.
                    # 4 chars can define ~10M unique strings,
                    # which should be more than enough
        id = shortuuid.ShortUUID().random(length=LENGTH)

        # ensure that there's no collisions
        while id in self.__analyzers__.keys():
            id = shortuuid.ShortUUID().random(length=LENGTH)

        self.__analyzers__[id] = analyzer
        self._address_space.update({
            "/".join([id, address]): bind(analyzer, method)
            for address, method in self.__id__.address_space.items()
            if method is not None
        })
        self._update(self)
        return id

    def remove(self, id: str):
        del self.__analyzers__[id]
        for k,v in self._address_space:  # todo: this is a bit lame
            if id in k:
                del self._address_space[k]
        self._update(self)


class DatabaseDispatcher(Dispatcher):
    """ Dispatches requests to a History instance. """
    get_recent_paths = Endpoint(Callable[[], Dict[str, List[str]]])

    get_result_list = Endpoint(Callable[[int], dict])
    get_result = Endpoint(Callable[[int, int], dict])
    export_result = Endpoint(Callable[[int, int], bool])

    clean = Endpoint(Callable[[], None])
    forget = Endpoint(Callable[[], None])


class FilesystemDispatcher(Dispatcher):
    select_video = Endpoint(Callable[[], str])
    select_design = Endpoint(Callable[[], str])

    check_video = Endpoint(Callable[[str], bool])
    check_design = Endpoint(Callable[[str], bool])

    open_root = Endpoint(Callable[[], None])


class ApiDispatcher(Dispatcher):
    """ Dispatches API requests. """
    ping = Endpoint(Callable[[], bool])

    map = Endpoint(Callable[[], dict])
    schemas = Endpoint(Callable[[], dict])

    get_settings = Endpoint(Callable[[], dict])
    set_settings = Endpoint(Callable[[dict], dict])

    unload = Endpoint(Callable[[], bool])
    quit = Endpoint(Callable[[], bool])
    restart = Endpoint(Callable[[], bool])

    fs = FilesystemDispatcher()
    db = DatabaseDispatcher()
    va = VideoAnalyzerManagerDispatcher()


# Global
api = ApiDispatcher(True)
