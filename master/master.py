import asyncio
import os

import grpc
import argparse
import server_pb2
import server_pb2_grpc
from quart import Quart, request, jsonify
from logging_config import setup_logger
import traceback

logger = setup_logger('master')

parser = argparse.ArgumentParser()
parser.add_argument('--target_port', type=int, default=50051, help='Port to run the http server on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the http server on')
parser.add_argument('--number_of_replicas', type=int, default=2, help='Number of replicas to forward logs to')
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

app = Quart(__name__)
COUNTER = 0
COUNTER_LOCK = asyncio.Lock()
LOG = []
LOG_LOCK = asyncio.Lock()



async def forward_log_to_secondary(channel_name, item, log_id, ACKS):
    max_retries = int(os.environ.get("MAX_RETRIES", 3))
    for attempt in range(max_retries):
        async with grpc.aio.insecure_channel(channel_name) as channel_obj:
            try:
                stub = server_pb2_grpc.ReplicatorStub(channel_obj)
                response = await stub.ReplicateLog(item)
                logger.info(f"Forwarded log to secondary {channel_name}: {response.message}")
                ACKS[log_id] = ACKS.get(log_id, 0) + 1
                break
            except Exception as e:
                logger.error(f"Failed to forward log to secondary {channel_name}"
                             f" within attempt {attempt}: {e} \n Retrying...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Max retries reached for {channel_name}. Giving up.")
                    raise



@app.route('/send_log', methods=['POST'])
async def send_log():
    data = await request.get_json()
    w = int(data.get('w', 1))
    if w > number_of_replicas + 1:
        return jsonify({'status': 400, 'error': 'w cannot be greater than number_of_replicas + 1'})
    global COUNTER
    async with COUNTER_LOCK:
        COUNTER += 1
        message_id = COUNTER
    ACKS = {message_id: 1}
    ack_event = asyncio.Event()
    message = {'id': message_id, 'message': str(data.get('message', 'default_message'))}
    global LOG
    async with LOG_LOCK:
        LOG.append(message)
    async def forward_and_ack(channel_name, item, log_id):
        try:
            await forward_log_to_secondary(channel_name, item, log_id, ACKS)
            if ACKS[log_id] >= w:
                ack_event.set()
        except Exception:
            logger.error(f"Failed to get acknowledgement from {channel_name}")
            ack_event.set()

    try:
        item = server_pb2.LogTuple(id=message['id'], message=message['message'])
        channels = [
            ChannelWrapper(f'secondary{i}:{target_port + i}',
                           grpc.insecure_channel(f'secondary{i}:{target_port + i}'))
            for i in range(1, number_of_replicas + 1)
        ]
        for channel in channels:
            asyncio.create_task(forward_and_ack(channel.name, item, message_id))
        if w == 1:
            ack_event.set()
        await ack_event.wait()
        ack_count = ACKS.get(message_id, 0)
        if ack_count >= w:
            return jsonify({'status': 200, 'acks': ack_count})
        else:
            return jsonify({'status': 502, 'error': 'Failed to achieve required acknowledgments'})
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        return jsonify({'status': 500, 'error': 'Internal server error'})
    finally:
        ACKS.pop(message_id, None)

@app.route('/logs', methods=['GET'])
async def get_logs():
    global LOG
    return jsonify({'logs':LOG})


async def start_quart():
    await app.run_task(port=port, host='0.0.0.0')

if __name__ == '__main__':
    asyncio.run(start_quart())