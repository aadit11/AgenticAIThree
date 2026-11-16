"""Forward local Ollama traffic through Tailscale's userspace SOCKS proxy.

The Cloud Run container has no kernel route to the tailnet. Tailscale's
Cloud Run guide publishes a SOCKS5 server on localhost. This process
listens on the normal Ollama port and opens each connection through that
proxy, so the rest of Lumen can keep using http://127.0.0.1:11434.
"""

from __future__ import annotations

import os
import socket
import threading
import time


def socks_connect_request(host: str, port: int) -> bytes:
    """SOCKS5 CONNECT request. No authentication."""
    try:
        packed = socket.inet_aton(host)
    except OSError:
        host_bytes = host.encode("idna")
        if len(host_bytes) > 255:
            raise ValueError("upstream host is too long")
        address = b"\x03" + bytes([len(host_bytes)]) + host_bytes
    else:
        address = b"\x01" + packed
    return b"\x05\x01\x00" + address + port.to_bytes(2, "big")


def _read_exact(sock: socket.socket, count: int) -> bytes:
    chunks = []
    remaining = count
    while remaining:
        piece = sock.recv(remaining)
        if not piece:
            raise OSError("socks proxy closed the handshake")
        chunks.append(piece)
        remaining -= len(piece)
    return b"".join(chunks)


def _open_upstream(proxy_host: str, proxy_port: int, upstream: str) -> socket.socket:
    host, _, port_text = upstream.rpartition(":")
    if not host or not port_text.isdigit():
        raise ValueError("OLLAMA_UPSTREAM must look like host:port")
    remote = socket.create_connection((proxy_host, proxy_port), timeout=20)
    remote.settimeout(20)
    remote.sendall(b"\x05\x01\x00")
    if _read_exact(remote, 2) != b"\x05\x00":
        remote.close()
        raise OSError("socks proxy rejected the greeting")
    remote.sendall(socks_connect_request(host, int(port_text)))
    head = _read_exact(remote, 4)
    if head[1] != 0:
        remote.close()
        raise OSError(f"socks connect failed with status {head[1]}")
    if head[3] == 1:
        _read_exact(remote, 4 + 2)
    elif head[3] == 4:
        _read_exact(remote, 16 + 2)
    elif head[3] == 3:
        length = _read_exact(remote, 1)[0]
        _read_exact(remote, length + 2)
    else:
        remote.close()
        raise OSError("socks proxy returned an unknown address")
    # The handshake timeout must not apply to a Gemma generation.
    remote.settimeout(None)
    return remote


def _relay(left: socket.socket, right: socket.socket) -> None:
    try:
        while True:
            data = left.recv(65536)
            if not data:
                break
            right.sendall(data)
    except OSError:
        pass
    finally:
        try:
            right.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _handle(client: socket.socket, proxy_host: str, proxy_port: int, upstream: str) -> None:
    remote = None
    try:
        last_error: OSError | None = None
        for _attempt in range(3):
            try:
                remote = _open_upstream(proxy_host, proxy_port, upstream)
                last_error = None
                break
            except OSError as exc:
                last_error = exc
                time.sleep(0.4)
        if remote is None and last_error is not None:
            raise last_error
        left = threading.Thread(target=_relay, args=(client, remote), daemon=True)
        right = threading.Thread(target=_relay, args=(remote, client), daemon=True)
        left.start()
        right.start()
        left.join()
        right.join()
    except OSError as exc:
        detail = str(exc)
        if "tskey" in detail or "Bearer" in detail:
            detail = type(exc).__name__
        print(f"isolation: ollama forward failed {detail}", flush=True)
    finally:
        client.close()
        if remote is not None:
            remote.close()


def serve(listen_host: str, listen_port: int, proxy_host: str, proxy_port: int, upstream: str) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(16)
    print(f"isolation: ollama forward listening {listen_port}", flush=True)
    while True:
        client, _addr = server.accept()
        threading.Thread(
            target=_handle,
            args=(client, proxy_host, proxy_port, upstream),
            daemon=True,
        ).start()


def main() -> None:
    upstream = os.environ["OLLAMA_UPSTREAM"]
    proxy = os.environ.get("TAILSCALE_SOCKS", "127.0.0.1:1055")
    proxy_host, _, proxy_port = proxy.rpartition(":")
    listen = os.environ.get("OLLAMA_FORWARD_LISTEN", "127.0.0.1:11434")
    listen_host, _, listen_port = listen.rpartition(":")
    serve(listen_host, int(listen_port), proxy_host, int(proxy_port), upstream)


if __name__ == "__main__":
    main()
