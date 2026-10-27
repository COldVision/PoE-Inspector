import sys
from poe_inspector import index
index.build(sys.argv[1] if len(sys.argv) > 1 else r"D:\SteamLibrary\steamapps\common\Path of Exile 2", "poe2.db")
