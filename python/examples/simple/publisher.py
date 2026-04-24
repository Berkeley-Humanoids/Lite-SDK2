import argparse
import time

from lite_sdk2 import ChannelPublisher
from loop_rate_limiters import RateLimiter

from user_data import UserData


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish sample DDS user data.")
    parser.add_argument("nic")
    args = parser.parse_args()

    pub = ChannelPublisher("topic", UserData, network_interface=args.nic)
    pub.initialize()
    if not pub.wait_for_reader(timeout=2.0):
        print("No subscriber after 2s, publishing anyway.")

    rate = RateLimiter(100)
    for _ in range(30):
        msg = UserData(string_data="Hello world", float_data=time.time())
        pub.write(msg)
        print("published", msg)
        rate.sleep()

    pub.close()


if __name__ == "__main__":
    main()
