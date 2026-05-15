"""
Error Recovery System — Graceful retry logic with exponential backoff.

Features:
  • Automatic retry on API failures
  • Exponential backoff (avoid hammering servers)
  • Circuit breaker pattern (fail fast if service down)
  • Error categorization (retryable vs permanent)
  • Fallback chains (Groq → Gemini → Offline)
"""

import time
import threading
from typing import Callable, Any, Optional, Dict, Tuple
from enum import Enum


class ErrorType(Enum):
    """Categorizes errors for retry decisions."""
    RETRYABLE = "retryable"      # Network, timeouts, rate limits
    PERMANENT = "permanent"      # Auth, syntax, not found
    UNKNOWN = "unknown"          # Unexpected errors


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(self, name: str, failure_threshold: int = 5, timeout: float = 60.0):
        """
        Args:
            name: Service name (e.g., "groq", "gemini")
            failure_threshold: Failures before opening circuit
            timeout: Seconds before attempting reset
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def record_failure(self) -> bool:
        """
        Record a failure. Returns True if circuit should remain closed.
        """
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                print(f"[CircuitBreaker] {self.name} circuit OPENED (failed {self.failure_count}x)")
                return False
            return True
    
    def record_success(self):
        """Reset failure counter on success."""
        with self._lock:
            self.failure_count = 0
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                print(f"[CircuitBreaker] {self.name} circuit CLOSED (recovered)")
    
    def is_available(self) -> bool:
        """Check if circuit is available for requests."""
        with self._lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                # Check if timeout passed
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "HALF_OPEN"
                    print(f"[CircuitBreaker] {self.name} circuit HALF_OPEN (trying recovery)")
                    return True
                return False
            
            return True  # HALF_OPEN
    
    def get_status(self) -> Dict:
        """Get circuit status."""
        with self._lock:
            return {
                "service": self.name,
                "state": self.state,
                "failure_count": self.failure_count,
                "last_failure": self.last_failure_time,
            }


class ErrorRecoveryManager:
    """Manages retries, backoff, and circuit breaking."""
    
    # Categorize errors by exception type and message
    RETRYABLE_ERRORS = {
        "timeout": ErrorType.RETRYABLE,
        "connection": ErrorType.RETRYABLE,
        "rate_limit": ErrorType.RETRYABLE,
        "429": ErrorType.RETRYABLE,  # HTTP 429 Too Many Requests
        "503": ErrorType.RETRYABLE,  # HTTP 503 Service Unavailable
        "temporary": ErrorType.RETRYABLE,
    }
    
    PERMANENT_ERRORS = {
        "authentication": ErrorType.PERMANENT,
        "401": ErrorType.PERMANENT,  # Unauthorized
        "403": ErrorType.PERMANENT,  # Forbidden
        "404": ErrorType.PERMANENT,  # Not Found
        "invalid": ErrorType.PERMANENT,
        "syntax": ErrorType.PERMANENT,
    }
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_config = {
            "max_retries": 3,
            "initial_delay": 0.5,  # seconds
            "max_delay": 10.0,
            "backoff_factor": 2.0,
        }
    
    def categorize_error(self, error: Exception) -> ErrorType:
        """Determine if error is retryable, permanent, or unknown."""
        error_str = str(error).lower()
        
        for keyword, error_type in self.RETRYABLE_ERRORS.items():
            if keyword in error_str:
                return error_type
        
        for keyword, error_type in self.PERMANENT_ERRORS.items():
            if keyword in error_str:
                return error_type
        
        return ErrorType.UNKNOWN
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Decide if operation should be retried."""
        error_type = self.categorize_error(error)
        
        if attempt >= self.retry_config["max_retries"]:
            print(f"[ErrorRecovery] Max retries ({attempt}) reached")
            return False
        
        if error_type == ErrorType.PERMANENT:
            print(f"[ErrorRecovery] Permanent error, not retrying: {error}")
            return False
        
        return True
    
    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        import random
        
        base_delay = self.retry_config["initial_delay"]
        factor = self.retry_config["backoff_factor"]
        max_delay = self.retry_config["max_delay"]
        
        # Exponential: 0.5s, 1s, 2s, 4s...
        delay = min(base_delay * (factor ** attempt), max_delay)
        
        # Add jitter (±20%)
        jitter = delay * 0.2 * (random.random() - 0.5)
        return max(delay + jitter, 0.1)
    
    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(service)
        return self.circuit_breakers[service]
    
    def retry_with_backoff(
        self,
        func: Callable,
        service_name: str,
        args: Tuple = (),
        kwargs: Dict = None,
    ) -> Optional[Any]:
        """
        Execute function with automatic retry and exponential backoff.
        
        Args:
            func: Function to execute
            service_name: Name of service for circuit breaking
            args: Positional arguments for func
            kwargs: Keyword arguments for func
        
        Returns:
            Function result, or None if all retries failed
        """
        if kwargs is None:
            kwargs = {}
        
        circuit_breaker = self.get_circuit_breaker(service_name)
        
        # Check circuit breaker first
        if not circuit_breaker.is_available():
            print(f"[ErrorRecovery] Circuit breaker OPEN for {service_name}, skipping request")
            return None
        
        last_error = None
        
        for attempt in range(self.retry_config["max_retries"] + 1):
            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            
            except Exception as e:
                last_error = e
                error_type = self.categorize_error(e)
                
                print(f"[ErrorRecovery] {service_name} attempt {attempt+1} failed: {error_type.value}")
                print(f"  Error: {str(e)[:100]}")
                
                # Record failure in circuit breaker
                circuit_breaker.record_failure()
                
                # Check if we should retry
                if not self.should_retry(e, attempt):
                    return None
                
                # Calculate backoff and sleep
                if attempt < self.retry_config["max_retries"]:
                    backoff = self.calculate_backoff(attempt)
                    print(f"[ErrorRecovery] Retrying after {backoff:.2f}s...")
                    time.sleep(backoff)
        
        print(f"[ErrorRecovery] All retries exhausted for {service_name}")
        return None
    
    def get_status(self) -> Dict:
        """Get status of all circuit breakers."""
        return {
            breaker_name: breaker.get_status()
            for breaker_name, breaker in self.circuit_breakers.items()
        }


# Global instance
ERROR_RECOVERY = ErrorRecoveryManager()
