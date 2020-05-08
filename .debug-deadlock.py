import time
import json
import requests

from isimple.main import Main, Thread


if __name__ == '__main__':
    def _main():
        main = Main()
        main.serve(False)
        main.cleanup()  # todo: doesn't clean up :(

    Thread(target=_main, daemon=True).start()

    config = {
        "video_path": "/home/ybnd/projects/200210 - isimple/data/shuttle.mp4",
        "design_path": "/home/ybnd/projects/200210 - isimple/data/shuttle.svg",
        "features": ["Volume_uL"]
    }

    time.sleep(2)

    response = requests.post("http://localhost:7951/api/init")
    id1 = response.content.decode('utf-8').strip().replace('"', '')
    requests.post(f"http://localhost:7951/api/{id1}/call/set_config?config={json.dumps(config)}")
    requests.post(f"http://localhost:7951/api/{id1}/launch")
    time.sleep(1)
    response = requests.post("http://localhost:7951/api/init")
    id2 = response.content.decode('utf-8').strip().replace('"', '')
    requests.post(f"http://localhost:7951/api/{id2}/call/set_config?config={json.dumps(config)}")
    requests.post(f"http://localhost:7951/api/{id2}/launch")
    time.sleep(1)
