from typing import Dict, Optional, List, Callable, Tuple, Type
import numpy as np

from isimple.core import ImmutableRegistry, Endpoint
from isimple.core.interface import FilterConfig
from isimple.maths.colors import HsvColor


class BackendRegistry(ImmutableRegistry):
    can_launch = Endpoint(Callable[[], bool])
    can_run = Endpoint(Callable[[], bool])
    confirm_run = Endpoint(Callable[[], None])
    launch = Endpoint(Callable[[], bool])
    analyze = Endpoint(Callable[[], bool])
    get_config = Endpoint(Callable[[], dict])
    set_config = Endpoint(Callable[[dict], bool])
    get_relative_roi = Endpoint(Callable[[], dict])
    get_name = Endpoint(Callable[[], str])
    get_total_frames = Endpoint(Callable[[], int])
    seek = Endpoint(Callable[[float], float])
    get_seek_position = Endpoint(Callable[[], float])
    get_raw_frame = Endpoint(Callable[[Optional[int]], np.ndarray])
    set_transform_implementation = Endpoint(Callable[[str], str])
    transform = Endpoint(Callable[[np.ndarray], np.ndarray])
    estimate_transform = Endpoint(Callable[[dict], bool])
    get_coordinates = Endpoint(Callable[[], Optional[list]])
    get_mask_name = Endpoint(Callable[[int], str])
    get_mask_names = Endpoint(Callable[[], tuple])
    set_filter_implementation = Endpoint(Callable[[str], str])
    set_filter_parameters = Endpoint(Callable[[FilterConfig, HsvColor], FilterConfig])  # todo: frontend shouldn't have to care about FilterConfig!
    get_filter_parameters = Endpoint(Callable[[], FilterConfig])
    get_filter_mean_color = Endpoint(Callable[[], HsvColor])
    get_overlay = Endpoint(Callable[[], np.ndarray])
    get_overlay_png = Endpoint(Callable[[], bytes])
    get_frame = Endpoint(Callable[[Optional[int]], np.ndarray])
    get_masked_frame = Endpoint(Callable[[int], np.ndarray])
    set_filter_click = Endpoint(Callable[[float, float], dict])
    filter = Endpoint(Callable[[np.ndarray], np.ndarray])
    mask = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_filtered_frame = Endpoint(Callable[[Optional[int]], np.ndarray])
    get_filtered_masked_frame = Endpoint(Callable[[int], np.ndarray])
    overlay_frame = Endpoint(Callable[[np.ndarray], np.ndarray])
    get_overlaid_frame = Endpoint(Callable[[int], np.ndarray])
    get_inverse_transformed_overlay = Endpoint(Callable[[], np.ndarray])
    get_inverse_overlaid_frame = Endpoint(Callable[[Optional[int]], np.ndarray])
    get_state_frame = Endpoint(Callable[[Optional[int], Optional[int]], np.ndarray])
    get_colors = Endpoint(Callable[[], List[Tuple[HsvColor,...]]])
    get_time = Endpoint(Callable[[int], float])
    get_fps = Endpoint(Callable[[], float])
    get_h = Endpoint(Callable[[], float])
    get_dpi = Endpoint(Callable[[], float])


class HistoryRegistry(ImmutableRegistry):
    pass


class GuiRegistry(ImmutableRegistry):  # todo: move to isimple.og, should only be used by LegacyVideoAnalyzer(VideoAnalyzer)
    open_setupwindow = Endpoint(Callable[[], None])
    open_transformwindow = Endpoint(Callable[[], None])
    open_filterwindow = Endpoint(Callable[[int], None])
    update_filterwindow = Endpoint(Callable[[int], None])
    open_progresswindow = Endpoint(Callable[[], None])
    update_progresswindow = Endpoint(Callable[[float, list, np.ndarray, np.ndarray], None])
