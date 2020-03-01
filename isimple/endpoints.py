from typing import Dict, Optional, List, Callable, Tuple, Type
import numpy as np

from isimple.core.common import ImmutableRegistry, Endpoint
from isimple.core.config import Color, FilterConfig

class BackendEndpoints(ImmutableRegistry):  # todo: confusing naming
    get_config = Endpoint(Callable[[], dict])
    set_config = Endpoint(Callable[[dict], None])
    get_name = Endpoint(Callable[[], str])
    get_total_frames = Endpoint(Callable[[], int])
    get_raw_frame = Endpoint(Callable[[int], Optional[np.ndarray]])
    set_transform_implementation = Endpoint(Callable[[str], str])
    transform = Endpoint(Callable[[np.ndarray], np.ndarray])
    estimate_transform = Endpoint(Callable[[list], None])
    get_coordinates = Endpoint(Callable[[], Optional[list]])
    get_mask_name = Endpoint(Callable[[int], str])
    get_mask_names = Endpoint(Callable[[], tuple])
    set_filter_implementation = Endpoint(Callable[[str], str])
    set_filter_parameters = Endpoint(Callable[[FilterConfig, Tuple[float,float,float]], FilterConfig])
    get_filter_parameters = Endpoint(Callable[[], FilterConfig])
    get_filter_mean_color = Endpoint(Callable[[], Tuple[float,float,float]])
    get_overlay = Endpoint(Callable[[], np.ndarray])
    get_frame = Endpoint(Callable[[int], np.ndarray])
    get_masked_frame = Endpoint(Callable[[int], np.ndarray])
    filter = Endpoint(Callable[[np.ndarray], np.ndarray])
    mask = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_filtered_frame = Endpoint(Callable[[int], np.ndarray])
    get_filtered_masked_frame = Endpoint(Callable[[int], np.ndarray])
    overlay_frame = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_overlaid_frame = Endpoint(Callable[[int], np.ndarray])
    get_inverse_transformed_overlay = Endpoint(Callable[[], np.ndarray])
    get_colors = Endpoint(Callable[[], List[Tuple[Tuple[float,float,float],...]]])
    get_time = Endpoint(Callable[[int], float])
    get_fps = Endpoint(Callable[[], float])
    get_h = Endpoint(Callable[[], float])
    get_dpi = Endpoint(Callable[[], float])


class GuiEndpoints(ImmutableRegistry):
    open_setupwindow = Endpoint(Callable[[], None])
    open_transformwindow = Endpoint(Callable[[], None])
    open_filterwindow = Endpoint(Callable[[int], None])
    update_filterwindow = Endpoint(Callable[[int], None])
    open_progresswindow = Endpoint(Callable[[], None])
    update_progresswindow = Endpoint(Callable[[float, list, np.ndarray, np.ndarray], None])
