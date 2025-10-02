import asyncio
import multiprocessing
import grpc
import json
import argparse
import server_pb2
import server_pb2_grpc
from quart import Quart, request, jsonify
from google.protobuf import empty_pb2
from logging_config import setup_logger

logger = setup_logger('master')

parser = argparse.ArgumentParser()
parser.add_argument('--target_port', type=int, default=50051, help='Port to run the http server on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the http server on')
parser.add_argument('--number_of_replicas', type=int, default=1, help='Number of replicas to forward logs to')
parser.add_argument('--port', type=int, default=8080, help='Port to run the http server on')
port, host, number_of_replicas, target_port = (parser.parse_args().port, parser.parse_args().host,
                                  parser.parse_args().number_of_replicas, parser.parse_args().target_port)

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
    LOG_LOCK = asyncio.Lock()

    async def forward_log_to_secondary(self, channel_name, item):
        async with grpc.aio.insecure_channel(channel_name) as channel_obj:
            try:
                stub = server_pb2_grpc.ReplicatorStub(channel_obj)
                response = await stub.ReplicateLog(item)
                logger.info(f"Forwarded log to secondary {channel_name}: {response.message}")
                logger.info(response.message)
            except Exception as e:
                logger.error(f"Failed to forward log to secondary {channel_name}: {e}")


    async def ReceiveLog(self, request, context):
        logger.info(f"Received log: {request.message}")
        msg = json.loads(request.message)
        item = server_pb2.LogTuple(id=msg['id'], message=msg['message'])
        async with self.LOG_LOCK:
            self.LOG.append(item)
        channels = [
            ChannelWrapper(f'secondary{i}:{target_port + i}', grpc.insecure_channel(f'secondary{i}:{target_port + i}'))
            for i in range(1, number_of_replicas + 1)
        ]
        tasks = [asyncio.create_task(self.forward_log_to_secondary(channel.name, item)) for channel in channels]

        return server_pb2.LogReply(message=f"message {msg['id']} successfully logged")

    async def GetAllLogs(self, request, context):
        async with self.LOG_LOCK:
            logs_copy = list(self.LOG)
        return server_pb2.AllLogs(logs=logs_copy)


async def serve():
    server = grpc.aio.server()
    server_pb2_grpc.add_LoggerServicer_to_server(LoggerService(), server)
    server.add_insecure_port(f'[::]:{target_port}')
    await server.start()
    await server.wait_for_termination()

# master  client  code
app = Quart(__name__)
COUNTER = 0
COUNTER_LOCK = asyncio.Lock()


@app.route('/send_log', methods=['POST'])
async def send_log():
    data = await request.get_json()
    global COUNTER
    async with COUNTER_LOCK:
        COUNTER += 1
        message_id = COUNTER
    message = json.dumps({'id':message_id, 'message':str(data.get('message', 'default_message'))})
    try:
        async with grpc.aio.insecure_channel(f'master:{target_port}/{message_id}') as channel:
            stub = server_pb2_grpc.LoggerStub(channel)
            response = await stub.ReceiveLog(server_pb2.LogRequest(message=message))
            logger.info(f"Sent log to master at port {target_port}: {response.message}")
        return jsonify({'status': 200})
    except Exception as e:
        logger.error(f"Failed to send log to master at port {target_port}: {e}")
        return jsonify({'status': 500})

@app.route('/logs', methods=['GET'])
async def get_logs():
    async with grpc.aio.insecure_channel(f'master:{target_port}') as channel:
        stub = server_pb2_grpc.LoggerStub(channel)
        response = await stub.GetAllLogs(empty_pb2.Empty())
    logs = {'logs': [{"id": log.id, 'message': log.message} for log in response.logs]}
    return jsonify(logs)


async def start_quart():
    await app.run_task(port=port, host='0.0.0.0')


def run_grpc():
    asyncio.run(serve())

def run_quart():
    asyncio.run(start_quart())

if __name__ == '__main__':
    grpc_process = multiprocessing.Process(target=run_grpc)
    quart_process = multiprocessing.Process(target=run_quart)
    grpc_process.start()
    quart_process.start()
    grpc_process.join()
    quart_process.join()