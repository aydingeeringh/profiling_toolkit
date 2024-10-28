I'll revise the README to be more streamlined, letting the setup script handle the dependency checks and installations. Here's the simplified version:

# Project Setup

This README provides instructions for setting up a data pipeline using Airbyte for data ingestion, PostgreSQL for storage, and Evidence.dev for data profiling.

## Prerequisites

The setup script will check for and install required dependencies. If Docker is not installed, you'll need to install it first:

- [Docker Desktop for Windows/Mac](https://www.docker.com/products/docker-desktop/)
- [Docker Engine for Linux](https://docs.docker.com/engine/install/)

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
- Check and install required dependencies (Git, Python, Node.js)
- Create a Python virtual environment
- Install Airbyte
- Start PostgreSQL in Docker

### 3. Configure Airbyte

1. Access Airbyte UI at `http://localhost:8000`
   - Use the credentials displayed in terminal
   - If needed, run `abctl local credentials` to see credentials again

2. Configure Your Source:
   - Click "Sources" in the left sidebar
   - Select your data source type
   - Enter connection details
   - Test and save the connection

3. Configure PostgreSQL Destination:
   - Click "Destinations"
   - Select "PostgreSQL"
   - Enter connection details:
     ```
     Host: host.docker.internal
     Port: 5432
     Database: postgres
     Username: postgres
     Password: postgres
     ```
   - Test and save the connection

4. Create Connection:
   - Go to "Connections""
   - Select your source and destination
   - Configure sync settings
   - Start the sync

### 4. Run Tasks

With the virtual environment activated (it should show `.env` in the terminal prompt), run the following tasks:

```bash
# Run all tasks
invoke all

# Or run individual tasks:
invoke setup     # Install npm dependencies (dependencies for profiling report ui)
invoke profile   # Run data profiling (queries the data loaded into PostgreSQL by Airbyte)
invoke sources   # Generate source files (Caches the profiling results so the report can display the data)
invoke report    # Start Evidence.dev report (Starts the report UI)
```

### 5. View Reports and Logs

#### Access Applications
- Evidence.dev Report: `http://localhost:3000`
- Airbyte UI: `http://localhost:8000`

#### View Docker Logs
Using Docker Desktop:
1. Open Docker Desktop
2. Click "Containers"
3. Click container name to view:
   - Live logs
   - Performance metrics
   - Container details

Using Command Line:
```bash
# View PostgreSQL logs
docker compose logs postgres

# View Airbyte logs
docker compose logs airbyte-abctl-control-plane

# Follow logs in real-time
docker compose logs -f [container_name]
```

### Maintenance

#### Stop Services
```bash
# Stop PostgreSQL and Airbyte
docker compose down

# Stop Evidence.dev (in the running terminal)
Ctrl+C
```

#### Restart Services
```bash
# Restart all containers
docker compose restart

# Restart specific container
docker compose restart postgres
docker compose restart airbyte
```

#### Update Data
1. Trigger sync in Airbyte UI
2. Run `invoke profile` to update profiling
3. Evidence.dev report will auto-update if running, otherwise run `invoke sources` and `invoke report`

## Troubleshooting

- **Docker Issues**: Ensure Docker Desktop is running
- **Airbyte Credentials**: Run `abctl local credentials`
- **Container Status**: Run `docker compose ps`
- **Detailed Logs**: Run `docker compose logs [container_name]`
- **Setup Issues**: Check `setup.sh` output for specific error messages