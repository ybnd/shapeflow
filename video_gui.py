from isimple.core.config import VideoAnalyzerConfig, DesignFileHandlerConfig
from isimple.video import VideoAnalyzer
from isimple.gui import VideoAnalyzerGui


def analysis(config=None):
    # Initialize backend & frontend
    backend = VideoAnalyzer(config)
    VideoAnalyzerGui(backend)

    # Open setup window to gather arguments if necessary
    if not backend._can_launch():
        backend.configure()  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)

    # Once we have all arguments, launch the backend
    backend.launch()

    with backend.caching():
        # Open alignment window
        backend.align()  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)
        for i, _ in enumerate(backend.masks):
            # Open color picker windows for each mask
            backend.pick(i)  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)

        # Perform the video analysis & save the results
        backend.analyze()


if __name__ == '__main__':
    analysis(
        VideoAnalyzerConfig(
            design = DesignFileHandlerConfig(keep_renders=True)
        )
    )
