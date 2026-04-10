from dynaconf import Dynaconf, loaders
from dynaconf.utils.boxing import DynaBox

CONFIG_PATH = "config.yaml"


class Config:
    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.settings = Dynaconf(settings_files=[path])

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings.set(key, value)
        loaders.write(self.path, DynaBox(self.settings.as_dict()).to_dict())


config = Config()
