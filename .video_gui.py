from isimple.config import DesignFileHandlerConfig, VideoAnalyzerConfig
from isimple.video import VideoAnalyzer
from isimple.history import History
import asyncio
from og.gui import VideoAnalyzerGui


def analysis(config=None):
    # Initialize backend & frontend
    h = History()
    va = VideoAnalyzer(config)
    vm = h.add_analysis(va)

    VideoAnalyzerGui(va)

    # Open setup window to gather arguments if necessary
    if not va.can_launch():
        va.configure()  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)

    # Once we have all arguments, launch the backend
    va.launch()

    with va.caching():
        # Open alignment window
        va.align()  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)
        for i, _ in enumerate(va.masks):
            # Open color picker windows for each mask
            va.pick(i)  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)

        # Perform the video analysis & save the results
        va.analyze()

    vm.store()


if __name__ == '__main__':
    analysis(
        VideoAnalyzerConfig(
            design = DesignFileHandlerConfig(keep_renders=True)
        )
    )
