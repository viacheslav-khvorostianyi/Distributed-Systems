import grpc
import server_pb2
import server_pb2_grpc
from logging_config import setup_logger
import asyncio
from aiohttp import web
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8081, help='Port to run the http server on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the gRPC server on')
parser.add_argument('--target_port', type=int, default=50052, help='Port to run the gRPC server on')
port, host, target_port = parser.parse_args().port, parser.parse_args().host, parser.parse_args().target_port
logger = setup_logger(f'server_secondary:{port}')

class ReplicatorService(server_pb2_grpc.ReplicatorServicer):
    LOG = []
    async def ReplicateLog(self, request, context):
        logger.info(f"Received replicated log: {request.message}")
        self.LOG.append(request)
        return server_pb2.LogReply(message=f"message {request.id} successfully replicated on port {port}")
    async def GetAllLogs(self, request, context):
        return server_pb2.AllLogs(logs=self.LOG)


replicator_service = ReplicatorService()

async def get_logs(request):
    # Convert protobuf messages to dicts for JSON serialization
    logs = sorted(list(set([
        {"id": log.id, "message": log.message}
        for log in replicator_service.LOG
    ])), key=lambda log: log["id"])

    return web.json_response({"logs": logs})

async def start_http_server():
    app = web.Application()
    app.router.add_get('/logs', get_logs)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def serve():
    grpc_server = grpc.aio.server()
    server_pb2_grpc.add_ReplicatorServicer_to_server(replicator_service, grpc_server)
    grpc_server.add_insecure_port(f'[::]:{target_port}')
    await grpc_server.start()
    await start_http_server()
    await grpc_server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
