from typing import Callable, Optional, List, Callable
import numpy as np

from isimple.core.common import ImmutableRegistry, Endpoint

class BackendEndpoints(ImmutableRegistry):  # todo: confusing naming
    set_video_path = Endpoint(Callable[[str], None])
    set_design_path = Endpoint(Callable[[str], None])
    configure = Endpoint(Callable[[dict], None])
    get_raw_frame = Endpoint(Callable[[int], Optional[np.ndarray]])
    estimate_transform = Endpoint(Callable[[List], None])
    set_filter_from_color = Endpoint(Callable[[List], None])
    get_transformed_frame = Endpoint(Callable[[int], np.ndarray])
    get_transformed_overlaid_frame = Endpoint(Callable[[int], np.ndarray])


class GuiEndpoints(ImmutableRegistry):
    open_setupwindow = Endpoint(Callable[[Callable], None])
    open_transformwindow = Endpoint(Callable[[Callable], None])
    open_filterwindow = Endpoint(Callable[[Callable,Callable], None])
    open_progresswindow = Endpoint(Callable[[], None])
    update_progresswindow = Endpoint(Callable[[], None])
