import psutil
import logging

logger = logging.getLogger("SPARK_SYSMON")

def get_system_health() -> str:
    """Returns a J.A.R.V.I.S.-style summary of system health (CPU, RAM, Disk, Battery)."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        
        mem = psutil.virtual_memory()
        ram_free_gb = mem.available / (1024 ** 3)
        
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 ** 3)
        
        battery = psutil.sensors_battery()
        batt_str = f", battery at {battery.percent}%" if battery else ", running on desktop power"
        
        if cpu > 85 or mem.percent > 90:
            status = "System under heavy load, sir."
        else:
            status = "All systems nominal, sir."
            
        return f"{status} CPU is at {cpu}%, with {ram_free_gb:.1f} GB of RAM available{batt_str}."
    except Exception as e:
        logger.error(f"Sysmon error: {e}")
        return "I am currently unable to read the hardware telemetry, sir."

def get_raw_metrics() -> dict:
    """Returns raw hardware telemetry for the React HUD WebSocket."""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    battery = psutil.sensors_battery()
    return {
        "cpu": cpu,
        "ramFree": mem.available / (1024 ** 3),
        "ramTotal": mem.total / (1024 ** 3),
        "diskFree": disk.free / (1024 ** 3),
        "diskTotal": disk.total / (1024 ** 3),
        "batteryPercent": battery.percent if battery else 100
    }
