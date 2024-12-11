import logging, os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from colorama import Back, Style, init, Fore
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    def __init__(self):
        self.COLOR_CODES = {
            logging.DEBUG: Fore.BLUE,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA,
        }
        log_fmt = f"{Back.BLACK}[%(asctime)s][%(filename)s:%(lineno)d]{Style.RESET_ALL} %(levelname)s - %(message)s"
        date_fmt = "%Y-%m-%d %H:%M"
        super().__init__(log_fmt, date_fmt)
    
    def format(self, record):
        record.levelname = f"{self.COLOR_CODES.get(record.levelno, '')}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


class CustomLogger(logging.Logger):
    def __init__(self, name, level=logging.DEBUG):
        super().__init__(name, level)
        ch = logging.StreamHandler()
        ch.setFormatter(ColoredFormatter())
        self.addHandler(ch)

        
if "__main__" == __name__:
    logger = CustomLogger("test")
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")