import logging as pylogging
from typing import List

from grpclib.events import listen, RecvRequest
from grpclib.reflection.service import ServerReflection
from grpclib.server import Server as GRPCServer
from grpclib.utils import graceful_exit

from viam import logging
from viam.components.base import BaseService
from viam.components.component_base import ComponentBase
from viam.components.motor import MotorService
from viam.components.resource_manager import ResourceManager
from viam.components.imu import IMUService
from viam.components.pose_tracker import PoseTrackerService
from viam.components.sensor import SensorService
from viam.components.servo import ServoService
from viam.metadata.service import MetadataService
from viam.robot.service import RobotService

from .signaling import SignalingService


LOGGER = logging.getLogger(__name__)


class Server(ResourceManager):
    """
    gRPC Server
    """

    def __init__(
        self,
        components: List[ComponentBase]
    ):
        """
        Initialize the Server with a list of components
        to be managed.

        Args:
            components (List[ComponentBase]): List of components to be managed
        """
        super().__init__(components)

        services = [
            SignalingService(),
            MetadataService(manager=self),
            RobotService(manager=self),
            BaseService(manager=self),
            IMUService(manager=self),
            MotorService(manager=self),
            PoseTrackerService(manager=self),
            SensorService(manager=self),
            ServoService(manager=self),
        ]
        services = ServerReflection.extend(services)
        self._server = GRPCServer(services)

    async def _grpc_event_handler(
        self,
        event: RecvRequest
    ):
        host = None
        port = None
        address = event.peer.addr()
        if address:
            host = address[0]
            port = address[1]
        msg = '[gRPC Request] ' + \
              f'{host or "xxxx"}:{port or "xxxx"} - ' + \
              f'{event.method_name}'
        LOGGER.info(msg)

    async def serve(
        self,
        host: str = 'localhost',
        port: int = 9090,
        log_level: int = pylogging.INFO,
    ):
        """
        Server the gRPC server on the provided host and port

        Args:
            host (str, optional): Desired hostname of the server.
                Defaults to 'localhost'.
            port (int, optional): Desired port of the server.
                Defaults to 9090.
            log_level(int, optional): The minimum log level.
                To not receive any logs, set to None
                Defaults to logging.INFO
        """
        logging.setLevel(log_level)
        listen(self._server, RecvRequest, self._grpc_event_handler)

        with graceful_exit([self._server]):
            await self._server.start(host, port)
            print(f'Serving on {host}:{port}')
            await self._server.wait_closed()

    def close(self):
        self._server.close()

    @classmethod
    async def create_and_serve(
        cls,
        components: List[ComponentBase],
        host: str = "localhost",
        port: int = 9090,
        log_level: int = pylogging.INFO,
    ):
        """
        Convenience method to create and start the server.

        Args:
            components (List[ComponentBase]): List of components to manage
            host (str, optional): Desired hostname. Defaults to "localhost".
            port (int, optional): Desired port. Defaults to 9090.
            log_level(int, optional): The minimum log level.
                To not receive any logs, set to None.
                Defaults to logging.INFO
        """
        server = cls(components)
        await server.serve(host, port, log_level)