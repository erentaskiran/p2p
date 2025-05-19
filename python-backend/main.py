from utils.P2PNode import P2PNode
import time
import os

if __name__ == "__main__":
    node = P2PNode()
    if not os.path.exists("publicFiles"):
        os.mkdir("publicFiles")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping P2P node...")
        node.stop()