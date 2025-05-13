from P2PNode import P2PNode
import time

if __name__ == "__main__":

    node = P2PNode()
    
    directory_path = "test"
    
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping P2P node...")
        node.stop()