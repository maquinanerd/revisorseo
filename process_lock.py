
import os
import time
import logging

logger = logging.getLogger(__name__)

class ProcessLock:
    def __init__(self, lock_file="seo_optimizer.lock"):
        self.lock_file = lock_file
        self.locked = False
    
    def acquire(self) -> bool:
        """Acquire the process lock."""
        try:
            if os.path.exists(self.lock_file):
                # Check if lock is stale (older than 2 hours)
                lock_age = time.time() - os.path.getmtime(self.lock_file)
                if lock_age > 7200:  # 2 hours
                    logger.warning("Removing stale lock file")
                    os.remove(self.lock_file)
                else:
                    logger.warning("Another instance is already running")
                    return False
            
            # Create lock file
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            self.locked = True
            logger.info("Process lock acquired")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def release(self):
        """Release the process lock."""
        try:
            if self.locked and os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                self.locked = False
                logger.info("Process lock released")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
    
    def __enter__(self):
        return self.acquire()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
