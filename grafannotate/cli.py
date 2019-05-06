import sys
import requests
import click
import logging
import time
import json

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


@click.command()
@click.option('-u', '--uri', 'annotate_uri',
              default='http://localhost:3000/api/annotations',
              help='uri to send annotation to')
@click.option('-T', '--title', 'title', default='event', help='event title')
@click.option('-t', '--tag', 'tags', multiple=True, help='event tags')
@click.option('-d', '--description', 'description', help='event description')
@click.option('-s', '--start', 'start_time',
              default=int(round(time.time() * 1000)),
              help='event start timestamp (unix secs)')
@click.option('-e', '--end', 'end_time', default=0, help='event end timestamp (unix secs)')
def main(annotate_uri, title, tags, description, start_time, end_time):
    """ Send Grafana annotations """

    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

    if description is None:
        description = "".join([line for line in iter(sys.stdin.readline, '')])

    tags_field = ';'.join(tags)

    try:
        url_parts = urlparse(annotate_uri)
        event_data = {}

        if 'http' in url_parts.scheme:
            event_data['text'] = '<b>%s</b>\n\n%s' % (title, description)
            event_data['tags'] = tags
            event_data['time'] = start_time
            if end_time > 0:
                if end_time < start_time:
                    raise Exception('Event end time cannot be before start time')
                event_data['isRegion'] = True
                event_data['timeEnd'] = end_time

            send_web_annotation(url_parts, event_data)

        elif 'influx' in url_parts.scheme:
            event_data['name'] = 'events'
            event_data['columns'] = ['tags', 'text', 'title']
            event_data['points'] = [[tags_field, description, title]]

            send_influx_annotation(url_parts, event_data)

        else:
            raise NotImplementedError('Scheme %s not recognised in uri %s' %
                                      (url_parts.scheme, annotate_uri))

    except Exception as e:
        logging.fatal(e)
        """ We could exit 1 here but we really don't want to cause a job to
            fail just because we couldn't send an event. """

    sys.exit(0)


def send_web_annotation(url_parts, event_data):
    """ POST event to an endpoint in Grafana Annotations API format """
    logging.info('Sending web event to %s' % url_parts.hostname)

    url = url_parts.geturl()
    auth_tuple = None

    if url_parts.username and url_parts.password:
        auth_tuple = (url_parts.username, url_parts.password)
        url_host_port = url_parts.netloc.split('@')[1]
        url = '%s://%s%s' % (url_parts.scheme, url_host_port, url_parts.path)

    post_result = requests.post(url, json=json.dumps(event_data),
                                auth=auth_tuple, timeout=5)

    if post_result.status_code > 299:
        logging.error('Received %s response, sending event failed' % post_result.status_code)

    if 'message' in post_result:
        logging.info(post_result.message)


def send_influx_annotation(url_parts, event_data):
    raise NotImplementedError('Influx annotations not yet implemented, check back soon.')
    logging.info('Sending influx event to %s' % url_parts.hostname)
    logging.debug(json.dumps(event_data))