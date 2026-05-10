import pytest
from unittest.mock import MagicMock, patch
from tools.sysmon import get_system_health

def test_get_system_health_nominal():
    with patch('psutil.cpu_percent', return_value=50.0), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.sensors_battery') as mock_battery, \
         patch('GPUtil.getGPUs') as mock_gpus:

        mock_mem.return_value.available = 8.0 * (1024 ** 3)
        mock_mem.return_value.percent = 50.0

        mock_disk.return_value.free = 100.0 * (1024 ** 3)

        mock_battery.return_value.percent = 80

        mock_gpu = MagicMock()
        mock_gpu.name = "GTX 1080"
        mock_gpu.load = 0.5
        mock_gpus.return_value = [mock_gpu]

        result = get_system_health()
        assert "All systems nominal, sir." in result
        assert "CPU is at 50.0%" in result
        assert "with 8.0 GB of RAM available" in result
        assert "battery at 80%" in result
        assert "GTX 1080 is at 50% utilization" in result

def test_get_system_health_heavy_load_cpu():
    with patch('psutil.cpu_percent', return_value=90.0), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.sensors_battery') as mock_battery, \
         patch('GPUtil.getGPUs', return_value=[]):

        mock_mem.return_value.available = 8.0 * (1024 ** 3)
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.free = 100.0 * (1024 ** 3)
        mock_battery.return_value.percent = 80

        result = get_system_health()
        assert "System under heavy load, sir." in result

def test_get_system_health_heavy_load_mem():
    with patch('psutil.cpu_percent', return_value=50.0), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.sensors_battery') as mock_battery, \
         patch('GPUtil.getGPUs', return_value=[]):

        mock_mem.return_value.available = 1.0 * (1024 ** 3)
        mock_mem.return_value.percent = 95.0
        mock_disk.return_value.free = 100.0 * (1024 ** 3)
        mock_battery.return_value.percent = 80

        result = get_system_health()
        assert "System under heavy load, sir." in result

def test_get_system_health_desktop_power():
    with patch('psutil.cpu_percent', return_value=50.0), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.sensors_battery', return_value=None), \
         patch('GPUtil.getGPUs', return_value=[]):

        mock_mem.return_value.available = 8.0 * (1024 ** 3)
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.free = 100.0 * (1024 ** 3)

        result = get_system_health()
        assert "running on desktop power" in result

def test_get_system_health_no_gpu():
    with patch('psutil.cpu_percent', return_value=50.0), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.sensors_battery') as mock_battery, \
         patch('GPUtil.getGPUs', return_value=[]):

        mock_mem.return_value.available = 8.0 * (1024 ** 3)
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.free = 100.0 * (1024 ** 3)
        mock_battery.return_value.percent = 80

        result = get_system_health()
        assert "utilization" not in result

def test_get_system_health_exception():
    with patch('psutil.cpu_percent', side_effect=Exception("mocked error")):
        result = get_system_health()
        assert "I am currently unable to read the hardware telemetry, sir." in result
