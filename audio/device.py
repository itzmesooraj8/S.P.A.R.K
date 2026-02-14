import pyaudio
from core.config import Config

class AudioDevice:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None

    def start_input_stream(self, callback=None):
        """Starts the audio input stream."""
        if self.stream and self.stream.is_active():
            return

        self.stream = self.pa.open(
            rate=Config.SAMPLE_RATE,
            channels=Config.CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=Config.FRAME_LENGTH,
            stream_callback=callback
        )
        print("Audio Input Stream Started.")

    def stop_input_stream(self):
        """Stops and closes the audio input stream."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        print("Audio Input Stream Stopped.")

    def get_input_devices(self):
        """Lists available input devices."""
        info = self.pa.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        devices = []
        for i in range(0, numdevices):
            if (self.pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                devices.append(self.pa.get_device_info_by_host_api_device_index(0, i).get('name'))
        return devices

    def terminate(self):
        self.stop_input_stream()
        self.pa.terminate()
