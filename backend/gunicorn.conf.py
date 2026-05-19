# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5001")
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", str(multiprocessing.cpu_count() * 2 + 1)))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "300"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Restart workers after this many requests, to prevent memory leaks
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Preload the application before forking worker processes
preload_app = os.getenv("GUNICORN_PRELOAD_APP", "true").lower() == "true"

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # Log to stdout by default
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")    # Log to stderr by default
loglevel = os.getenv("GUNICORN_LOG_LEVEL", os.getenv("LOG_LEVEL", "info")).lower()
access_log_format = os.getenv("GUNICORN_ACCESS_LOG_FORMAT", 
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(T)s')

# Process naming
proc_name = os.getenv("GUNICORN_PROC_NAME", "sera-backend")

# Graceful timeout for worker restart
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "300"))

# Security
limit_request_line = int(os.getenv("GUNICORN_LIMIT_REQUEST_LINE", "4094"))
limit_request_fields = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELDS", "100"))
limit_request_field_size = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELD_SIZE", "8190"))

# Performance optimizations
# Enable threading for better I/O handling with Redis/AWS calls
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# SSL/TLS Configuration (for production with reverse proxy)
keyfile = os.getenv("GUNICORN_KEYFILE")
certfile = os.getenv("GUNICORN_CERTFILE")
ca_certs = os.getenv("GUNICORN_CA_CERTS")
ssl_version = os.getenv("GUNICORN_SSL_VERSION")

# Forwarded headers (when behind reverse proxy)
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")

# Environment variables to pass to workers
current_dir = os.path.dirname(os.path.abspath(__file__))
raw_env = [
    f"PYTHONPATH={current_dir}",
    f"FLASK_ENV={os.getenv('FLASK_ENV', 'production')}",
    f"FLASK_DEBUG={os.getenv('FLASK_DEBUG', 'false')}",
]

# Hooks for monitoring and logging
def on_starting(server):
    """Hook called before the master process is initialized."""
    server.log.info("Starting SERA backend server")

def on_reload(server):
    """Hook called during reload.""" 
    server.log.info("Reloading SERA backend server")

def worker_int(worker):
    """Hook called when a worker receives SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received interrupt signal")

def pre_fork(server, worker):
    """Hook called before worker process is forked."""
    server.log.debug(f"Forking worker {worker.pid}")

def post_fork(server, worker):
    """Hook called after worker process is forked."""
    server.log.debug(f"Worker {worker.pid} forked successfully")

def worker_abort(worker):
    """Hook called when worker process is aborted."""
    worker.log.error(f"Worker {worker.pid} aborted")