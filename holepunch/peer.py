from threading import Thread
from typing import Tuple

import curio
from curio import socket
import click

from . import stun


class UdpPeer:
    def __init__(self, bind_port: int) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(('0.0.0.0', bind_port))

    async def start(self) -> None:
        recv_task = await curio.spawn(self.recv_data)

        queue = curio.UniversalQueue()
        stdin_thread = Thread(target=read_peer_info, args=(queue,))
        stdin_thread.start()

        peer_ip, peer_port = await queue.get()
        print(f'Connecting to: {peer_ip}:{peer_port}')

        await self._sock.sendto(b'hey there!', (peer_ip, peer_port))

        stdin_thread.join()
        await recv_task.join()

    async def recv_data(self) -> None:
        while True:
            data, addr = await self._sock.recvfrom(4096)
            print('Received [{}]: '.format(addr), data)


class TcpPeer:
    def __init__(self, bind_port: int) -> None:
        self._bind_port = bind_port
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._sock.bind(('0.0.0.0', bind_port))

    async def start(self) -> None:
        queue = curio.UniversalQueue()
        stdin_thread = Thread(target=read_peer_info, args=(queue,))
        stdin_thread.start()

        peer_ip, peer_port = await queue.get()
        print(f'Connecting to: {peer_ip}:{peer_port}')

        await self._sock.connect((peer_ip, peer_port))
        # We must start reading only when connected, otherwise Linux returns
        # socket error #107
        recv_task = await curio.spawn(self.recv_data)

        print('Connected')
        await self._sock.send(b'hey there!')
        print('Sent msg')

        stdin_thread.join()
        await recv_task.join()

    async def recv_data(self) -> None:
        while True:
            data = await self._sock.recv(4096)
            if len(data) == 0:
                break
            print('Received: ', data)


def read_peer_info(queue: curio.UniversalQueue) -> None:
    line = input('Enter peer connection info: ')
    queue.put(parse_conn_info(line))


@click.command()
@click.option('--protocol', '--proto', 'protocol', default='udp', type=str,
              help='Use either TCP or UDP to communicate with STUN server.',)
def main(protocol: str) -> None:
    my_ip, my_port = curio.run(whats_my_external_ip, protocol)
    print('Public connection info:', my_ip, my_port)

    peer = None
    if protocol == 'udp':
        peer = UdpPeer(my_port)
    elif protocol == 'tcp':
        peer = TcpPeer(my_port)
    else:
        raise Exception('Unsupported protocol')

    curio.run(peer.start)


def parse_conn_info(ln: str) -> Tuple[str, int]:
    parts = ln.strip().split()
    return (parts[0], int(parts[1]))


async def whats_my_external_ip(protocol: str='udp') -> Tuple[str, int]:
    if protocol == 'udp':
        stun_port = 19302
        stun_ip = await resolve_hostname('stun.l.google.com', stun_port)
        _, ip, port = await stun.get_ip_info(stun_host=stun_ip, stun_port=stun_port)
        return (ip, port)
    elif protocol == 'tcp':
        return await stun.get_ip_for_tcp('35.202.168.244', 80)
    else:
        raise Exception('Unsupported protocol')


async def resolve_hostname(hostname: str, port: int=None) -> str:
    """DNS resolve hostname.

    Args:
        hostname: hostname to get IP address for.
        port: optional. Used to hint what DNS entry we're looking
            for.

    Returns:
        IP address used to connect to the specified hostname.
    """
    try:
        res = await socket.getaddrinfo(hostname, port, socket.AF_INET)
        if len(res) == 0:
            return None

        _, _, _, _, socket_addr = res[0]
        ip_addr, _ = socket_addr

        return ip_addr
    except socket.gaierror:
        return None


if __name__ == '__main__':
    main()
