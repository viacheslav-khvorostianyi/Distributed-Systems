# Distributed Systems Project

This project implements a distributed logging system using Python, gRPC, and Quart. It consists of a master server, secondary servers, and a master client for sending and retrieving logs.

## Project Structure

- `master.py` - Master server handling log reception and forwarding.
- `secondary.py` - Secondary servers for log replication.
- `master_client.py` - HTTP API for sending logs to the master via gRPC.
- `server.proto` - Protocol Buffers definition for gRPC services.
- `server_pb2.py`, `server_pb2_grpc.py` - Generated gRPC code.
- `logging_config.py` - Logging setup utility.
- `Dockerfile.master`, `Dockerfile.secondary1`, `Dockerfile.secondary2`, `Dockerfile.master_client` - Dockerfiles for each service.
- `docker-compose.yml` - Orchestrates all services.
- `requirements.txt` - Python dependencies.
- `.gitignore` - Git ignore file.
- `README.md` - Project documentation.

## Setup

1. **Clone the repository:**  git clone https://github.com/viacheslav-khvorostianyi/Distributed-Systems.git; cd Distributed-Systems
2. **Build and start all services:**  `docker-compose up --build`
3. **Access the master client API:**
   - Send logs: `curl -X POST  -H "Content-Type: application/json" -d '{"message": "Hello World"}' http://127.0.0.1:8080/send_log`
   - Get logs: `curl http:127.0.0.1:8080/logs` from master client.
   - Get logs from secondary servers: `curl http:127.0.0.1:8081/logs` and `curl http:127.0.0.1:8082/logs`

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