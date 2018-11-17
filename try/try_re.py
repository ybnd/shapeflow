import re
import random, string

def randomword(length):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for i in range(length))


names = [f"Layer {i} - {randomword(16)}" for i in range(100)]
random.shuffle(names)

pt = re.compile('(\d+)[?\-=_#/\\\ ]+(\w+)')

out = {}

indexmatch = []

for name in names:
    indexmatch.append(
        pt.search(name)
    )

    out.update(
        {int(pt.search(name).groups()[0]): pt.search(name).groups()[1]}
    )

