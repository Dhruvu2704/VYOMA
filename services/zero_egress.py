import socket


class ZeroEgressMonitor:

    def check_connection(self, host: str, port: int):

        try:

            socket.create_connection(
                (host, port),
                timeout=2
            )

            return {
                "allowed": False,
                "host": host,
                "port": port,
                "message": "Outbound connection detected"
            }

        except (socket.timeout, ConnectionRefusedError, OSError):

            return {
                "allowed": True,
                "host": host,
                "port": port,
                "message": "No outbound connection established"
            }