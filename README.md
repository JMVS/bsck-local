# BGH UDP Smart Control

Integración de Home Assistant para controlar aires acondicionados BGH mediante protocolo UDP local.

## Características

✅ **100% Local** - Sin conexión a Internet requerida
✅ **Múltiples ACs** - Agrega todos los aires que necesites
✅ **Polling automático** - Actualización cada 1 minuto
✅ **Modos completos** - Off, Cool, Heat, Dry, Fan Only, Auto
✅ **Control de ventilador** - 3 velocidades (Low, Medium, High)

## Instalación

### Vía HACS (Recomendado)

1. Abre HACS en Home Assistant
2. Ve a "Integraciones"
3. Click en los 3 puntos → "Repositorios personalizados"
4. Agrega: `https://github.com/JMVS/bsck-local`
5. Selecciona categoría: "Integration"
6. Busca "BSCK - BGH UDP Smart Control" e instala
7. Reinicia Home Assistant

### Manual

1. Copia la carpeta `custom_components/bsck-local` a tu directorio `config/custom_components/`
2. Reinicia Home Assistant

## Configuración

1. Ve a **Configuración** → **Dispositivos y Servicios**
2. Click en **+ Agregar Integración**
3. Busca "BGH UDP Smart Control"
4. Completa:
   - **Nombre del AC**: Ej: "Living", "Dormitorio"
   - **Dirección IP**: IP del módulo WiFi del AC (ej: 192.168.2.169)
   - **Puerto UDP** (opcional): Por defecto 20910
   - **Puerto Local** (opcional): Por defecto 20911

5. Repite para cada AC adicional

## Uso

Cada AC aparecerá como entidad `climate` en Home Assistant:

```yaml
# Ejemplo de automatización
automation:
  - alias: "Enfriar dormitorio a las 22hs"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.dormitorio
        data:
          hvac_mode: cool
      - service: climate.set_fan_mode
        target:
          entity_id: climate.dormitorio
        data:
          fan_mode: "High"
```

## Características Avanzadas

✅ **Cambio de temperatura**: Ahora soportado vía UDP (bytes 23-24 del comando)
✅ **Fan Auto**: Modo automático de ventilador (254)
✅ **Validación robusta**: Rangos de temperatura y modos verificados
✅ **Estado de disponibilidad**: Detecta cuando el AC está offline
✅ **Logging detallado**: Debug completo para troubleshooting

📊 **Temperatura ambiente**: Se reporta desde sensor del propio AC. Puedes complementar con sensor externo DHT/BME280 para mayor precisión.

## Troubleshooting

### No se actualiza el estado
- Verifica que el puerto 20911 no esté en uso
- Revisa los logs: `Configuración → Registros → Filtrar por "bgh_udp"`

### No responde a comandos
- Verifica la IP del AC con `ping 192.168.2.169`
- Asegúrate que el puerto 20910 esté abierto en el firewall

### Múltiples ACs conflictos
- Cada AC debe usar puertos locales diferentes
- Ejemplo: AC1 usa 20911, AC2 usa 20912, etc.

## Estructura del Proyecto

```
custom_components/bsck-local/
├── __init__.py          # Inicialización
├── manifest.json        # Metadatos
├── const.py            # Constantes
├── config_flow.py      # Configuración UI
├── climate.py          # Entidad climate
└── translations/
    └── en.json         # Traducciones
```

## Desarrollo

Basado en ingeniería inversa del protocolo UDP usado por:
- Módulos WiFi BGH Smart Control
- Apps BGH Smart Home
- Integraciones Node-RED existentes

## Licencia

MIT

## Soporte

🐛 Reporta bugs en: [GitHub Issues](https://github.com/JMVS/bsck-local/issues)
