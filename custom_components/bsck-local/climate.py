"""Climate platform for BSCK."""
import asyncio
import logging
import socket
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_MEDIUM,
    FAN_LOW,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    CONF_AC_NAME,
    CONF_IP_ADDRESS,
    CONF_UDP_PORT,
    CONF_LOCAL_PORT,
    DEFAULT_UDP_PORT,
    DEFAULT_LOCAL_PORT,
    DEFAULT_POLLING_INTERVAL,
    MODE_OFF,
    MODE_COOL,
    MODE_HEAT,
    MODE_DRY,
    MODE_FAN_ONLY,
    MODE_AUTO,
    COMMAND_HEADER,
    STATUS_REQUEST,
    FAN_SPEED_MIN,
    FAN_SPEED_MAX,
)

_LOGGER = logging.getLogger(__name__)

# Mapeo de modos BGH a HVAC
MAP_MODE_HVAC_TO_BGH = {
    HVACMode.OFF: MODE_OFF,
    HVACMode.COOL: MODE_COOL,
    HVACMode.HEAT: MODE_HEAT,
    HVACMode.DRY: MODE_DRY,
    HVACMode.FAN_ONLY: MODE_FAN_ONLY,
    HVACMode.AUTO: MODE_AUTO,
}

MAP_MODE_BGH_TO_HVAC = {v: k for k, v in MAP_MODE_HVAC_TO_BGH.items()}

# Mapeo de velocidades de ventilador
MAP_FAN_MODE_TO_SPEED = {
    FAN_LOW: 1,
    FAN_MEDIUM: 2,
    FAN_HIGH: 3,
    FAN_AUTO: 254,
}

MAP_FAN_SPEED_TO_MODE = {v: k for k, v in MAP_FAN_MODE_TO_SPEED.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BGH climate entity from a config entry."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    
    climate = BGHClimate(
        name=config.get(CONF_AC_NAME),
        ip_address=config.get(CONF_IP_ADDRESS),
        udp_port=config.get(CONF_UDP_PORT, DEFAULT_UDP_PORT),
        local_port=config.get(CONF_LOCAL_PORT, DEFAULT_LOCAL_PORT),
    )
    
    async_add_entities([climate], True)


class BGHClimate(ClimateEntity):
    """Representation of a BGH AC controlled via UDP."""

    def __init__(self, name: str, ip_address: str, udp_port: int, local_port: int):
        """Initialize the climate device."""
        self._attr_name = name
        self._attr_unique_id = f"bgh_ac_{name.lower().replace(' ', '_')}"
        
        self._ip_address = ip_address
        self._udp_port = udp_port
        self._local_port = local_port
        
        # Modos HVAC soportados
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.AUTO,
        ]
        self._attr_hvac_mode = HVACMode.OFF
        
        # Modos de ventilador soportados
        self._attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
        self._attr_fan_mode = FAN_AUTO
        
        # Configuración de temperatura
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_current_temperature = None
        self._attr_target_temperature = 24.0
        self._attr_min_temp = 17.0
        self._attr_max_temp = 30.0
        self._attr_target_temperature_step = 0.5
        
        # Características soportadas
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
        )
        
        # Estado interno
        self._fan_speed = 254  # Auto por defecto
        self._current_mode = MODE_OFF
        
        # Socket UDP
        self._socket = None
        self._remove_interval = None
        self._available = True

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        # Crear socket UDP
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setblocking(False)
            self._socket.bind(("0.0.0.0", self._local_port))
            _LOGGER.info(
                f"[{self._attr_name}] Socket UDP creado en puerto {self._local_port}"
            )
        except Exception as e:
            _LOGGER.error(
                f"[{self._attr_name}] Error al crear socket UDP en puerto {self._local_port}: {e}"
            )
            self._available = False
            return
        
        # Iniciar polling cada 1 minuto
        self._remove_interval = async_track_time_interval(
            self.hass,
            self._async_update,
            timedelta(seconds=DEFAULT_POLLING_INTERVAL),
        )
        
        # Primera actualización inmediata
        await self._async_update()

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed."""
        if self._remove_interval:
            self._remove_interval()
        
        if self._socket:
            self._socket.close()

    async def _async_update(self, now=None):
        """Request status update from AC."""
        if not self._socket:
            return
            
        try:
            await self.hass.async_add_executor_job(
                self._socket.sendto,
                STATUS_REQUEST,
                (self._ip_address, self._udp_port),
            )
            
            # Intentar recibir respuesta (timeout 2 segundos)
            loop = asyncio.get_event_loop()
            data = await asyncio.wait_for(
                loop.run_in_executor(None, self._receive_data),
                timeout=2.0,
            )
            
            if data:
                self._parse_status(data)
                self._available = True
                self.async_write_ha_state()
            else:
                _LOGGER.debug(f"[{self._attr_name}] Sin respuesta del dispositivo")
                
        except asyncio.TimeoutError:
            _LOGGER.debug(
                f"[{self._attr_name}] Timeout esperando respuesta de {self._ip_address}"
            )
            self._available = False
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"[{self._attr_name}] Error al actualizar: {e}")
            self._available = False
            self.async_write_ha_state()

    def _receive_data(self):
        """Receive UDP data (blocking call)."""
        try:
            data, _ = self._socket.recvfrom(1024)
            return data
        except socket.timeout:
            return None
        except Exception as e:
            _LOGGER.debug(f"[{self._attr_name}] Error recibiendo datos: {e}")
            return None

    def _parse_status(self, data: bytes):
        """Parse status data from AC."""
        if len(data) < 25:
            _LOGGER.warning(
                f"[{self._attr_name}] Datos incompletos recibidos: {len(data)} bytes"
            )
            return
        
        try:
            # Parsear según protocolo BGH
            mode = data[18]
            fan_speed = data[19]
            temp1 = data[21]
            temp2 = data[22]
            tempset1 = data[23]
            tempset2 = data[24]
            
            # Temperatura actual (en décimas de grado)
            current_temp = ((temp2 * 256) + temp1) / 100.0
            if 0 <= current_temp <= 50:  # Validación
                self._attr_current_temperature = round(current_temp, 1)
            
            # Temperatura objetivo (en décimas de grado)
            target_temp = ((tempset2 * 256) + tempset1) / 100.0
            if self._attr_min_temp <= target_temp <= self._attr_max_temp:
                self._attr_target_temperature = round(target_temp, 1)
            
            # Modo de operación
            self._current_mode = mode
            if mode in MAP_MODE_BGH_TO_HVAC:
                self._attr_hvac_mode = MAP_MODE_BGH_TO_HVAC[mode]
            else:
                _LOGGER.warning(f"[{self._attr_name}] Modo desconocido: {mode}")
            
            # Velocidad ventilador
            if fan_speed in MAP_FAN_SPEED_TO_MODE:
                self._fan_speed = fan_speed
                self._attr_fan_mode = MAP_FAN_SPEED_TO_MODE[fan_speed]
            elif FAN_SPEED_MIN <= fan_speed <= FAN_SPEED_MAX:
                self._fan_speed = fan_speed
                self._attr_fan_mode = MAP_FAN_SPEED_TO_MODE.get(fan_speed, FAN_MEDIUM)
            
            _LOGGER.debug(
                f"[{self._attr_name}] Estado actualizado - "
                f"Modo: {self._attr_hvac_mode}, "
                f"Fan: {self._attr_fan_mode}, "
                f"Temp: {self._attr_current_temperature}°C, "
                f"Target: {self._attr_target_temperature}°C"
            )
            
        except Exception as e:
            _LOGGER.error(f"[{self._attr_name}] Error al parsear datos: {e}")

    async def _send_command(self, set_temperature: bool = False):
        """Send command to AC."""
        if not self._socket:
            _LOGGER.error(f"[{self._attr_name}] Socket no disponible")
            return
            
        try:
            cmd = bytearray(COMMAND_HEADER)
            cmd[17] = self._current_mode
            cmd[18] = self._fan_speed
            
            # Si se debe cambiar temperatura, modificar los bytes correspondientes
            if set_temperature and self._attr_target_temperature:
                temp_value = int(self._attr_target_temperature * 100)
                cmd[23] = temp_value & 0xFF  # Byte bajo
                cmd[24] = (temp_value >> 8) & 0xFF  # Byte alto
            
            await self.hass.async_add_executor_job(
                self._socket.sendto,
                bytes(cmd),
                (self._ip_address, self._udp_port),
            )
            
            _LOGGER.debug(
                f"[{self._attr_name}] Comando enviado - "
                f"Modo: {self._current_mode}, "
                f"Fan: {self._fan_speed}, "
                f"Temp: {self._attr_target_temperature if set_temperature else 'sin cambio'}°C"
            )
            
            # Solicitar estado actualizado después de 1 segundo
            await asyncio.sleep(1)
            await self._async_update()
            
        except Exception as e:
            _LOGGER.error(f"[{self._attr_name}] Error al enviar comando: {e}")
            self._available = False
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning(
                f"[{self._attr_name}] Modo HVAC no soportado: {hvac_mode}"
            )
            return
            
        if hvac_mode in MAP_MODE_HVAC_TO_BGH:
            self._current_mode = MAP_MODE_HVAC_TO_BGH[hvac_mode]
            self._attr_hvac_mode = hvac_mode
            await self._send_command()
        else:
            _LOGGER.error(
                f"[{self._attr_name}] No se pudo mapear modo HVAC: {hvac_mode}"
            )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        
        if temperature is None:
            return
            
        if not (self._attr_min_temp <= temperature <= self._attr_max_temp):
            _LOGGER.warning(
                f"[{self._attr_name}] Temperatura fuera de rango: {temperature}°C "
                f"(rango: {self._attr_min_temp}-{self._attr_max_temp}°C)"
            )
            return
        
        self._attr_target_temperature = round(temperature, 1)
        
        # Enviar comando con cambio de temperatura
        await self._send_command(set_temperature=True)

    async def async_set_fan_mode(self, fan_mode: str):
        """Set new target fan mode."""
        if fan_mode not in self._attr_fan_modes:
            _LOGGER.warning(
                f"[{self._attr_name}] Modo de ventilador no soportado: {fan_mode}"
            )
            return
            
        if fan_mode in MAP_FAN_MODE_TO_SPEED:
            self._fan_speed = MAP_FAN_MODE_TO_SPEED[fan_mode]
            self._attr_fan_mode = fan_mode
            await self._send_command()
        else:
            _LOGGER.error(
                f"[{self._attr_name}] No se pudo mapear modo ventilador: {fan_mode}"
            )

    async def async_update(self):
        """Update entity state."""
        await self._async_update()
