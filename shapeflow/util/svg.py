import OnionSVG


def check_svg(path) -> bool:
    return OnionSVG.check_svg(path)


def peel(path, dpi, dir) -> None:
    OnionSVG.OnionSVG(path, dpi=dpi).peel(
        'all', to=dir
    )
    print("\n")
