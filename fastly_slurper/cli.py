"""
fastly_slurper.cli
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2017 Disqus, Inc.
:license: Apache, see LICENSE for more details.
"""
import logging
import click
import functools
import statsd
import six
import collections
import time

from . import __version__, slurper

log = logging.getLogger(__name__)

NetAddr = collections.namedtuple('NetAddr', ['host', 'port'])


def _split_netaddr(value, default_port=None):
    if ':' not in value and default_port:
        host = value
        port = default_port
    else:
        try:
            host, port = value.rsplit(':', 1)
            port = int(port)
        except ValueError:
            raise click.BadParameter('Network address format must be IP:PORT: %s' % value)
    return NetAddr(host, port)


def _set_verbosity(ctx, param, verbosity):
    level_map = {
        True: logging.DEBUG,
        False: logging.ERROR,
    }

    level = level_map.get(verbosity, verbosity)
    if level is None:
        return

    logging.root.setLevel(level)


def _make_services(ctx, param, value):
    return tuple(service.split(':', 1) for service in value)


@click.command()
@click.option('--delay', default=1.0, type=float)
@click.option('--statsd-addr', '--statsd', 'statsd_addr', default='localhost')
@click.option('--service', 'services', multiple=True, required=True, callback=_make_services)
@click.option('--prefix', default='fastly')
@click.option('--api-key', required=True)
@click.option('--workers-per-service', type=int, default=1)
@click.option('--verbose/--quiet', default=None, callback=_set_verbosity)
@click.pass_context
def cli(ctx, delay, statsd_addr, services, prefix, api_key, workers_per_service, verbose):
    """Fastly Slurper."""
    log.info('Fastly slurper v%s', __version__)

    client = slurper.Fastly(api_key)

    stats_addr = _split_netaddr(statsd_addr, default_port=8125)
    publisher = statsd.StatsClient(stats_addr.host, stats_addr.port, prefix=prefix)

    workers = [
        slurper.RecorderWorker(client, publisher, service, delay)
        for service in services
        for idx in range(workers_per_service)
    ]

    log.info('Spawning slurpers (%d)', len(workers))
    [w.start() for w in workers]

    log.info('Waiting on workers (%d) to complete', len(workers))
    while True:
        time.sleep(1)

        if all([w.isAlive() for w in workers]):
            continue

        log.error('Oh no! A thread has DIED! Telling remaining children to commit seppuku.')
        [w.seppuku() for w in workers]
        break

    log.error('Waiting for children.')
    [w.join() for w in workers]

    log.info('Done')
