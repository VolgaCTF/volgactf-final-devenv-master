import os
import base64
import hashlib
import redis
import jwt
import datetime
from flask import Flask, request, render_template, jsonify
import requests
import pytz
import json
from flask_sse import sse
from random import randrange
from random import choice
from string import ascii_letters, digits
import gevent
from time import mktime
from datetime import datetime, timedelta


app = Flask(__name__)
app.config['REDIS_URL'] = 'redis://redis:6379/2'
app.config['TEMPLATES_AUTO_RELOAD'] = os.getenv('SERVER_RELOAD', 'no') == 'yes'
app.register_blueprint(sse, url_prefix='/stream')

cache = redis.Redis(host='redis', port=6379, db=1)

KEY_LOGS = 'volgactf_final_logs'
KEY_FLAGS = 'volgactf_final_flags'
KEY_STATE = 'volgactf_final_state'

LOG_HISTORY = int(os.getenv('LOG_HISTORY', '150'))
FLAG_HISTORY = int(os.getenv('FLAG_HISTORY', '25'))

def get_form_defaults():
    return {
        'checker_host': os.getenv('DEFAULT_CHECKER_HOST', 'checker'),
        'team_host': os.getenv('DEFAULT_TEAM_HOST', 'service'),
        'team_name': os.getenv('DEFAULT_TEAM_NAME', 'TEAM'),
        'service_name': os.getenv('DEFAULT_SERVICE_NAME', 'SERVICE'),
        'round': int(os.getenv('DEFAULT_ROUND', '1')),
        'flag_lifetime': int(os.getenv('DEFAULT_FLAG_LIFETIME', '360')),
        'round_timespan': int(os.getenv('DEFAULT_ROUND_TIMESPAN', '120')),
        'poll_timespan': int(os.getenv('DEFAULT_POLL_TIMESPAN', '35')),
        'poll_delay': int(os.getenv('DEFAULT_POLL_DELAY', '40'))
    }


@app.route('/')
def index():
    return render_template('index.html', form_defaults=get_form_defaults())


def issue_flag():
    secret = base64.urlsafe_b64decode(
        os.getenv('VOLGACTF_FINAL_FLAG_GENERATOR_SECRET')
    )
    h = hashlib.md5()
    h.update(os.urandom(32))
    h.update(secret)
    flag = h.hexdigest() + '='
    label = ''.join(choice(ascii_letters + digits) for _ in range(8))
    return flag, label


def create_capsule(flag):
    key = os.getenv('VOLGACTF_FINAL_FLAG_SIGN_KEY_PRIVATE').replace('\\n', '\n')
    return '{0}{1}{2}'.format(
        os.getenv('VOLGACTF_FINAL_FLAG_WRAP_PREFIX'),
        jwt.encode(
            {'flag': flag},
            key=key,
            algorithm='ES256'
        ),
        os.getenv('VOLGACTF_FINAL_FLAG_WRAP_SUFFIX')
    )


def create_push_job(capsule, label, params):
    return {
        'params': {
            'endpoint': params['team_host'],
            'capsule': capsule,
            'label': label
        },
        'metadata': {
            'timestamp': datetime.now(pytz.utc).isoformat(),
            'round': params['round'],
            'team_name': params['team_name'],
            'service_name': params['service_name']
        },
        'report_url': 'http://master/api/checker/v2/report_push'
    }


def create_pull_job(capsule, label, params):
    return {
        'params': {
            'request_id': randrange(1, 100),
            'endpoint': params['team_host'],
            'capsule': capsule,
            'label': label
        },
        'metadata': {
            'timestamp': datetime.now(pytz.utc).isoformat(),
            'round': params['round'],
            'team_name': params['team_name'],
            'service_name': params['service_name']
        },
        'report_url': 'http://master/api/checker/v2/report_pull'
    }


def schedule(delay, func, *args, **kw_args):
    state = fetch_state()
    if state['mode'] != 'recurring':
        return
    gevent.spawn_later(0, func, *args, **kw_args)
    gevent.spawn_later(delay, schedule, delay, func, *args, **kw_args)


def parse_settings_form(form):
    defaults = get_form_defaults()
    return {
        'checker_host': form.get('checker_host', defaults['checker_host']),
        'team_host': form.get('team_host', defaults['team_host']),
        'team_name': form.get('team_name', defaults['team_name']),
        'service_name': form.get('service_name', defaults['service_name'])
    }


def parse_onetime_form(form):
    defaults = get_form_defaults()
    r = parse_settings_form(form)
    r.update({
        'round': int(form.get('round', str(defaults['round'])))
    })
    return r


def parse_recurring_form(form):
    defaults = get_form_defaults()
    r = parse_settings_form(form)
    r.update({
        'round': 0,
        'flag_lifetime': int(form.get('flag_lifetime', str(defaults['flag_lifetime']))),
        'round_timespan': int(form.get('round_timespan', str(defaults['round_timespan']))),
        'poll_timespan': int(form.get('poll_timespan', str(defaults['poll_timespan']))),
        'poll_delay': int(form.get('poll_delay', str(defaults['poll_delay'])))
    })
    return r


def internal_push(params):
    flag, label = issue_flag()
    capsule = create_capsule(flag)
    job = create_push_job(capsule, label, params)
    auth = (os.getenv('VOLGACTF_FINAL_AUTH_CHECKER_USERNAME'),
            os.getenv('VOLGACTF_FINAL_AUTH_CHECKER_PASSWORD'))
    url = 'http://{0}/push'.format(params['checker_host'])
    r = requests.post(url, json=job, auth=auth)
    update_logs(dict(
        type='egress',
        category='PUSH',
        timestamp=datetime.now(pytz.utc).isoformat(),
        raw=job
    ))
    sse.publish(fetch_logs(), type='logs')
    update_flags(dict(
        checker_host=params['checker_host'],
        flag=flag,
        status=-1,
        capsule=capsule,
        label=label,
        params=dict(
            team_host=params['team_host'],
            round=params['round'],
            team_name=params['team_name'],
            service_name=params['service_name']
        )
    ))
    sse.publish(fetch_flags(), type='flags')
    return job, r.status_code


@app.route('/onetime_push', methods=['POST'])
def onetime_push():
    params = parse_onetime_form(request.form)
    job, status_code = internal_push(params)
    return jsonify(job), status_code


def scheduled_push():
    with app.app_context():
        state = fetch_state()
        if state['mode'] != 'recurring':
            return
        time_pos = state['params']['poll_delay']
        while time_pos < state['params']['round_timespan']:
            gevent.spawn_later(time_pos, scheduled_pull)
            time_pos += state['params']['poll_timespan']
        state['params']['round'] += 1
        update_state(state)
        sse.publish(fetch_state(), type='state')
        internal_push(state['params'])


def scheduled_pull():
    with app.app_context():
        state = fetch_state()
        if state['mode'] != 'recurring':
            return
        now = datetime.now(pytz.utc)
        items = [x for x in fetch_flags() if x['status'] == 101 and datetime.fromisoformat(x['expires']) > now]
        if len(items):
            internal_pull(choice(items)['flag'])


@app.route('/recurring', methods=['POST'])
def recurring_start():
    state = fetch_state()
    if state['mode'] == 'recurring':
        return '', 400
    params = parse_recurring_form(request.form)
    update_state({
        'mode': 'recurring',
        'params': params
    })
    sse.publish(fetch_state(), type='state')
    schedule(params['round_timespan'], scheduled_push)
    return jsonify({}), 202


@app.route('/recurring', methods=['DELETE'])
def recurring_stop():
    update_state({
        'mode': 'onetime'
    })
    sse.publish(fetch_state(), type='state')
    return jsonify({}), 202


def internal_pull(flag):
    with app.app_context():
        flags = fetch_flags()
        item = [x for x in flags if x['flag'] == flag][0]
        job = create_pull_job(item['capsule'], item['label'], item['params'])
        auth = (os.getenv('VOLGACTF_FINAL_AUTH_CHECKER_USERNAME'),
                os.getenv('VOLGACTF_FINAL_AUTH_CHECKER_PASSWORD'))
        checker_host = item['checker_host']
        url = 'http://{0}/pull'.format(checker_host)
        r = requests.post(url, json=job, auth=auth)
        update_logs(dict(
            type='egress',
            category='PULL',
            timestamp=datetime.now(pytz.utc).isoformat(),
            raw=job
        ))
        sse.publish(fetch_logs(), type='logs')
        return job, r.status_code


@app.route('/pull', methods=['POST'])
def pull():
    flag = request.form.get('flag')
    job, status_code = internal_pull(flag)
    return jsonify(job), status_code


def fetch_logs():
    if cache.llen(KEY_LOGS) == 0:
        return list()
    return list(map(lambda x: json.loads(x), cache.lrange(KEY_LOGS, 0, -1)))


def fetch_flags():
    if cache.llen(KEY_FLAGS) == 0:
        return list()
    return list(map(lambda x: json.loads(x), cache.lrange(KEY_FLAGS, 0, -1)))


def fetch_state():
    state_str = cache.get(KEY_STATE)
    if state_str is None:
        return { 'mode': 'onetime' }
    return json.loads(state_str)


def update_logs(item):
    cache.lpush(KEY_LOGS, json.dumps(item))
    cache.ltrim(KEY_LOGS, 0, LOG_HISTORY - 1)


def update_flags(item):
    cache.lpush(KEY_FLAGS, json.dumps(item))
    cache.ltrim(KEY_FLAGS, 0, FLAG_HISTORY - 1)


@app.route('/logs')
def get_logs():
    logs = fetch_logs()
    return jsonify(logs)


@app.route('/logs', methods=['DELETE'])
def clear_logs():
    cache.delete(KEY_LOGS)
    sse.publish(fetch_logs(), type='logs')
    return '', 204


@app.route('/flags')
def get_flags():
    flags = fetch_flags()
    return jsonify(flags)


@app.route('/flags', methods=['DELETE'])
def clear_flags():
    cache.delete(KEY_FLAGS)
    sse.publish(fetch_flags(), type='flags')
    return '', 204


def edit_flags(flag, label, status, lifetime):
    for ndx, item in enumerate(fetch_flags()):
        if item['flag'] == flag:
            item['status'] = status
            item['label'] = label
            expires = datetime.now(pytz.utc) + timedelta(seconds=lifetime)
            item['expires'] = expires.isoformat()
            cache.lset(KEY_FLAGS, ndx, json.dumps(item))
            break


@app.route('/state')
def get_state():
    state = fetch_state()
    return jsonify(state)


def update_state(state):
    cache.set(KEY_STATE, json.dumps(state))


@app.route('/api/checker/v2/report_push', methods=['POST'])
def report_push():
    data = request.get_json()
    update_logs(dict(
        type='ingress',
        category='PUSH',
        timestamp=datetime.now(pytz.utc).isoformat(),
        raw=data
    ))
    sse.publish(fetch_logs(), type='logs')
    if data['status'] == 101:
        lifetime = 0
        state = fetch_state()
        if state['mode'] == 'recurring':
            lifetime = state['params']['flag_lifetime']
        edit_flags(data['flag'], data['label'], data['status'], lifetime)
        sse.publish(fetch_flags(), type='flags')
        if state['mode'] == 'recurring':
            gevent.spawn(internal_pull, data['flag'])
    return '', 204


@app.route('/api/checker/v2/report_pull', methods=['POST'])
def report_pull():
    data = request.get_json()
    update_logs(dict(
        type='ingress',
        category='PULL',
        timestamp=datetime.now(pytz.utc).isoformat(),
        raw=data
    ))
    sse.publish(fetch_logs(), type='logs')
    return '', 204


@app.route('/api/capsule/v1/public_key', methods=['GET'])
def get_public_key():
    key = os.getenv('VOLGACTF_FINAL_FLAG_SIGN_KEY_PUBLIC').replace('\\n', '\n')
    return key, 200, { 'Content-Type': 'text/plain' }


with app.app_context():
    state = fetch_state()
    if state['mode'] == 'recurring':
        schedule(state['params']['round_timespan'], scheduled_push)
