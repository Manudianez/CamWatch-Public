from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)]
)

logger = logging.getLogger("StripWatch")

# httpx anota cada petición; con consultas cada pocos segundos es solo ruido.
logging.getLogger("httpx").setLevel(logging.WARNING)
