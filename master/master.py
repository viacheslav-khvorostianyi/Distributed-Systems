import asyncio
import time
import grpc
import argparse
import server_pb2
import server_pb2_grpc
from quart import Quart, request, jsonify
from logging_config import setup_logger
from pydantic import BaseModel
import traceback
from enum import Enum

logger = setup_logger('master')

class HealthStatus(Enum):
    HEALTHY = "Healthy"
    SUSPECTED = "Suspected"
    UNHEALTHY = "Unhealthy"

class MessageModel(BaseModel):
    message: str
    w: int = 1

parser = argparse.ArgumentParser()
parser.add_argument('--target_port', type=int, default=50051)
parser.add_argument('--host', type=str, default='127.0.0.1')
parser.add_argument('--number_of_replicas', type=int, default=2)
parser.add_argument('--port', type=int, default=8080)
parser.add_argument('--heartbeat_interval', type=int, default=5)
parser.add_argument('--suspected_timeout', type=int, default=10)
parser.add_argument('--unhealthy_timeout', type=int, default=20)

args = parser.parse_args()
port, host, number_of_replicas, target_port = (
    args.port, args.host, args.number_of_replicas, args.target_port
)

app = Quart(__name__)
COUNTER = 0
COUNTER_LOCK = asyncio.Lock()
LOG = []
LOG_LOCK = asyncio.Lock()
ACKS = {}
ACKS_LOCK = asyncio.Lock()
SECONDARY_CHANNELS = {}
SECONDARY_HEALTH = {}
READ_ONLY_MODE = False


async def init_channels():
    """Initialize persistent gRPC channels to secondaries"""
    for i in range(1, number_of_replicas + 1):
        channel_name = f'secondary{i}:{target_port + i}'
        SECONDARY_CHANNELS[channel_name] = grpc.aio.insecure_channel(channel_name)
        SECONDARY_HEALTH[channel_name] = {
            'status': HealthStatus.HEALTHY,
            'last_check': time.time(),
            'last_log_id': 0
        }


def update_health_status(channel_name):
    """Update health status based on time since last successful check"""
    now = time.time()
    last_check = SECONDARY_HEALTH[channel_name]['last_check']
    elapsed = now - last_check

    if elapsed > args.unhealthy_timeout:
        SECONDARY_HEALTH[channel_name]['status'] = HealthStatus.UNHEALTHY
    elif elapsed > args.suspected_timeout:
        SECONDARY_HEALTH[channel_name]['status'] = HealthStatus.SUSPECTED
    else:
        SECONDARY_HEALTH[channel_name]['status'] = HealthStatus.HEALTHY


async def forward_log_to_secondary(channel_name, item, log_id, ack_event):
    """Forward log with unlimited retries and exponential backoff"""
    attempt = 0
    base_delay = 1
    max_delay = 120

    while True:
        try:
            channel = SECONDARY_CHANNELS[channel_name]
            stub = server_pb2_grpc.ReplicatorStub(channel)
            response = await stub.ReplicateLog(item, timeout=6)

            if response.success:
                logger.info(f"Log {log_id} forwarded to {channel_name}")
                async with ACKS_LOCK:
                    ACKS[log_id] = ACKS.get(log_id, 0) + 1
                SECONDARY_HEALTH[channel_name]['last_check'] = time.time()
                SECONDARY_HEALTH[channel_name]['status'] = HealthStatus.HEALTHY
                SECONDARY_HEALTH[channel_name]['last_log_id'] = log_id
                break
        except Exception as e:
            attempt += 1
            update_health_status(channel_name)

            if SECONDARY_HEALTH[channel_name]['status'] == HealthStatus.UNHEALTHY:
                delay = max_delay
            else:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)

            logger.error(f"Failed to forward log {log_id} to {channel_name} "
                         f"(attempt {attempt}, status={SECONDARY_HEALTH[channel_name]['status'].value}): {e}. "
                         f"Retrying in {delay}s...")
            await asyncio.sleep(delay)


async def sync_secondary(channel_name):
    """Sync missed logs when secondary rejoins"""
    try:
        channel = SECONDARY_CHANNELS[channel_name]
        stub = server_pb2_grpc.ReplicatorStub(channel)

        health = await stub.Heartbeat(
            server_pb2.HeartbeatRequest(secondary_name=channel_name)
        )
        last_id = health.last_log_id

        logger.info(f"Syncing {channel_name}, last_id={last_id}")

        async with LOG_LOCK:
            for msg_id, message in LOG:
                if msg_id > last_id:
                    item = server_pb2.LogTuple(id=msg_id, message=message)
                    await forward_log_to_secondary(channel_name, item, msg_id, None)

        logger.info(f"Sync completed for {channel_name}")
    except Exception as e:
        logger.error(f"Failed to sync {channel_name}: {e}")


async def heartbeat_loop():
    """Continuously monitor secondary health"""
    while True:
        for channel_name in SECONDARY_CHANNELS:
            try:
                channel = SECONDARY_CHANNELS[channel_name]
                stub = server_pb2_grpc.ReplicatorStub(channel)
                response = await stub.Heartbeat(
                    server_pb2.HeartbeatRequest(secondary_name=channel_name),
                    timeout=3
                )

                old_status = SECONDARY_HEALTH[channel_name]['status']
                SECONDARY_HEALTH[channel_name] = {
                    'status': HealthStatus.HEALTHY,
                    'last_check': time.time(),
                    'last_log_id': response.last_log_id
                }

                if old_status != HealthStatus.HEALTHY:
                    logger.info(f"{channel_name} recovered, starting sync")
                    asyncio.create_task(sync_secondary(channel_name))

            except Exception as e:
                logger.debug(f"Heartbeat failed for {channel_name}: {e}")
                update_health_status(channel_name)

        check_quorum()
        await asyncio.sleep(args.heartbeat_interval)


def check_quorum():
    """Check if we have quorum and update read-only mode"""
    global READ_ONLY_MODE
    healthy = sum(
        1 for h in SECONDARY_HEALTH.values()
        if h['status'] == HealthStatus.HEALTHY
    )
    total_nodes = number_of_replicas + 1
    required_quorum = (total_nodes // 2) + 1

    has_quorum = (healthy + 1) >= required_quorum

    if not has_quorum and not READ_ONLY_MODE:
        logger.warning(f"Lost quorum! Healthy: {healthy + 1}/{total_nodes}. Entering read-only mode.")
        READ_ONLY_MODE = True
    elif has_quorum and READ_ONLY_MODE:
        logger.info(f"Quorum restored! Healthy: {healthy + 1}/{total_nodes}. Exiting read-only mode.")
        READ_ONLY_MODE = False

    return has_quorum


@app.route('/send_log', methods=['POST'])
async def send_log():
    """Append message with write concern"""
    if READ_ONLY_MODE:
        return jsonify({'status': 503, 'error': 'Master is in read-only mode, no quorum'}), 503

    data = await request.get_json()
    w = int(data.get('w', 1))

    if w > number_of_replicas + 1:
        return jsonify({
            'status': 400,
            'error': f'w={w} cannot be greater than total nodes ({number_of_replicas + 1})'
        }), 400

    global COUNTER
    async with COUNTER_LOCK:
        COUNTER += 1
        message_id = COUNTER

    async with ACKS_LOCK:
        ACKS[message_id] = 1  # Master counts as 1 ack
    ack_event = asyncio.Event()
    message = str(data.get('message', 'default_message'))

    async with LOG_LOCK:
        LOG.append((message_id, message))

    async def forward_and_ack(channel_name, item, log_id):
        try:
            await forward_log_to_secondary(channel_name, item, log_id, ack_event)
            async with ACKS_LOCK:
                if ACKS.get(log_id, 0) >= w:
                    ack_event.set()
        except Exception as e:
            logger.error(f"Forward task failed for {channel_name}: {e}")

    try:
        item = server_pb2.LogTuple(id=message_id, message=message)

        for channel_name in SECONDARY_CHANNELS:
            asyncio.create_task(forward_and_ack(channel_name, item, message_id))

        if w == 1:
            ack_event.set()

        try:
            await asyncio.wait_for(ack_event.wait(), timeout=120)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for acks for message {message_id}")

        async with ACKS_LOCK:
            ack_count = ACKS.get(message_id, 0)

        if ack_count >= w:
            return jsonify({'status': 200, 'acks': ack_count, 'message_id': message_id})
        else:
            return jsonify({
                'status': 202,
                'message': f'Accepted but only {ack_count}/{w} acks received',
                'acks': ack_count,
                'message_id': message_id
            }), 202

    except Exception as e:
        logger.error(f"Error in send_log: {e}")
        traceback.print_exception(type(e), e, e.__traceback__)
        return jsonify({'status': 500, 'error': 'Internal server error'}), 500
    finally:
        async with ACKS_LOCK:
            ACKS.pop(message_id, None)


@app.route('/logs', methods=['GET'])
async def get_logs():
    """Get master logs"""
    async with LOG_LOCK:
        return jsonify({'logs': [{'id': msg_id, 'message': msg} for msg_id, msg in LOG]})


@app.get("/health")
async def get_health():
    """Get health status of all secondaries"""
    return jsonify({
        'read_only_mode': READ_ONLY_MODE,
        'secondaries': {
            name: {
                'status': health['status'].value,
                'last_check': health['last_check'],
                'last_log_id': health['last_log_id']
            }
            for name, health in SECONDARY_HEALTH.items()
        }
    })


async def startup():
    """Initialize channels and start background tasks"""
    await init_channels()
    asyncio.create_task(heartbeat_loop())


@app.before_serving
async def before_serving():
    await startup()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
