import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any


class TransactionLogger:

    DEFAULT_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    DEFAULT_DATEFMT = '%Y-%m-%d %H:%M:%S'

    def __init__(
            self,
            name: str = "bank_transactions",
            log_dir: str = "logs",
            log_file: str = "transactions.log",
            max_bytes: int = 10 * 1024 * 1024,  # 10 MB
            backup_count: int = 5,
            level: int = logging.INFO,
            format_str: Optional[str] = None,
            datefmt: Optional[str] = None,
            extra_fields: Optional[Dict[str, Any]] = None
    ):
        self.logger = self._setup_logger(
            name=name,
            log_dir=log_dir,
            log_file=log_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
            level=level,
            format_str=format_str or self.DEFAULT_FORMAT,
            datefmt=datefmt or self.DEFAULT_DATEFMT,
            extra_fields=extra_fields
        )

    def _setup_logger(
            self,
            name: str,
            log_dir: str,
            log_file: str,
            max_bytes: int,
            backup_count: int,
            level: int,
            format_str: str,
            datefmt: str,
            extra_fields: Optional[Dict[str, Any]]
    ) -> logging.Logger:

        Path(log_dir).mkdir(exist_ok=True)

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(format_str, datefmt)

        file_handler = RotatingFileHandler(
            filename=Path(log_dir) / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)

        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        if extra_fields:
            for key, value in extra_fields.items():
                setattr(logger, key, value)

        return logger

#if __name__ == "__main__":
#    TransactionLogger().logger.info("Логгер инициализирован")