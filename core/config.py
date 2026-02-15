import os
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from typing import Optional

class AudioSettings(BaseSettings):
    wake_word: str = "spark"
    voice: str = "en-US-ChristopherNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    engine: str = "edge"

class VisionSettings(BaseSettings):
    enabled: bool = True
    model: str = "moondream"
    screenshot_dir: str = "./screenshots"

class MemorySettings(BaseSettings):
    enabled: bool = True
    path: str = "./spark_memory_db"

class SystemSettings(BaseSettings):
    log_level: str = "INFO"

class Secrets(BaseSettings):
    google_gemini_api_key: Optional[SecretStr] = Field(default=None, alias="GOOGLE_GEMINI_API_KEY")
    deepgram_api_key: Optional[SecretStr] = Field(default=None, alias="DEEPGRAM_API_KEY")
    openai_api_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    elevenlabs_api_key: Optional[SecretStr] = Field(default=None, alias="ELEVENLABS_API_KEY")

class SparkConfig(BaseSettings):
    app_name: str = "S.P.A.R.K."
    version: str = "2.0.0"
    
    audio: AudioSettings = AudioSettings()
    vision: VisionSettings = VisionSettings()
    memory: MemorySettings = MemorySettings()
    system: SystemSettings = SystemSettings()
    secrets: Secrets = Secrets()

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

def load_config(settings_path="config/settings.yaml", secrets_path="config/secrets.yaml") -> SparkConfig:
    """
    Loads configuration from YAML files and overrides with Environment Variables.
    Hierarchy: Env Vars > Secrets.yaml > Settings.yaml > Defaults
    """
    
    # Base config
    config_dict = {}

    # 1. Load Settings YAML
    if os.path.exists(settings_path):
        with open(settings_path, "r") as f:
            yaml_content = yaml.safe_load(f)
            if yaml_content:
                config_dict.update(yaml_content)

    # 2. Load Secrets YAML (if exists)
    secrets_dict = {}
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
            secrets_content = yaml.safe_load(f)
            if secrets_content and "keys" in secrets_content:
                # Map keys to Pydantic model
                s = secrets_content["keys"]
                if s.get("google_gemini"): secrets_dict["google_gemini_api_key"] = s["google_gemini"]
                if s.get("deepgram"): secrets_dict["deepgram_api_key"] = s["deepgram"]
                if s.get("openai"): secrets_dict["openai_api_key"] = s["openai"]

    # Merge secrets into main dict structure if compatible, or just rely on Pydantic to pick them up via env vars
    # For now, we instantiate the config and let Pydantic handle the rest
    
    cfg = SparkConfig(**config_dict)
    
    # Explicitly set secrets if found in YAML (Pydantic will prioritize env vars if set)
    if secrets_dict:
        # This is a simple update; for robust merging we might need more logic
        # But since secrets are simple strings, this works.
        for k, v in secrets_dict.items():
            if v and not getattr(cfg.secrets, k): # Only if not already set (e.g. by ENV)
                setattr(cfg.secrets, k, SecretStr(v))
                
    return cfg

# Global Config Instance
settings = load_config()
