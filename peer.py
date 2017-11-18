import socket
from threading import Thread
from typing import Tuple

import stun


def main() -> None:
    my_ip, my_port = whats_my_external_ip()
    print('Public connection info:', my_ip, my_port)

    #listener_thread = Thread(target=start_listener)
    #listener_thread.start()
    #print('Listener started')

    line = input('Enter peer connection info: ')
    peer_ip, peer_port = parse_conn_info(line)
    print(f'Connecting to: {peer_ip}:{peer_port}')


    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_sock.bind(('0.0.0.0', my_port))
    client_sock.sendto(b'hey there!', (peer_ip, peer_port))
    data, addr = client_sock.recvfrom(4096)
    print('Received: ', data, addr)
    client_sock.close()


def parse_conn_info(ln: str) -> Tuple[str, int]:
    parts = ln.strip().split()
    return (parts[0], int(parts[1]))


def start_listener() -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind(('0.0.0.0', 0))
    data, addr = server_sock.recvfrom(4096)
    server_sock.close()


def whats_my_external_ip() -> Tuple[str, int]:
    stun_port = 19302
    stun_ip = resolve_hostname('stun.l.google.com', stun_port)
    _, ip, port = stun.get_ip_info(stun_host=stun_ip, stun_port=stun_port)
    return (ip, port)


def resolve_hostname(hostname: str, port: int=None) -> str:
    """DNS resolve hostname.

    Args:
        hostname: hostname to get IP address for.
        port: optional. Used to hint what DNS entry we're looking
            for.

    Returns:
        IP address used to connect to the specified hostname.
    """
    try:
        res = socket.getaddrinfo(hostname, port, socket.AF_INET)
        if len(res) == 0:
            return None

        _, _, _, _, socket_addr = res[0]
        ip_addr, _ = socket_addr

        return ip_addr
    except socket.gaierror:
        return None


main()
