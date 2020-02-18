from typing import Dict, Optional, List, Callable
import numpy as np

from isimple.core.common import ImmutableRegistry, Endpoint

class BackendEndpoints(ImmutableRegistry):  # todo: confusing naming
    set_video_path = Endpoint(Callable[[str], None])
    set_design_path = Endpoint(Callable[[str], None])
    configure = Endpoint(Callable[[dict], None])
    get_raw_frame = Endpoint(Callable[[int], Optional[np.ndarray]])
    set_transform_implementation = Endpoint(Callable[[str], str])
    estimate_transform = Endpoint(Callable[[list], None])
    set_filter_implementation = Endpoint(Callable[[str], str])
    set_filter_parameters = Endpoint(Callable[[list, dict], dict])
    get_filter_mean_color = Endpoint(Callable[[], list])
    get_frame = Endpoint(Callable[[int], np.ndarray])
    get_masked_frame = Endpoint(Callable[[int], np.ndarray])
    get_filtered_frame = Endpoint(Callable[[int], np.ndarray])
    get_filtered_masked_frame = Endpoint(Callable[[int], np.ndarray])
    get_overlaid_frame = Endpoint(Callable[[int], np.ndarray])
    get_inverse_transformed_overlay = Endpoint(Callable[[int], np.ndarray])


class GuiEndpoints(ImmutableRegistry):
    open_setupwindow = Endpoint(Callable[[], None])
    open_transformwindow = Endpoint(Callable[[], None])
    open_filterwindow = Endpoint(Callable[[int], None])
    update_filterwindow = Endpoint(Callable[[int], None])
    open_progresswindow = Endpoint(Callable[[], None])
    update_progresswindow = Endpoint(Callable[[list, np.ndarray], None])

