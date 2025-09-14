import json
import argparse

from quart import Quart, request, jsonify
import grpc
import server_pb2
import server_pb2_grpc
from google.protobuf import empty_pb2
from logging_config import setup_logger

logger = setup_logger('master_client')


app = Quart(__name__)

COUNTER = 0
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8080, help='Port to run the http server on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the gRPC server on')
parser.add_argument('--target_port', type=int, default=50051, help='Port to run the gRPC server on')

port, host, target_port = parser.parse_args().port, parser.parse_args().host, parser.parse_args().target_port

@app.route('/send_log', methods=['POST'])
async def send_log():
    data = await request.get_json()
    global COUNTER
    global PORT
    COUNTER += 1
    message = json.dumps({'id':COUNTER, 'message':data.get('message', 'default_message')})
    try:
        with grpc.insecure_channel(f'{host}:{target_port}') as channel:
            stub = server_pb2_grpc.LoggerStub(channel)
            response = stub.ReceiveLog(server_pb2.LogRequest(message=message))
            logger.info(f"Sent log to master at port {target_port}: {response.message}")
        return jsonify({'status':200})
    except Exception as e:
        logger.error(f"Failed to send log to master at port {target_port}: {e}")
        return jsonify({'status':500})

@app.route('/logs', methods=['GET'])
async def get_logs():
    with grpc.insecure_channel(f'{host}:{target_port}') as channel:
        stub = server_pb2_grpc.LoggerStub(channel)
        response = stub.GetAllLogs(empty_pb2.Empty())
    logs = [{"id": log.id, 'message': log.message} for log in response.logs]
    return jsonify(logs)

if __name__ == '__main__':
    app.run(port=port)