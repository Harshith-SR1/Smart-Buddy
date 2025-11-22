"""Metrics collection and monitoring for Smart Buddy.

Tracks performance, usage, and quality metrics for observability.
Critical for Top 3 - demonstrates production systems thinking.
"""
import time
import json
from typing import Dict, List, Optional
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
import threading


class MetricsCollector:
    """Production-grade metrics collection with percentile tracking.
    
    Tracks:
    - Request latency (p50, p95, p99, p999)
    - Token usage per mode
    - Error rates
    - Intent distribution
    - Memory operations
    - Sentiment trends
    """
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.lock = threading.Lock()
        
        # Latency tracking (milliseconds)
        self.latencies = deque(maxlen=window_size)
        self.latencies_by_mode = defaultdict(lambda: deque(maxlen=window_size))
        
        # Token tracking
        self.tokens_used = defaultdict(int)  # {mode: count}
        self.total_tokens = 0
        
        # Request counts
        self.request_count = 0
        self.requests_by_mode = defaultdict(int)
        self.requests_by_intent = defaultdict(int)
        
        # Error tracking
        self.error_count = 0
        self.errors_by_type = defaultdict(int)
        
        # Sentiment tracking
        self.sentiment_counts = defaultdict(int)  # {positive/neutral/negative: count}
        
        # Memory operations
        self.memory_reads = 0
        self.memory_writes = 0
        
        # Start time
        self.start_time = time.time()
        
        # Persistence
        self.metrics_file = Path("metrics_log.jsonl")
    
    def record_request(
        self,
        mode: str,
        intent: str,
        latency_ms: float,
        tokens: int = 0,
        error: Optional[str] = None,
        sentiment: Optional[str] = None
    ):
        """Record a request with all metadata."""
        with self.lock:
            self.request_count += 1
            self.requests_by_mode[mode] += 1
            self.requests_by_intent[intent] += 1
            
            # Latency
            self.latencies.append(latency_ms)
            self.latencies_by_mode[mode].append(latency_ms)
            
            # Tokens
            if tokens > 0:
                self.tokens_used[mode] += tokens
                self.total_tokens += tokens
            
            # Errors
            if error:
                self.error_count += 1
                self.errors_by_type[error] += 1
            
            # Sentiment
            if sentiment:
                self.sentiment_counts[sentiment] += 1
            
            # Log to file
            self._append_log({
                'timestamp': datetime.now().isoformat(),
                'mode': mode,
                'intent': intent,
                'latency_ms': latency_ms,
                'tokens': tokens,
                'error': error,
                'sentiment': sentiment
            })
    
    def record_memory_op(self, operation: str):
        """Track memory read/write operations."""
        with self.lock:
            if operation == 'read':
                self.memory_reads += 1
            elif operation == 'write':
                self.memory_writes += 1
    
    def get_summary(self) -> Dict:
        """Get current metrics summary."""
        with self.lock:
            uptime_seconds = time.time() - self.start_time
            
            summary = {
                'uptime_seconds': round(uptime_seconds, 2),
                'uptime_hours': round(uptime_seconds / 3600, 2),
                'total_requests': self.request_count,
                'requests_per_minute': round(self.request_count / (uptime_seconds / 60), 2) if uptime_seconds > 0 else 0,
                'error_rate': round(self.error_count / self.request_count * 100, 2) if self.request_count > 0 else 0,
                'total_tokens': self.total_tokens,
                'tokens_per_request': round(self.total_tokens / self.request_count, 2) if self.request_count > 0 else 0,
                'latency': self._calculate_percentiles(list(self.latencies)),
                'latency_by_mode': {
                    mode: self._calculate_percentiles(list(latencies))
                    for mode, latencies in self.latencies_by_mode.items()
                },
                'requests_by_mode': dict(self.requests_by_mode),
                'requests_by_intent': dict(self.requests_by_intent),
                'tokens_by_mode': dict(self.tokens_used),
                'errors': {
                    'total': self.error_count,
                    'by_type': dict(self.errors_by_type)
                },
                'sentiment': dict(self.sentiment_counts),
                'memory': {
                    'reads': self.memory_reads,
                    'writes': self.memory_writes
                }
            }
            
            return summary
    
    def get_dashboard_html(self) -> str:
        """Generate simple HTML dashboard for /metrics endpoint."""
        summary = self.get_summary()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Smart Buddy Metrics</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-label {{ color: #888; font-size: 14px; }}
        .metric-value {{ color: #333; font-size: 24px; font-weight: bold; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .bad {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Smart Buddy Metrics Dashboard</h1>
        
        <div class="card">
            <h2>📊 Overview</h2>
            <div class="metric">
                <div class="metric-label">Uptime</div>
                <div class="metric-value">{summary['uptime_hours']}h</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value">{summary['total_requests']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Requests/min</div>
                <div class="metric-value">{summary['requests_per_minute']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Error Rate</div>
                <div class="metric-value {'good' if summary['error_rate'] < 1 else 'warning' if summary['error_rate'] < 5 else 'bad'}">{summary['error_rate']}%</div>
            </div>
        </div>
        
        <div class="card">
            <h2>⚡ Latency (ms)</h2>
            <div class="metric">
                <div class="metric-label">p50 (median)</div>
                <div class="metric-value">{summary['latency'].get('p50', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">p95</div>
                <div class="metric-value">{summary['latency'].get('p95', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">p99</div>
                <div class="metric-value">{summary['latency'].get('p99', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">p999</div>
                <div class="metric-value">{summary['latency'].get('p999', 0)}</div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 Mode Distribution</h2>
            <table>
                <tr><th>Mode</th><th>Requests</th><th>Tokens</th><th>Avg Latency</th></tr>
                {''.join(f"<tr><td>{mode}</td><td>{count}</td><td>{summary['tokens_by_mode'].get(mode, 0)}</td><td>{summary['latency_by_mode'].get(mode, {}).get('p50', 0)} ms</td></tr>" for mode, count in summary['requests_by_mode'].items())}
            </table>
        </div>
        
        <div class="card">
            <h2>🎭 Intent Classification</h2>
            <table>
                <tr><th>Intent</th><th>Count</th><th>Percentage</th></tr>
                {''.join(f"<tr><td>{intent}</td><td>{count}</td><td>{round(count/summary['total_requests']*100, 1) if summary['total_requests'] > 0 else 0}%</td></tr>" for intent, count in summary['requests_by_intent'].items())}
            </table>
        </div>
        
        <div class="card">
            <h2>💾 Memory Operations</h2>
            <div class="metric">
                <div class="metric-label">Reads</div>
                <div class="metric-value">{summary['memory']['reads']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Writes</div>
                <div class="metric-value">{summary['memory']['writes']}</div>
            </div>
        </div>
        
        <p style="text-align: center; color: #888; margin-top: 40px;">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
        """
        return html
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate latency percentiles."""
        if not values:
            return {'p50': 0, 'p95': 0, 'p99': 0, 'p999': 0, 'mean': 0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'p50': round(sorted_values[int(n * 0.5)], 2),
            'p95': round(sorted_values[int(n * 0.95)], 2),
            'p99': round(sorted_values[int(n * 0.99)], 2) if n >= 100 else round(sorted_values[-1], 2),
            'p999': round(sorted_values[int(n * 0.999)], 2) if n >= 1000 else round(sorted_values[-1], 2),
            'mean': round(sum(sorted_values) / n, 2)
        }
    
    def _append_log(self, entry: Dict):
        """Append metric entry to log file."""
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception:
            pass  # Silent fail for logging


# Global instance
metrics = MetricsCollector()
