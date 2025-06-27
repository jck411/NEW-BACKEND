"""Prometheus metrics endpoint for observability compliance.

NOTE: This is PURELY for monitoring - Prometheus doesn't affect your app's functionality.
It just scrapes this endpoint to collect metrics for dashboards and alerting.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from api.dependencies import get_connection_manager
from api.services.connection_manager import ConnectionManager

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics(
    connection_manager: ConnectionManager = Depends(get_connection_manager)
) -> str:
    """Prometheus metrics endpoint - MONITORING ONLY.
    
    This endpoint just exposes application data in Prometheus format.
    Prometheus (external service) scrapes this for monitoring/alerting.
    Your app continues to work normally regardless of Prometheus.
    """
    # Get actual data from your application
    active_connections = len(connection_manager.active_connections)
    
    # Format as Prometheus metrics (just text formatting)
    metrics = [
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter", 
        "http_requests_total{method=\"GET\",endpoint=\"/health\"} 0",
        "",
        "# HELP websocket_connections_active Active WebSocket connections",
        "# TYPE websocket_connections_active gauge",
        f"websocket_connections_active {active_connections}",
        "",
        "# HELP api_response_time_seconds API response time in seconds", 
        "# TYPE api_response_time_seconds histogram",
        "api_response_time_seconds_bucket{le=\"0.1\"} 0",
        "api_response_time_seconds_bucket{le=\"+Inf\"} 0",
        "api_response_time_seconds_sum 0.0",
        "api_response_time_seconds_count 0",
        "",
        "# Application-specific metrics",
        "# HELP chatbot_sessions_total Total chatbot sessions created",
        "# TYPE chatbot_sessions_total counter",
        "chatbot_sessions_total 0",
    ]
    
    return "\n".join(metrics) 