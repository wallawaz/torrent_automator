import configparser

config_parser = configparser.ConfigParser()
DEFAULTAPI = "thetvdb.com"

def get_config_values(config, section):
    if config.endswith(".ini"):
        config_parser.read(config)
    else:
        config_parser.read_string(config)
    return config_parser[section]
