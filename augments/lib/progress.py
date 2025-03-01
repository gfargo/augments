"""
Progress indicators and loading animations for async operations.
"""
import sys
import threading
import time
from concurrent.futures import Future
from enum import Enum
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar, Union

class LoaderStyle(Enum):
    DOTS = "dots"         # Simple dots: ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏
    ARROW = "arrow"       # Rotating arrow: ←↖↑↗→↘↓↙
    BAR = "bar"          # Progress bar: █▉▊▋▌▍▎▏
    PULSE = "pulse"      # Pulsing circle: ◐◓◑◒
    MOON = "moon"        # Moon phases: 🌑🌒🌓🌔🌕🌖🌗🌘
    BRAILLE = "braille"  # Braille pattern: ⣾⣽⣻⢿⡿⣟⣯⣷

# Animation frames for different styles
FRAMES = {
    LoaderStyle.DOTS: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    LoaderStyle.ARROW: ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    LoaderStyle.BAR: ["█", "▉", "▊", "▋", "▌", "▍", "▎", "▏"],
    LoaderStyle.PULSE: ["◐", "◓", "◑", "◒"],
    LoaderStyle.MOON: ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"],
    LoaderStyle.BRAILLE: ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
}

class ProgressTracker:
    """Tracks progress of multiple operations."""
    
    def __init__(self):
        self.operations: List[str] = []
        self.current: Optional[str] = None
        self._stop = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start(self, message: str, style: LoaderStyle = LoaderStyle.DOTS):
        """Start tracking a new operation."""
        with self._lock:
            self.operations.append(message)
            self.current = message
            if not self._thread:
                self._stop = False
                self._thread = threading.Thread(target=self._animate, args=(style,))
                self._thread.daemon = True
                self._thread.start()
    
    def stop(self, success: bool = True):
        """Stop tracking the current operation."""
        with self._lock:
            if self.current:
                symbol = "✓" if success else "✗"
                sys.stdout.write(f"\r{symbol} {self.current}\n")
                sys.stdout.flush()
                self.operations.remove(self.current)
                self.current = self.operations[-1] if self.operations else None
            
            if not self.operations:
                self._stop = True
                if self._thread:
                    self._thread.join()
                    self._thread = None
    
    def _animate(self, style: LoaderStyle):
        """Animate the loading indicator."""
        frames = FRAMES[style]
        i = 0
        while not self._stop:
            with self._lock:
                if self.current:
                    frame = frames[i % len(frames)]
                    sys.stdout.write(f"\r{frame} {self.current}")
                    sys.stdout.flush()
            time.sleep(0.1)
            i += 1

# Global progress tracker
_progress = ProgressTracker()

T = TypeVar('T')

def with_progress(message: str, style: LoaderStyle = LoaderStyle.DOTS) -> Callable:
    """
    Decorator to show progress while executing a function.
    
    Args:
        message: Message to show during execution
        style: Animation style to use
    
    Example:
        @with_progress("Downloading file...")
        def download_file(url: str) -> bool:
            # Function implementation
            return True
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            _progress.start(message, style)
            try:
                result = func(*args, **kwargs)
                if isinstance(result, Future):
                    result = result.result()
                _progress.stop(success=True)
                return result
            except Exception as e:
                _progress.stop(success=False)
                raise e
        return wrapper
    return decorator

def track_progress(message: str, style: LoaderStyle = LoaderStyle.DOTS) -> 'ProgressContext':
    """
    Context manager to track progress of a block of code.
    
    Args:
        message: Message to show during execution
        style: Animation style to use
    
    Example:
        with track_progress("Processing data..."):
            process_data()
    """
    class ProgressContext:
        def __enter__(self):
            _progress.start(message, style)
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            _progress.stop(success=exc_type is None)
            return False  # Don't suppress exceptions
    
    return ProgressContext()

def show_parallel_progress(operations: List[tuple[str, Callable[[], Any]]]) -> List[Any]:
    """
    Execute multiple operations in parallel with progress tracking.
    
    Args:
        operations: List of (message, function) tuples to execute
    
    Returns:
        List of results from each operation
    
    Example:
        results = show_parallel_progress([
            ("Downloading file 1...", lambda: download_file(url1)),
            ("Downloading file 2...", lambda: download_file(url2))
        ])
    """
    from concurrent.futures import ThreadPoolExecutor
    results = []
    
    with ThreadPoolExecutor() as executor:
        futures = []
        for msg, func in operations:
            _progress.start(msg)
            future = executor.submit(func)
            future.message = msg  # type: ignore
            futures.append(future)
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
                _progress.stop(success=True)
            except Exception as e:
                _progress.stop(success=False)
                print(f"Error in {future.message}: {e}")  # type: ignore
                results.append(None)
    
    return results