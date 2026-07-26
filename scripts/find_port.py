import os
import socket


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


start = int(os.getenv("PORT_SCAN_START", "8100"))
end = int(os.getenv("PORT_SCAN_END", "8999"))
preferred = os.getenv("PORT", "").strip()
if preferred and port_available(int(preferred)):
    print(preferred)
else:
    for candidate in range(start, end + 1):
        if port_available(candidate):
            print(candidate)
            break
    else:
        raise SystemExit(f"No free port found between {start} and {end}")

