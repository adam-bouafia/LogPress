# Deployment Directory

Docker infrastructure for containerized deployment of LogSim.

## Structure

```
deployment/
├── Dockerfile           # Container image definition
├── docker-compose.yml   # Service orchestration
└── Makefile            # Build automation
```

## Quick Start

### Build and Run

```bash
# Build all services
docker-compose -f deployment/docker-compose.yml build

# Run interactive CLI
docker-compose -f deployment/docker-compose.yml run --rm logsim-interactive

# Run bash menu
docker-compose -f deployment/docker-compose.yml run --rm logsim-interactive-bash
```

## Docker Services

### logsim-interactive (Python Rich UI)

**Beautiful terminal interface** with:
- Dataset auto-discovery
- Progress bars and tables
- Multi-select compression
- Query builder

```bash
docker-compose -f deployment/docker-compose.yml run --rm logsim-interactive
```

**Environment Variables**:
- `PYTHONUNBUFFERED=1` - Real-time output
- `TERM=xterm-256color` - Colored terminal

### logsim-interactive-bash (Bash Menu)

**Alternative bash interface** with:
- Colored menus
- Dataset scanning
- Compression workflows
- Results viewing

```bash
docker-compose -f deployment/docker-compose.yml run --rm logsim-interactive-bash
```

**Entry Point**: `/app/scripts/logsim-interactive.sh`

### logsim-cli (Command-Line)

**Direct command execution**:

```bash
# Compress logs
docker-compose -f deployment/docker-compose.yml run --rm logsim-cli \
  compress -i /app/data/datasets/Apache/Apache_full.log -o /app/evaluation/compressed/apache.lsc -m

# Query compressed logs
docker-compose -f deployment/docker-compose.yml run --rm logsim-cli \
  query -c /app/evaluation/compressed/apache.lsc --severity ERROR --limit 20

# Run evaluation
docker-compose -f deployment/docker-compose.yml run --rm logsim-cli \
  python /app/evaluation/run_full_evaluation.py
```

### logsim-query (Query Service)

**Dedicated query service**:

```bash
docker-compose -f deployment/docker-compose.yml run --rm logsim-query \
  -c /app/evaluation/compressed/apache.lsc --severity ERROR
```

## Dockerfile

### Base Image
```dockerfile
FROM python:3.11-slim
```

### System Dependencies
- `bash` - Shell for interactive scripts
- `tree` - Directory visualization
- `git` - Version control (optional)

### Python Dependencies
All packages from `requirements.txt`:
- `msgpack>=1.0.0` - Serialization
- `zstandard>=0.21.0` - Compression
- `rich>=13.0.0` - Terminal UI
- `click>=8.1.0` - CLI framework
- `pytest>=7.4.0` - Testing

### Working Directory
```dockerfile
WORKDIR /app
```

### Volume Mounts
```yaml
volumes:
  - ../data:/app/data                    # Input datasets
  - ../evaluation:/app/evaluation        # Outputs
  - ../logsim:/app/logsim               # Source code
  - ../scripts:/app/scripts             # Automation scripts
```

## Makefile

### Build Commands

```bash
# Build Docker image
make build

# Build without cache
make build-no-cache
```

### Run Commands

```bash
# Run interactive CLI
make interactive

# Run bash menu
make interactive-bash

# Run tests
make test

# Run evaluation
make evaluate
```

### Cleanup

```bash
# Remove containers
make clean

# Remove images and volumes
make clean-all
```

## Configuration

### Environment Variables

Set in `docker-compose.yml` or via `.env` file:

```bash
# Python settings
PYTHONUNBUFFERED=1          # Disable output buffering
PYTHONPATH=/app             # Python module path

# Terminal settings
TERM=xterm-256color         # Enable colors

# LogSim settings
MIN_SUPPORT=3               # Template extraction threshold
ZSTD_LEVEL=15              # Compression level (1-22)
MAX_TEMPLATES=1000         # Maximum templates to extract

# Query settings
QUERY_CACHE_SIZE=100       # Query result cache (MB)
ENABLE_INDEXES=true        # Enable columnar indexes
```

### Resource Limits

```yaml
services:
  logsim-cli:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Production Deployment

### 1. Build Production Image

```bash
# Optimize for size
docker build \
  -f deployment/Dockerfile \
  -t logsim:latest \
  --target production \
  .

# Multi-stage build (smaller image)
docker build \
  -f deployment/Dockerfile.multistage \
  -t logsim:slim \
  .
```

### 2. Push to Registry

```bash
# Tag for registry
docker tag logsim:latest ghcr.io/adam-bouafia/logsim:latest

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u adam-bouafia --password-stdin

# Push image
docker push ghcr.io/adam-bouafia/logsim:latest
```

### 3. Deploy to Server

```bash
# Pull on production server
docker pull ghcr.io/adam-bouafia/logsim:latest

# Run with docker-compose
docker-compose -f deployment/docker-compose.prod.yml up -d

# Or with docker run
docker run -d \
  --name logsim-service \
  -v /data/logs:/app/data \
  -v /data/compressed:/app/evaluation/compressed \
  --restart unless-stopped \
  ghcr.io/adam-bouafia/logsim:latest
```

## Volume Management

### Persistent Storage

```yaml
volumes:
  # Named volumes for persistence
  logsim-data:
    driver: local
  logsim-results:
    driver: local

services:
  logsim-cli:
    volumes:
      - logsim-data:/app/data
      - logsim-results:/app/evaluation
```

### Backup Volumes

```bash
# Backup compressed files
docker run --rm \
  -v logsim-results:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/results-$(date +%Y%m%d).tar.gz /data

# Restore from backup
docker run --rm \
  -v logsim-results:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/results-20241127.tar.gz -C /
```

## Networking

### Expose Query Service

```yaml
services:
  logsim-api:
    ports:
      - "8080:8080"
    command: python -m logsim.api.server --host 0.0.0.0 --port 8080
```

### Link Services

```yaml
services:
  logsim-worker:
    depends_on:
      - logsim-db
      - logsim-redis
    networks:
      - logsim-network

networks:
  logsim-network:
    driver: bridge
```

## Monitoring

### Health Checks

```yaml
services:
  logsim-api:
    healthcheck:
      test: ["CMD", "python", "-c", "import logsim; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Logging

```yaml
services:
  logsim-cli:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Resource Monitoring

```bash
# View container stats
docker stats logsim-service

# View logs
docker logs -f logsim-service

# Inspect container
docker inspect logsim-service
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f deployment/docker-compose.yml logs logsim-cli

# Inspect image
docker run --rm -it logsim:latest bash

# Verify volumes
docker volume ls
docker volume inspect logsim-data
```

### Permission Issues

```bash
# Run with user permissions
docker-compose -f deployment/docker-compose.yml run \
  --user $(id -u):$(id -g) \
  logsim-cli compress -i /app/data/datasets/Apache/Apache_full.log
```

### Out of Memory

```bash
# Increase memory limit
docker-compose -f deployment/docker-compose.yml run \
  --memory 8g \
  logsim-cli compress -i /app/data/datasets/OpenStack/OpenStack_full.log
```

### Slow Performance

```bash
# Use tmpfs for temporary data
docker run --rm \
  --tmpfs /tmp:rw,size=2g \
  logsim:latest compress -i /app/data/datasets/Apache/Apache_full.log
```

## Development Mode

### Mount Source Code

```yaml
services:
  logsim-dev:
    volumes:
      - ../logsim:/app/logsim:rw  # Enable hot reload
      - ../tests:/app/tests:rw
    command: pytest /app/tests/ --watch
```

### Interactive Debugging

```bash
# Run with interactive shell
docker-compose -f deployment/docker-compose.yml run \
  --entrypoint bash \
  logsim-cli

# Inside container
python -m pdb -m logsim.cli.commands compress -i /app/data/datasets/Apache/Apache_full.log
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -f deployment/Dockerfile -t logsim:${{ github.sha }} .
      
      - name: Run tests
        run: docker run logsim:${{ github.sha }} pytest /app/logsim/tests/
      
      - name: Push to registry
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker tag logsim:${{ github.sha }} ghcr.io/adam-bouafia/logsim:latest
          docker push ghcr.io/adam-bouafia/logsim:latest
```

## Security

### Scan for Vulnerabilities

```bash
# Using Trivy
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image logsim:latest

# Using Snyk
snyk container test logsim:latest
```

### Best Practices

- ✅ Use specific base image versions
- ✅ Run as non-root user
- ✅ Scan for vulnerabilities regularly
- ✅ Use multi-stage builds
- ✅ Minimize image layers
- ✅ Remove unnecessary dependencies

---

**See parent [README.md](../README.md) for complete project information.**
