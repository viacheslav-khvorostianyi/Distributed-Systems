# Distributed Systems Project

This project implements a distributed logging system using Python, gRPC, and Quart. It consists of a master server, secondary servers, and a master client for sending and retrieving logs.

## Project Structure

- `master.py` - Master server handling log reception and forwarding.
- `secondary.py` - Secondary servers for log replication.
- `server.proto` - Protocol Buffers definition for gRPC services.
- `logging_config.py` - Logging setup utility.
- `Dockerfile.master`, `Dockerfile.secondary1`, `Dockerfile.secondary2` - Dockerfiles for each service.
- `docker-compose.yml` - Orchestrates all services.
- `requirements.txt` - Python dependencies.
- `.gitignore` - Git ignore file.
- `README.md` - Project documentation.

## Setup

1. **Clone the repository:**  git clone https://github.com/viacheslav-khvorostianyi/Distributed-Systems.git; cd Distributed-Systems
2. **Build and start all services:**  `docker-compose up --build`
3. **Access the master client API:**
   - Send logs:  
     * `curl -X POST  -H "Content-Type: application/json" -d '{"message": "Hello World", "w":1}' http://127.0.0.1:8080/send_log`
     * `curl -X POST  -H "Content-Type: application/json" -d '{"message": "Hello World", "w":2}' http://127.0.0.1:8080/send_log`
     * `curl -X POST  -H "Content-Type: application/json" -d '{"message": "Hello World", "w":3}' http://127.0.0.1:8080/send_log`  
     * `curl -X POST  -H "Content-Type: application/json" -d '{"message": "Hello World", "w":4}' http://127.0.0.1:8080/send_log`  
   - Get logs: `curl http://127.0.0.1:8080/logs` from master client.
   - Get logs from secondary servers: `curl http://127.0.0.1:8081/logs` and `curl http://127.0.0.1:8082/logs`

## Configuration

- Ports and hostnames are configured in `docker-compose.yml`.
- Logging levels and formats can be adjusted in `logging_config.py`.  
- gRPC services are defined in `server.proto`.  
- Dockerfiles specify the environment for each service.  
- Dependencies are listed in `requirements.txt`.  
- The `docker-compose.yml` file orchestrates the multi-container setup.  
- The project uses Python 3.12.
- The `quart` library is used for the HTTP API in the master client.  
- The `grpcio` and `grpcio-tools` libraries are used for gRPC communication.  
- The `protobuf` library is used for Protocol Buffers serialization.  


## Troubleshooting

- Check container logs: `docker-compose logs <service_name>`
- Ensure all services are running: `docker-compose ps`
- Verify network connectivity between containers.  

Sef-check assessment:
```bash                                                                                                                                                            
Attaching to distributed-systems_secondary1_1, distributed-systems_secondary2_1, distributed-systems_master_1
secondary2_1  | 2025-11-15 11:53:38,503 - secondary - INFO - HTTP server starting on port 8082
secondary1_1  | 2025-11-15 11:53:38,505 - secondary - INFO - HTTP server starting on port 8081
secondary2_1  | 2025-11-15 11:53:38,505 - secondary - INFO - gRPC server started on port 50053 with network delay=1.0s
secondary2_1  | [2025-11-15 11:53:38 +0000] [1] [INFO] Running on http://0.0.0.0:8082 (CTRL + C to quit)
secondary1_1  | 2025-11-15 11:53:38,507 - secondary - INFO - gRPC server started on port 50052 with network delay=5.0s
secondary1_1  | [2025-11-15 11:53:38 +0000] [1] [INFO] Running on http://0.0.0.0:8081 (CTRL + C to quit)
master_1      | [2025-11-15 11:53:39 +0000] [1] [INFO] Running on http://0.0.0.0:8080 (CTRL + C to quit)
secondary2_1  | 2025-11-15 11:53:47,415 - secondary - INFO - Added message 1 to log
master_1      |  * Serving Quart app 'master'
master_1      |  * Debug mode: False
master_1      |  * Please use an ASGI server (e.g. Hypercorn) directly in production
master_1      |  * Running on http://0.0.0.0:8080 (CTRL + C to quit)
master_1      | 2025-11-15 11:53:47,416 - master - INFO - Log 1 forwarded to secondary2:50053
secondary1_1  | 2025-11-15 11:53:51,416 - secondary - INFO - Added message 1 to log
master_1      | 2025-11-15 11:53:51,417 - master - INFO - Log 1 forwarded to secondary1:50052
master_1      | [2025-11-15 11:53:51 +0000] [1] [INFO] 172.18.0.1:47730 POST /send_log 1.1 200 39 5008125
secondary2_1  | 2025-11-15 11:54:00,116 - secondary - INFO - Added message 2 to log
master_1      | 2025-11-15 11:54:00,117 - master - INFO - Log 2 forwarded to secondary2:50053
master_1      | [2025-11-15 11:54:00 +0000] [1] [INFO] 172.18.0.1:47720 POST /send_log 1.1 200 39 1006002
secondary1_1  | 2025-11-15 11:54:04,117 - secondary - INFO - Added message 2 to log
master_1      | 2025-11-15 11:54:04,118 - master - INFO - Log 2 forwarded to secondary1:50052
master_1      | [2025-11-15 11:54:04 +0000] [1] [INFO] 172.18.0.1:47722 POST /send_log 1.1 200 39 2407
secondary2_1  | 2025-11-15 11:54:05,465 - secondary - INFO - Added message 3 to log
master_1      | 2025-11-15 11:54:05,466 - master - INFO - Log 3 forwarded to secondary2:50053
secondary1_1  | 2025-11-15 11:54:09,468 - secondary - INFO - Added message 3 to log
master_1      | 2025-11-15 11:54:09,469 - master - INFO - Log 3 forwarded to secondary1:50052
master_1      | [2025-11-15 11:55:08 +0000] [1] [INFO] 172.18.0.1:58122 POST /send_log 1.1 200 39 2331
secondary2_1  | 2025-11-15 11:55:09,499 - secondary - INFO - Added message 4 to log
master_1      | 2025-11-15 11:55:09,500 - master - INFO - Log 4 forwarded to secondary2:50053
secondary2_1  | 2025-11-15 11:55:12,068 - secondary - INFO - Added message 5 to log
master_1      | 2025-11-15 11:55:12,069 - master - INFO - Log 5 forwarded to secondary2:50053
master_1      | [2025-11-15 11:55:12 +0000] [1] [INFO] 172.18.0.1:37568 POST /send_log 1.1 200 39 1005003
master_1      | 2025-11-15 11:55:14,500 - master - ERROR - Failed to forward log 4 to secondary1:50052 (attempt 1, status=Suspected): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
master_1      | >. Retrying in 1s...
master_1      | 2025-11-15 11:55:17,070 - master - ERROR - Failed to forward log 5 to secondary1:50052 (attempt 1, status=Suspected): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
master_1      | >. Retrying in 1s...
secondary2_1  | 2025-11-15 11:55:17,755 - secondary - INFO - Added message 6 to log
master_1      | 2025-11-15 11:55:17,756 - master - INFO - Log 6 forwarded to secondary2:50053
master_1      | 2025-11-15 11:55:21,504 - master - ERROR - Failed to forward log 4 to secondary1:50052 (attempt 2, status=Unhealthy): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_message:"Deadline Exceeded", grpc_status:4}"
master_1      | >. Retrying in 30s...
master_1      | 2025-11-15 11:55:24,046 - master - ERROR - Failed to forward log 6 to secondary1:50052 (attempt 1, status=Unhealthy): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
master_1      | >. Retrying in 30s...
master_1      | 2025-11-15 11:55:25,365 - master - ERROR - Failed to forward log 5 to secondary1:50052 (attempt 2, status=Unhealthy): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
master_1      | >. Retrying in 30s...
master_1      | 2025-11-15 11:56:00,097 - master - ERROR - Failed to forward log 4 to secondary1:50052 (attempt 3, status=Unhealthy): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
master_1      | >. Retrying in 30s...
master_1      | 2025-11-15 11:56:01,350 - master - ERROR - Failed to forward log 6 to secondary1:50052 (attempt 2, status=Unhealthy): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
master_1      | >. Retrying in 30s...
master_1      | 2025-11-15 11:56:02,669 - master - ERROR - Failed to forward log 5 to secondary1:50052 (attempt 3, status=Unhealthy): <AioRpcError of RPC that terminated with:
master_1      |         status = StatusCode.DEADLINE_EXCEEDED
master_1      |         details = "Deadline Exceeded"
master_1      |         debug_error_string = "UNKNOWN:Error received from peer  {grpc_message:"Deadline Exceeded", grpc_status:4}"
master_1      | >. Retrying in 30s...
master_1      | 2025-11-15 11:56:09,776 - master - INFO - secondary1:50052 recovered, starting sync
master_1      | 2025-11-15 11:56:09,778 - master - INFO - Syncing secondary1:50052, last_id=3
secondary1_1  | 2025-11-15 11:56:14,780 - secondary - INFO - Added message 4 to log
master_1      | 2025-11-15 11:56:14,781 - master - INFO - Log 4 forwarded to secondary1:50052
master_1      | 2025-11-15 11:56:19,344 - master - WARNING - Timeout waiting for acks for message 6
master_1      | [2025-11-15 11:56:19 +0000] [1] [INFO] 172.18.0.1:37572 POST /send_log 1.1 202 87 62593631
secondary1_1  | 2025-11-15 11:56:19,784 - secondary - INFO - Added message 5 to log
master_1      | 2025-11-15 11:56:19,785 - master - INFO - Log 5 forwarded to secondary1:50052
secondary1_1  | 2025-11-15 11:56:24,790 - secondary - INFO - Added message 6 to log
master_1      | 2025-11-15 11:56:24,791 - master - INFO - Log 6 forwarded to secondary1:50052
master_1      | 2025-11-15 11:56:24,791 - master - INFO - Sync completed for secondary1:50052
secondary1_1  | 2025-11-15 11:56:36,399 - secondary - INFO - Duplicate message 4, skipping
secondary1_1  | 2025-11-15 11:56:36,399 - secondary - INFO - Duplicate message 4, skipping
master_1      | 2025-11-15 11:56:36,400 - master - INFO - Log 4 forwarded to secondary1:50052
secondary1_1  | 2025-11-15 11:56:37,654 - secondary - INFO - Duplicate message 6, skipping
master_1      | 2025-11-15 11:56:37,654 - master - INFO - Log 6 forwarded to secondary1:50052
secondary1_1  | 2025-11-15 11:56:38,971 - secondary - INFO - Duplicate message 5, skipping
master_1      | 2025-11-15 11:56:38,973 - master - INFO - Log 5 forwarded to secondary1:50052
secondary1_1  | [2025-11-15 11:57:52 +0000] [1] [INFO] 172.18.0.1:54304 GET /logs 1.1 200 209 6399
secondary2_1  | [2025-11-15 11:58:08 +0000] [1] [INFO] 172.18.0.1:48344 GET /logs 1.1 200 209 2894
master_1      | [2025-11-15 11:58:26 +0000] [1] [INFO] 172.18.0.1:46274 GET /logs 1.1 200 209 957
master_1      | 2025-11-15 12:07:34,457 - master - WARNING - Lost quorum! Healthy: 1/3. Entering read-only mode.
master_1      | [2025-11-15 12:08:10 +0000] [1] [INFO] 172.18.0.1:40744 GET /logs 1.1 200 209 1230

```