import json
import os

from quart import Quart, request, jsonify
import grpc
import master_pb2
import master_pb2_grpc
from google.protobuf import empty_pb2
from logging_config import setup_logger

logger = setup_logger(__name__)


app = Quart(__name__)

COUNTER = 0
PORT = os.getenv('MASTER_PORT', '50051')

@app.route('/send_log', methods=['POST'])
async def send_log():
    data = await request.get_json()
    global COUNTER
    global PORT
    COUNTER += 1
    message = json.dumps({'id':COUNTER, 'message':data.get('message', 'default_message')})
    try:
        with grpc.insecure_channel(f'localhost:{PORT}') as channel:
            stub = master_pb2_grpc.LoggerStub(channel)
            response = stub.ReceiveLog(master_pb2.LogRequest(message=message))
            logger.info(f"Sent log to master at port {PORT}: {response.message}")
        return jsonify({'status':200})
    except Exception as e:
        logger.error(f"Failed to send log to master at port {PORT}: {e}")
        return jsonify({'status':500})

@app.route('/get_logs', methods=['GET'])
async def get_logs():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = master_pb2_grpc.LoggerStub(channel)
        response = stub.GetAllLogs(empty_pb2.Empty())
    logs = [{"id": log.id, 'message': log.message} for log in response.logs]
    return jsonify(logs)

if __name__ == '__main__':
    app.run(port=8080)