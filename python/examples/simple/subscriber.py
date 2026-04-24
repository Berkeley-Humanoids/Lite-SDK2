import argparse

from lite_sdk2 import ChannelSubscriber

from user_data import UserData


def main() -> None:
    parser = argparse.ArgumentParser(description="Subscribe to sample DDS user data.")
    parser.add_argument("nic")
    args = parser.parse_args()

    sub = ChannelSubscriber("topic", UserData, network_interface=args.nic)
    sub.initialize()

    while True:
        msg = sub.read(timeout=5.0)
        if msg is None:
            print("No data received.")
            break
        print("received", msg)

    sub.close()


if __name__ == "__main__":
    main()
