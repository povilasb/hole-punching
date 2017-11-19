import socket as blocking_socket
from threading import Thread
from typing import Tuple

import curio
from curio import socket

import stun


async def start_peer(bind_port: int) -> None:
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_sock.bind(('0.0.0.0', bind_port))
    recv_task = await curio.spawn(recv_data, client_sock)

    queue = curio.UniversalQueue()
    stdin_thread = Thread(target=read_peer_info, args=(queue,))
    stdin_thread.start()

    peer_ip, peer_port = await queue.get()
    print(f'Connecting to: {peer_ip}:{peer_port}')

    await client_sock.sendto(b'hey there!', (peer_ip, peer_port))

    stdin_thread.join()
    await recv_task.join()


def read_peer_info(queue: curio.UniversalQueue) -> None:
    line = input('Enter peer connection info: ')
    queue.put(parse_conn_info(line))


async def recv_data(sock: socket.socket) -> None:
    while True:
        data, addr = await sock.recvfrom(4096)
        print('Received: ', data, addr)


def main() -> None:
    my_ip, my_port = curio.run(whats_my_external_ip)
    print('Public connection info:', my_ip, my_port)
    curio.run(start_peer, my_port)


def parse_conn_info(ln: str) -> Tuple[str, int]:
    parts = ln.strip().split()
    return (parts[0], int(parts[1]))


async def whats_my_external_ip() -> Tuple[str, int]:
    stun_port = 19302
    stun_ip = resolve_hostname('stun.l.google.com', stun_port)
    _, ip, port = await stun.get_ip_info(stun_host=stun_ip, stun_port=stun_port)
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
        res = blocking_socket.getaddrinfo(
            hostname, port, blocking_socket.AF_INET)
        if len(res) == 0:
            return None

        _, _, _, _, socket_addr = res[0]
        ip_addr, _ = socket_addr

        return ip_addr
    except socket.gaierror:
        return None


if __name__ == '__main__':
    main()
