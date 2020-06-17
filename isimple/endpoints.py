from typing import Dict, Optional, List, Callable, Tuple, Type
import numpy as np

from isimple.core import ImmutableRegistry, Endpoint, stream_image, stream_json
from isimple.core.interface import FilterConfig
from isimple.maths.colors import HsvColor


class BackendRegistry(ImmutableRegistry):
    status = Endpoint(Callable[[], dict], stream_json)
    state_transition = Endpoint(Callable[[bool], int])
    can_launch = Endpoint(Callable[[], bool])
    can_analyze = Endpoint(Callable[[], bool])
    launch = Endpoint(Callable[[], bool])
    commit = Endpoint(Callable[[], bool])
    cache = Endpoint(Callable[[], bool])
    analyze = Endpoint(Callable[[], bool])
    cancel = Endpoint(Callable[[], None])
    is_caching = Endpoint(Callable[[], bool])
    cancel_caching = Endpoint(Callable[[], None])
    get_value = Endpoint(Callable[[], dict], stream_json)
    get_state = Endpoint(Callable[[], dict], stream_json)
    get_config = Endpoint(Callable[[], dict], stream_json)
    set_config = Endpoint(Callable[[dict], dict])
    get_results = Endpoint(Callable[[], dict])
    get_relative_roi = Endpoint(Callable[[], dict])
    undo_config = Endpoint(Callable[[], dict])
    redo_config = Endpoint(Callable[[], dict])
    get_name = Endpoint(Callable[[], str])
    seek = Endpoint(Callable[[float], float])
    get_seek_position = Endpoint(Callable[[], float])
    get_raw_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    set_transform_implementation = Endpoint(Callable[[str], str])
    transform = Endpoint(Callable[[np.ndarray], np.ndarray])
    estimate_transform = Endpoint(Callable[[dict], Optional[dict]])
    clear_roi = Endpoint(Callable[[], None])
    get_coordinates = Endpoint(Callable[[], Optional[list]])
    get_mask_name = Endpoint(Callable[[int], str])
    get_mask_names = Endpoint(Callable[[], tuple])
    get_filter_mean_color = Endpoint(Callable[[], HsvColor])
    get_overlay_png = Endpoint(Callable[[], bytes])
    get_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_masked_frame = Endpoint(Callable[[int], np.ndarray], stream_image)
    set_filter_click = Endpoint(Callable[[float, float], dict])
    filter = Endpoint(Callable[[np.ndarray], np.ndarray])
    mask = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_filtered_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_filtered_masked_frame = Endpoint(Callable[[int], np.ndarray], stream_image)
    overlay_frame = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_overlaid_frame = Endpoint(Callable[[int], np.ndarray], stream_image)
    get_inverse_transformed_overlay = Endpoint(Callable[[], np.ndarray], stream_image)
    get_inverse_overlaid_frame = Endpoint(Callable[[Optional[int]], np.ndarray], stream_image)
    get_state_frame = Endpoint(Callable[[Optional[int], Optional[int]], np.ndarray], stream_image)
    get_colors = Endpoint(Callable[[], Dict[str, Tuple[str, ...]]])
    get_time = Endpoint(Callable[[int], float])
    get_total_time = Endpoint(Callable[[], float])
    get_fps = Endpoint(Callable[[], float])
    get_h = Endpoint(Callable[[], float])
    get_dpi = Endpoint(Callable[[], float])
    get_mask_rects = Endpoint(Callable[[], Dict[str, np.ndarray]])
