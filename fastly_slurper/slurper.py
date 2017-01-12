"""
fastly_slurper.slurper
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2017 Disqus, Inc.
:license: Apache, see LICENSE for more details.
"""
from __future__ import (absolute_import, division, generators, nested_scopes,
                        print_function, unicode_literals, with_statement)

import logging
import threading
import requests
import six
import time

from . import __version__

log = logging.getLogger(__name__)

_FASTLY_API_BASE_URI = 'https://rt.fastly.com/'
_USER_AGENT = 'fastly-slurpy/%s' % __version__


class Fastly(requests.Session):
    base = _FASTLY_API_BASE_URI
    user_agent = _USER_AGENT

    def __init__(self, api_key, *args, **kwargs):
        super(Fastly, self).__init__(*args, **kwargs)

        self.api_key = api_key

        self.headers.update({
            'Fastly-Key': self.api_key,
            'User-Agent': self.user_agent,
        })

    def _ensure_abs_url(self, url):
        if '://' not in url:
            url = '%s%s' % (self.base, url)
        return url

    def request(self, method, url, *args, **kwargs):
        url = self._ensure_abs_url(url)
        return super(Fastly, self).request(method=method, url=url, **kwargs)


class RecorderWorker(threading.Thread):
    daemon = True

    def __init__(self, client, publisher, service, delay=1.0):
        super(RecorderWorker, self).__init__()
        self.client = client
        self.publisher = publisher
        self.name, self.channel = service
        self.delay = delay

    def url_for_timestamp(self, ts):
        strts = '%.9f' % ts
        strts = strts.replace('.', '')
        return '/'.join(['channel', self.channel, 'ts', strts])

    def fetch(self, ts):
        url = self.url_for_timestamp(ts)
        return self.client.get(url)

    def unwrap_resp(self, resp):
        # data data data
        data = resp.json()
        data = data['Data']
        # data
        return data

    def parse(self, iterable, skip_keys=['miss_histogram']):
        for stats in iterable:
            dc = stats.get('datacenter')
            if not dc:
                continue

            for dc_name, dc_stats in six.iteritems(dc):
                for k, v in six.iteritems(dc_stats):
                    if k in skip_keys:
                        continue

                    if k.endswith('_time'):
                        kpart = k.rsplit('_', 1)[0]

                        # TODO Wat
                        if dc_stats.get(kpart):
                            v = v / dc_stats[kpart] * 1000

                    k = '%s.%s' % (dc_name, k)
                    yield k, v

    def record(self, iterable):
        cnt = 0
        for k, v in iterable:
            k = '%s.%s' % (self.name, k)
            v = int(v)
            self.publisher.timing(k, v)
            cnt += 1

        self.publisher.gauge('last_record', time.time())
        return cnt

    def run(self, next_at=0):
        self.commit_seppuku = False
        while not self.commit_seppuku:
            remaining = time.time() - next_at
            if next_at and remaining > 0:
                log.debug('Delaying remaining=%s secs', remaining)
                time.sleep(remaining)

            ts = time.time()
            next_at = ts + self.delay

            log.debug('Slurping for timestamp=%s next_at=%s', ts, next_at)

            resp = self.fetch(ts)
            if not resp.ok:
                log.error('Failed to fetch stats for ts=%s resp=%s', ts, resp)
                continue

            try:
                data = self.unwrap_resp(resp)
                stats = dict(self.parse(data))
            except Exception:
                log.exception('Failed to parse stats for ts=%s resp=%s:', ts, resp)
                continue

            try:
                cnt = self.record(six.iteritems(stats))
            except Exception:
                log.exception('Failed to record stats=%s for ts=%s resp=%s', stats, ts, resp)
                continue

            log.info('Sent %d stats for ts=%s next_at=%s', cnt, ts, next_at)

    def seppuku(self):
        log.warn('Committing seppuku after this round. We all have a time, and my time is now.')
        self.commit_seppuku = True
