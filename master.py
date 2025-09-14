import asyncio
import grpc
import json
import master_pb2
import master_pb2_grpc
from logging_config import setup_logger
logger = setup_logger(__name__)



class LoggerService(master_pb2_grpc.LoggerServicer):
    LOG = []
    async def ReceiveLog(self, request, context):
        logger.info(f"Received log: {request.message}")
        msg = json.loads(request.message)
        self.LOG.append(master_pb2.LogTuple(id=msg['id'], message=msg['message']))

        return master_pb2.LogReply(message=f"message {msg['id']} successfully logged")

    async def GetAllLogs(self, request, context):
        return master_pb2.AllLogs(logs=self.LOG)

async def serve(port):
    server = grpc.aio.server()
    master_pb2_grpc.add_LoggerServicer_to_server(LoggerService(), server)
    server.add_insecure_port(f'[::]:{port}')
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve(50051))