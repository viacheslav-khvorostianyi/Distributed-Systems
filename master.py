import asyncio
import grpc
import json
import time
import argparse
import server_pb2
import server_pb2_grpc
from logging_config import setup_logger
logger = setup_logger('master')

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=50051, help='Port to run the http server on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the http server on')
parser.add_argument('--number_of_replicas', type=int, default=1, help='Number of replicas to forward logs to')
port, host, number_of_replicas = parser.parse_args().port, parser.parse_args().host, parser.parse_args().number_of_replicas

class ChannelWrapper:
    def __init__(self, name, channel):
        self.name = name
        self.channel = channel

    def __repr__(self):
        return f"<ChannelWrapper name={self.name}>"

    def __getattr__(self, attr):
        return getattr(self.channel, attr)

class LoggerService(server_pb2_grpc.LoggerServicer):
    LOG = []
    async def ReceiveLog(self, request, context):
        logger.info(f"Received log: {request.message}")
        msg = json.loads(request.message)
        item = server_pb2.LogTuple(id=msg['id'], message=msg['message'])
        self.LOG.append(item)
        channels = [
            ChannelWrapper(f'secondary{i}:{port + i}', grpc.insecure_channel(f'secondary{i}:{port + i}'))
            for i in range(1, number_of_replicas + 1)
        ]
        for channel in channels:
            try:
                stub = server_pb2_grpc.ReplicatorStub(channel)
                time.sleep(5)  # Simulate network delay
                response = stub.ReplicateLog(item)
                logger.info(f"Forwarded log to secondary {channel.__repr__()}: {response.message}")
                logger.info(response.message)
            except Exception as e:
                logger.error(f"Failed to forward log to secondary: {e}")
                raise
            finally:
                channel.close()

        return server_pb2.LogReply(message=f"message {msg['id']} successfully logged")

    async def GetAllLogs(self, request, context):
        return server_pb2.AllLogs(logs=self.LOG)


async def serve():
    server = grpc.aio.server()
    server_pb2_grpc.add_LoggerServicer_to_server(LoggerService(), server)
    server.add_insecure_port(f'[::]:{port}')
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())