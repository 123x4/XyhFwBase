"""Print the Lina H6 diagnostic firmware's USB HID log on Windows."""

import argparse
import sys
import time

VENDOR_ID = 0x1A81
PRODUCT_ID = 0x2071
USAGE_PAGE = 0xFF01
USAGE = 0x01
REPORT_SIZE = 64


def log_lines(device):
    pending = bytearray()
    while True:
        report = bytes(device.read(REPORT_SIZE + 1, 1000))
        if len(report) == REPORT_SIZE + 1 and report[0] == 0:
            report = report[1:]
        pending.extend(report.rstrip(b"\x00"))

        lines = pending.split(b"\n")
        pending = lines.pop()
        for line in lines:
            if line.startswith(b"[I]"):
                yield line.rstrip(b"\r").decode("ascii", errors="replace")
        if len(pending) > 1024:
            pending.clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Exit after the first H6 result.")
    args = parser.parse_args()

    try:
        import hid
    except ImportError:
        print("Install the USB HID package with: py -m pip install hidapi", file=sys.stderr)
        return 1

    print("Waiting for Lina USB HID 1A81:2071 (Ctrl+C to stop)...", file=sys.stderr)
    try:
        while True:
            matches = [
                item for item in hid.enumerate(VENDOR_ID, PRODUCT_ID)
                if item.get("usage_page") == USAGE_PAGE and item.get("usage") == USAGE
            ]
            if len(matches) > 1:
                print("Connect only the Lina board you want to test.", file=sys.stderr)
                return 1
            if matches:
                break
            time.sleep(0.5)

        device = hid.device()
        try:
            device.open_path(matches[0]["path"])
            print("HID connected. Listening for diagnostic logs.", file=sys.stderr)
            for line in log_lines(device):
                print(line, flush=True)
                if args.once and "H6_CAL " in line:
                    return 0
        finally:
            device.close()
    except KeyboardInterrupt:
        return 0
    except OSError as error:
        print(f"USB HID error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
