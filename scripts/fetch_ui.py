# Fetch the compiled ui for $name v$version from
url = "$url/releases/download/$version/dist-$version.tar.gz"

from urllib.request import urlopen
from tarfile import open

open(fileobj=urlopen(url), mode='r|gz').extractall(path='$name/ui/')
