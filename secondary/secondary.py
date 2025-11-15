import asyncio
import grpc
import server_pb2
import server_pb2_grpc
from logging_config import setup_logger
import argparse
from quart import Quart, jsonify
import os

logger = setup_logger('secondary')

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=50052)
parser.add_argument('--http_port', type=int, default=8081)
parser.add_argument('--error_rate', type=float, default=0.1)
args = parser.parse_args()

# Override with environment variable if present
NETWORK_DELAY = float(os.getenv('DELAY', 0))

# Create Quart app
app = Quart(__name__)

# Deduplication tracking
received_message_ids = set()

# Total order tracking
log = []
buffered_messages = {}
next_expected_id = 1
log_lock = asyncio.Lock()


def process_buffered_messages():
    """Process all consecutive messages from buffer"""
    global next_expected_id

    while next_expected_id in buffered_messages:
        message = buffered_messages[next_expected_id]
        log.append((next_expected_id, message))
        logger.info(f"Added message {next_expected_id} to log (from buffer)")
        del buffered_messages[next_expected_id]
        next_expected_id += 1


class ReplicatorServicer(server_pb2_grpc.ReplicatorServicer):
    async def ReplicateLog(self, request, context):
        """Handle log replication with deduplication and total order"""
        # Simulate network delay
        if NETWORK_DELAY > 0:
            logger.debug(f"Simulating network delay of {NETWORK_DELAY}s")
            await asyncio.sleep(NETWORK_DELAY)

        async with log_lock:
            # Deduplication check
            if request.id in received_message_ids:
                logger.info(f"Duplicate message {request.id}, skipping")
                return server_pb2.LogResponse(message="Duplicate", success=True)

            # Mark as received immediately
            received_message_ids.add(request.id)

            # Total order handling
            global next_expected_id

            if request.id == next_expected_id:
                # Expected message, add to log
                log.append((request.id, request.message))
                logger.info(f"Added message {request.id} to log")
                next_expected_id += 1

                # Process any buffered consecutive messages
                process_buffered_messages()
            else:
                # Out of order, buffer it
                logger.info(f"Buffering out-of-order message {request.id}, expecting {next_expected_id}")
                buffered_messages[request.id] = request.message

            return server_pb2.LogResponse(message="Success", success=True)

    async def Heartbeat(self, request, context):
        """Handle heartbeat requests"""

        last_log_id = log[-1][0] if log else 0
        logger.debug(f"Heartbeat from {request.secondary_name}, last_log_id={last_log_id}")
        return server_pb2.HeartbeatResponse(
            status="Healthy",
            last_log_id=last_log_id
        )

    async def GetMissedLogs(self, request, context):
        """Return logs that secondary missed"""
        # Simulate network delay
        if NETWORK_DELAY > 0:
            await asyncio.sleep(NETWORK_DELAY)

        async with log_lock:
            missed_logs = [
                server_pb2.LogTuple(id=msg_id, message=msg)
                for msg_id, msg in log
                if msg_id > request.last_received_id
            ]
            logger.info(f"Sending {len(missed_logs)} missed logs")
            return server_pb2.MissedLogsResponse(logs=missed_logs)


@app.route('/logs', methods=['GET'])
async def get_logs():
    """Get all logs from this secondary"""
    async with log_lock:
        return jsonify({
            'logs': [{'id': msg_id, 'message': msg} for msg_id, msg in log]
        })


@app.route('/health', methods=['GET'])
async def health_check():
    """Health check endpoint"""
    async with log_lock:
        return jsonify({
            'status': 'healthy',
            'last_log_id': log[-1][0] if log else 0,
            'total_logs': len(log),
            'buffered_messages': len(buffered_messages),
            'next_expected_id': next_expected_id,
            'network_delay': NETWORK_DELAY
        })


async def serve_grpc():
    """Start gRPC server"""
    server = grpc.aio.server()
    server_pb2_grpc.add_ReplicatorServicer_to_server(ReplicatorServicer(), server)
    server.add_insecure_port(f'[::]:{args.port}')
    await server.start()
    logger.info(f"gRPC server started on port {args.port} with network delay={NETWORK_DELAY}s")
    await server.wait_for_termination()


async def serve_http():
    """Start HTTP server"""
    logger.info(f"HTTP server starting on port {args.http_port}")
    await app.run_task(host='0.0.0.0', port=args.http_port)


async def main():
    """Run both gRPC and HTTP servers concurrently"""
    await asyncio.gather(
        serve_grpc(),
        serve_http()
    )


if __name__ == '__main__':
    asyncio.run(main())
