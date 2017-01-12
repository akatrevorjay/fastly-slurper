import logging.config

from . import cli

# At least for now, this is not a chained config as time is precious.
from . import default_config as config


def main():
    logging.config.dictConfig(config.LOGGING)

    return cli.cli(auto_envvar_prefix=config.SHORT_NAME.upper(),)


if __name__ == '__main__':
    main()
