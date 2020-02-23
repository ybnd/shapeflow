from isimple.core.config import VideoAnalyzerConfig
from isimple.video import VideoAnalyzer
from isimple.gui import VideoAnalyzerGui

from og.gui import FileSelectWindow


def analysis(config = None):
    # Initialize backend & frontend
    backend = VideoAnalyzer(config)
    VideoAnalyzerGui(backend)

    # Open setup window to gather arguments if necessary
    if not backend.can_launch():
        backend.configure()  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)

    # Once we have all arguments, launch the backend
    backend.launch()

    with backend.caching():
        # Open alignment window
        backend.align()  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)
        for i, _ in enumerate(backend.masks):
            # Open color picker windows for each mask
            backend.pick(i)  # todo: make sure that this waits on the window (was implemented in ScriptWindow iirc?)

        # Perform the video analysis
        backend.analyze()

        # Save the results
        backend.save()


if __name__ == '__main__':
    analysis(
        VideoAnalyzerConfig(**{
            'video_path': '/home/ybnd/projects/200210 - isimple/shuttle.mp4',
            'design_path': '/home/ybnd/projects/200210 - isimple/shuttle.svg',
            'dt': 5,
            'height': 153e-3,
            'video': {'do_cache': True}
        })
    )

