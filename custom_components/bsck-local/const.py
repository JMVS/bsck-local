"""Constants for BSCK."""

DOMAIN = "bsck-local"

# Configuration
CONF_AC_NAME = "ac_name"
CONF_IP_ADDRESS = "ip_address"
CONF_UDP_PORT = "udp_port"
CONF_LOCAL_PORT = "local_port"

# Default values
DEFAULT_UDP_PORT = 20910
DEFAULT_LOCAL_PORT = 20911
DEFAULT_POLLING_INTERVAL = 60  # 1 minuto

# BGH Modes mapping
MODE_OFF = 0
MODE_COOL = 1
MODE_HEAT = 2
MODE_DRY = 3
MODE_FAN_ONLY = 4
MODE_AUTO = 254

# Protocol constants
COMMAND_HEADER = bytes.fromhex("00000000000000accf23aa3190f60001610402000080")
STATUS_REQUEST = bytes.fromhex("00000000000000accf23aa3190590001e4")

# Fan speeds
FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 3
FAN_SPEED_AUTO = 254
