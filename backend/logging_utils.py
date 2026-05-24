"""
Logging utilities untuk concurrent job scraping
Setiap job_id mendapat logger unik dengan file handler terpisah
"""
import logging
import os
from pathlib import Path
from datetime import datetime

# Global job loggers cache
_job_loggers = {}


def get_job_logger(job_id: int, platform: str, keyword: str) -> logging.Logger:
    """
    Dapatkan atau buat logger unik untuk setiap job.
    Setiap job punya file log terpisah: logs/jobs/job_{job_id}_{platform}.log
    
    Args:
        job_id: Integer job ID
        platform: Platform name (seek, jora, indeed)
        keyword: Job keyword untuk log filename
        
    Returns:
        logging.Logger instance yang ready untuk write ke file & console
    """
    if job_id in _job_loggers:
        return _job_loggers[job_id]
    
    # Create logger dengan unique name
    logger_name = f"job_{job_id}"
    logger = logging.getLogger(logger_name)
    
    # Clear handlers kalo reuse
    if logger.handlers:
        logger.handlers.clear()
    
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Jangan propagate ke root logger agar tidak tercampur
    
    # Setup file handler dengan unique path
    log_dir = Path("logs/jobs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Filename: job_12345_seek_python_developer_20260417_143022.log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keyword_clean = keyword.replace(" ", "_").lower()[:20] if keyword else "all"
    log_file = log_dir / f"job_{job_id}_{platform}_{keyword_clean}_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Optional: console handler (biar tidak orphan)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        f'[job:{job_id}] [%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    _job_loggers[job_id] = logger
    return logger


def cleanup_job_logger(job_id: int):
    """Cleanup logger untuk job (close file handler)"""
    if job_id in _job_loggers:
        logger = _job_loggers[job_id]
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        del _job_loggers[job_id]


def get_log_file_path(job_id: int) -> str | None:
    """Dapatkan path file log untuk job_id"""
    if job_id in _job_loggers:
        for handler in _job_loggers[job_id].handlers:
            if isinstance(handler, logging.FileHandler):
                return handler.baseFilename
    return None
