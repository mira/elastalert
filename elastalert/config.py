# -*- coding: utf-8 -*-
import copy
import datetime
import hashlib
import logging
import os
import sys

import jsonschema
import yaml
import yaml.scanner
from staticconf.loader import yaml_loader

import alerts
import enhancements
from http import HttpConnection
from opsgenie import OpsGenieAlerter
import ruletypes
from util import dt_to_ts
from util import dt_to_ts_with_format
from util import dt_to_unix
from util import dt_to_unixms
from util import EAException
from util import ts_to_dt
from util import ts_to_dt_with_format
from util import unix_to_dt
from util import unixms_to_dt



# schema for rule yaml
rule_schema = jsonschema.Draft4Validator(
    yaml.load(open(os.path.join(os.path.dirname(__file__), 'schema.yaml')))
)

# Required global (config.yaml) and local (rule.yaml)  configuration options
required_globals = frozenset([
    'run_every', 'rules_folder', 'es_host', 'es_port', 
    'writeback_index', 'buffer_time'
])
required_locals = frozenset(['alert', 'type', 'name', 'index'])

# Settings that can be derived from ENV variables
env_settings = {'ES_USE_SSL': 'use_ssl',
                'ES_PASSWORD': 'es_password',
                'ES_USERNAME': 'es_username',
                'ES_HOST': 'es_host',
                'ES_PORT': 'es_port'}

# Used to map the names of rules to their classes
rules_mapping = {
    'frequency': ruletypes.FrequencyRule,
    'any': ruletypes.AnyRule,
    'spike': ruletypes.SpikeRule,
    'blacklist': ruletypes.BlacklistRule,
    'whitelist': ruletypes.WhitelistRule,
    'change': ruletypes.ChangeRule,
    'flatline': ruletypes.FlatlineRule,
    'new_term': ruletypes.NewTermsRule,
    'cardinality': ruletypes.CardinalityRule,
    'metric_aggregation': ruletypes.MetricAggregationRule,
    'percentage_match': ruletypes.PercentageMatchRule,
}

# Used to map names of alerts to their classes
alerts_mapping = {
    'email': alerts.EmailAlerter,
    'jira': alerts.JiraAlerter,
    'opsgenie': OpsGenieAlerter,
    'stomp': alerts.StompAlerter,
    'debug': alerts.DebugAlerter,
    'command': alerts.CommandAlerter,
    'sns': alerts.SnsAlerter,
    'hipchat': alerts.HipChatAlerter,
    'stride': alerts.StrideAlerter,
    'ms_teams': alerts.MsTeamsAlerter,
    'slack': alerts.SlackAlerter,
    'pagerduty': alerts.PagerDutyAlerter,
    'exotel': alerts.ExotelAlerter,
    'twilio': alerts.TwilioAlerter,
    'victorops': alerts.VictorOpsAlerter,
    'telegram': alerts.TelegramAlerter,
    'gitter': alerts.GitterAlerter,
    'servicenow': alerts.ServiceNowAlerter,
    'alerta': alerts.AlertaAlerter,
    'post': alerts.HTTPPostAlerter
}
'''
A partial ordering of alert types. Relative order will be preserved in the 
resulting alerts list. For example, jira goes before email so the ticket will 
be added to the resulting email.
'''
alerts_order = {
    'jira': 0,
    'email': 1
}

base_config = {}


def get_module(module_name):
    """ Loads a module and returns a specific object.
    module_name should 'module.file.object'.
    Returns object or raises EAException on error. """
    try:
        module_path, module_class = module_name.rsplit('.', 1)
        base_module = __import__(
            module_path, globals(), locals(), [module_class]
        )
        module = getattr(base_module, module_class)
    except (ImportError, AttributeError, ValueError) as e:
        raise EAException("Could not import module %s: %s" % (module_name, e)), None, sys.exc_info()[2]
    return module


def load_configuration(key, rule, conf, args=None):
    """ Load a yaml rule file and fill in the relevant fields with objects.

    :param filename: The name of a rule configuration file.
    :param conf: The global configuration dictionary, used for populating defaults.
    :return: The rule configuration, a dictionary.
    """
    load_options(rule, conf, key, args)
    load_modules(rule, args)
    return rule


def load_options(rule, conf, key, args=None):
    """ Converts time objects, sets defaults, and validates some settings.

    :param rule: A dictionary of parsed YAML from a rule config file.
    :param conf: The global configuration dictionary, used for populating defaults.
    """

    try:
        rule_schema.validate(rule)
    except jsonschema.ValidationError as e:
        raise EAException("Invalid Rule file: %s\n%s" % (key, e))

    try:
        # Set all time based parameters
        if 'timeframe' in rule:
            rule['timeframe'] = datetime.timedelta(**rule['timeframe'])
        if 'realert' in rule:
            rule['realert'] = datetime.timedelta(**rule['realert'])
        else:
            if 'aggregation' in rule:
                rule['realert'] = datetime.timedelta(minutes=0)
            else:
                rule['realert'] = datetime.timedelta(minutes=1)
        if 'aggregation' in rule and not rule['aggregation'].get('schedule'):
            rule['aggregation'] = datetime.timedelta(**rule['aggregation'])
        if 'query_delay' in rule:
            rule['query_delay'] = datetime.timedelta(**rule['query_delay'])
        if 'buffer_time' in rule:
            rule['buffer_time'] = datetime.timedelta(**rule['buffer_time'])
        if 'bucket_interval' in rule:
            rule['bucket_interval_timedelta'] = datetime.timedelta(**rule['bucket_interval'])
        if 'exponential_realert' in rule:
            rule['exponential_realert'] = datetime.timedelta(**rule['exponential_realert'])
        if 'kibana4_start_timedelta' in rule:
            rule['kibana4_start_timedelta'] = datetime.timedelta(**rule['kibana4_start_timedelta'])
        if 'kibana4_end_timedelta' in rule:
            rule['kibana4_end_timedelta'] = datetime.timedelta(**rule['kibana4_end_timedelta'])
    except (KeyError, TypeError) as e:
        raise EAException('Invalid time format used: %s' % (e))

    # Set defaults, copy defaults from config.yaml
    for key, val in base_config.items():
        rule.setdefault(key, val)
    rule.setdefault('name', os.path.splitext(key)[0])
    rule.setdefault('realert', datetime.timedelta(seconds=0))
    rule.setdefault('aggregation', datetime.timedelta(seconds=0))
    rule.setdefault('query_delay', datetime.timedelta(seconds=0))
    rule.setdefault('timestamp_field', '@timestamp')
    rule.setdefault('filter', [])
    rule.setdefault('timestamp_type', 'iso')
    rule.setdefault('timestamp_format', '%Y-%m-%dT%H:%M:%SZ')
    rule.setdefault('_source_enabled', True)
    rule.setdefault('use_local_time', True)
    rule.setdefault('description', "")

    # Set timestamp_type conversion function, used when generating queries and processing hits
    rule['timestamp_type'] = rule['timestamp_type'].strip().lower()
    if rule['timestamp_type'] == 'iso':
        rule['ts_to_dt'] = ts_to_dt
        rule['dt_to_ts'] = dt_to_ts
    elif rule['timestamp_type'] == 'unix':
        rule['ts_to_dt'] = unix_to_dt
        rule['dt_to_ts'] = dt_to_unix
    elif rule['timestamp_type'] == 'unix_ms':
        rule['ts_to_dt'] = unixms_to_dt
        rule['dt_to_ts'] = dt_to_unixms
    elif rule['timestamp_type'] == 'custom':
        def _ts_to_dt_with_format(ts):
            return ts_to_dt_with_format(ts, ts_format=rule['timestamp_format'])

        def _dt_to_ts_with_format(dt):
            return dt_to_ts_with_format(dt, ts_format=rule['timestamp_format'])

        rule['ts_to_dt'] = _ts_to_dt_with_format
        rule['dt_to_ts'] = _dt_to_ts_with_format
    else:
        raise EAException('timestamp_type must be one of iso, unix, or unix_ms')

    # Set HipChat options from global config
    rule.setdefault('hipchat_msg_color', 'red')
    rule.setdefault('hipchat_domain', 'api.hipchat.com')
    rule.setdefault('hipchat_notify', True)
    rule.setdefault('hipchat_from', '')
    rule.setdefault('hipchat_ignore_ssl_errors', False)

    # Make sure we have required options
    if required_locals - frozenset(rule.keys()):
        raise EAException('Missing required option(s): %s' % (', '.join(required_locals - frozenset(rule.keys()))))

    if 'include' in rule and type(rule['include']) != list:
        raise EAException('include option must be a list')

    if isinstance(rule.get('query_key'), list):
        rule['compound_query_key'] = rule['query_key']
        rule['query_key'] = ','.join(rule['query_key'])

    if isinstance(rule.get('aggregation_key'), list):
        rule['compound_aggregation_key'] = rule['aggregation_key']
        rule['aggregation_key'] = ','.join(rule['aggregation_key'])

    if isinstance(rule.get('compare_key'), list):
        rule['compound_compare_key'] = rule['compare_key']
        rule['compare_key'] = ','.join(rule['compare_key'])
    elif 'compare_key' in rule:
        rule['compound_compare_key'] = [rule['compare_key']]
    # Add QK, CK and timestamp to include
    include = rule.get('include', ['*'])
    if 'query_key' in rule:
        include.append(rule['query_key'])
    if 'compound_query_key' in rule:
        include += rule['compound_query_key']
    if 'compound_aggregation_key' in rule:
        include += rule['compound_aggregation_key']
    if 'compare_key' in rule:
        include.append(rule['compare_key'])
    if 'compound_compare_key' in rule:
        include += rule['compound_compare_key']
    if 'top_count_keys' in rule:
        include += rule['top_count_keys']
    include.append(rule['timestamp_field'])
    rule['include'] = list(set(include))

    # Check that generate_kibana_url is compatible with the filters
    if rule.get('generate_kibana_link'):
        for es_filter in rule.get('filter'):
            if es_filter:
                if 'not' in es_filter:
                    es_filter = es_filter['not']
                if 'query' in es_filter:
                    es_filter = es_filter['query']
                if es_filter.keys()[0] not in ('term', 'query_string', 'range'):
                    raise EAException('generate_kibana_link is incompatible with filters other than term, query_string and range. '
                                      'Consider creating a dashboard and using use_kibana_dashboard instead.')

    # Check that doc_type is provided if use_count/terms_query
    if rule.get('use_count_query') or rule.get('use_terms_query'):
        if 'doc_type' not in rule:
            raise EAException('doc_type must be specified.')

    # Check that query_key is set if use_terms_query
    if rule.get('use_terms_query'):
        if 'query_key' not in rule:
            raise EAException('query_key must be specified with use_terms_query')

    # Warn if use_strf_index is used with %y, %M or %D
    # (%y = short year, %M = minutes, %D = full date)
    if rule.get('use_strftime_index'):
        for token in ['%y', '%M', '%D']:
            if token in rule.get('index'):
                logging.warning('Did you mean to use %s in the index? '
                                'The index will be formatted like %s' % (token,
                                                                         datetime.datetime.now().strftime(rule.get('index'))))


def load_modules(rule, args=None):
    """ Loads things that could be modules. Enhancements, alerts and rule type. """
    # Set match enhancements
    match_enhancements = []
    for enhancement_name in rule.get('match_enhancements', []):
        if enhancement_name in dir(enhancements):
            enhancement = getattr(enhancements, enhancement_name)
        else:
            enhancement = get_module(enhancement_name)
        if not issubclass(enhancement, enhancements.BaseEnhancement):
            raise EAException("Enhancement module %s not a subclass of BaseEnhancement" % (enhancement_name))
        match_enhancements.append(enhancement(rule))
    rule['match_enhancements'] = match_enhancements

    # Convert rule type into RuleType object
    if rule['type'] in rules_mapping:
        rule['type'] = rules_mapping[rule['type']]
    else:
        rule['type'] = get_module(rule['type'])
        if not issubclass(rule['type'], ruletypes.RuleType):
            raise EAException('Rule module %s is not a subclass of RuleType' % (rule['type']))

    # Make sure we have required alert and type options
    reqs = rule['type'].required_options

    if reqs - frozenset(rule.keys()):
        raise EAException('Missing required option(s): %s' % (', '.join(reqs - frozenset(rule.keys()))))
    # Instantiate rule
    try:
        rule['type'] = rule['type'](rule, args)
    except (KeyError, EAException) as e:
        raise EAException('Error initializing rule %s: %s' % (rule['name'], e)), None, sys.exc_info()[2]
    # Instantiate alert
    rule['alert'] = load_alerts(rule, alert_field=rule['alert'])


def isyaml(filename):
    return filename.endswith('.yaml') or filename.endswith('.yml')


def get_file_paths(conf, use_rule=None):
    # Passing a filename directly can bypass rules_folder and .yaml checks
    if use_rule and os.path.isfile(use_rule):
        return [use_rule]
    rule_folder = conf['rules_folder']
    rule_keys = []
    if conf['scan_subdirectories']:
        for root, folders, files in os.walk(rule_folder):
            for filename in files:
                if use_rule and use_rule != filename:
                    continue
                if isyaml(filename):
                    rule_keys.append(os.path.join(root, filename))
    else:
        for filename in os.listdir(rule_folder):
            fullpath = os.path.join(rule_folder, filename)
            if os.path.isfile(fullpath) and isyaml(filename):
                rule_keys.append(fullpath)
    return rule_keys


def load_alerts(rule, alert_field):
    def normalize_config(alert):
        """Alert config entries are either "alertType" or {"alertType": {"key": "data"}}.
        This function normalizes them both to the latter format. """
        if isinstance(alert, basestring):
            return alert, rule
        elif isinstance(alert, dict):
            name, config = iter(alert.items()).next()
            config_copy = copy.copy(rule)
            config_copy.update(config)  # warning, this (intentionally) mutates the rule dict
            return name, config_copy
        else:
            raise EAException()

    def create_alert(alert, alert_config):
        alert_class = alerts_mapping.get(alert) or get_module(alert)
        if not issubclass(alert_class, alerts.Alerter):
            raise EAException('Alert module %s is not a subclass of Alerter' % (alert))
        missing_options = (rule['type'].required_options | alert_class.required_options) - frozenset(alert_config or [])
        if missing_options:
            raise EAException('Missing required option(s): %s' % (', '.join(missing_options)))
        return alert_class(alert_config)

    try:
        if type(alert_field) != list:
            alert_field = [alert_field]

        alert_field = [normalize_config(x) for x in alert_field]
        alert_field = sorted(alert_field, key=lambda (a, b): alerts_order.get(a, -1))
        # Convert all alerts into Alerter objects
        alert_field = [create_alert(a, b) for a, b in alert_field]

    except (KeyError, EAException) as e:
        raise EAException('Error initiating alert %s: %s' % (rule['alert'], e)), None, sys.exc_info()[2]

    return alert_field


def load_rules_configuration(filename):
    conf = yaml_loader(filename)

    for env_var, conf_var in env_settings.items():
        if env_var in os.environ:
            conf[conf_var] = os.environ[env_var]

    # Make sure we have all required globals
    if required_globals - frozenset(conf.keys()):
        raise EAException(
            '{filename} must contain {key}'.format(
                filename=filename, 
                key=', '.join(required_globals - frozenset(conf.keys()))
            )
        )

    conf.setdefault('max_query_size', 10000)
    conf.setdefault('scroll_keepalive', '30s')
    conf.setdefault('disable_rules_on_error', True)
    conf.setdefault('scan_subdirectories', True)
    conf.setdefault('rules_type', 'dir')

    # Convert run_every, buffer_time into a timedelta object
    try:
        conf['run_every'] = datetime.timedelta(**conf['run_every'])
        conf['buffer_time'] = datetime.timedelta(**conf['buffer_time'])
        if 'alert_time_limit' in conf:
            conf['alert_time_limit'] = datetime.timedelta(**conf['alert_time_limit'])
        else:
            conf['alert_time_limit'] = datetime.timedelta(days=2)
        if 'old_query_limit' in conf:
            conf['old_query_limit'] = datetime.timedelta(**conf['old_query_limit'])
        else:
            conf['old_query_limit'] = datetime.timedelta(weeks=1)
    except (KeyError, TypeError) as e:
        raise EAException('Invalid time format used: %s' % (e))

    global base_config
    base_config = copy.deepcopy(conf)
    return conf


def load_test_configuration(filename):
    conf = yaml_loader(filename)

    # Need to convert these parameters to datetime objects
    for key in ['buffer_time', 'run_every', 'alert_time_limit', 'old_query_limit']:
        if key in conf:
            conf[key] = datetime.timedelta(**conf[key])

    # Mock configuration. This specifies the base values for attributes, unless supplied otherwise.
    conf_default = {
        'rules_folder': 'rules',
        'es_host': 'localhost',
        'es_port': 14900,
        'writeback_index': 'wb',
        'max_query_size': 10000,
        'alert_time_limit': datetime.timedelta(hours=24),
        'old_query_limit': datetime.timedelta(weeks=1),
        'run_every': datetime.timedelta(minutes=5),
        'disable_rules_on_error': False,
        'buffer_time': datetime.timedelta(minutes=45),
        'scroll_keepalive': '30s'
    }

    for key in conf_default:
        if key not in conf:
            conf[key] = conf_default[key]

    global base_config
    base_config = copy.deepcopy(conf)
    return conf


def load_rules(args, is_test=False):
    """ Creates a conf dictionary for ElastAlerter. Loads the global
    config file and then each rule found in rules_folder.

    :param args: The parsed arguments to ElastAlert
    :return: The global configuration, a dictionary.
    """

    conf = load_rules_configuration(
        args.config
    ) if not is_test else load_test_rules_configuration(args.config)

    use_rule = args.rule

    # Load each rule configuration file
    names = []
    rules = []

    for key, value in yield_rules(conf, use_rule=use_rule):
        try:
            rule = load_configuration(key, value, conf, args)            
            if rule['name'] in names:
                raise EAException('Duplicate rule named %s' % (rule['name']))
        except EAException as e:
            raise EAException('Error loading file %s: %s' % (key, e))

        rules.append(rule)
        names.append(rule['name'])

    conf['rules'] = rules
    return conf


def parse_rule(key, value):
    rule = {'rule_key': key}

    while True:
        '''
        Special case for merging filters:
        if both files specify a filter merge (AND) them
        '''
        if 'filter' in rule and 'filter' in value:
            rule['filter'] = value['filter'] + rule['filter']

        value.update(rule)
        rule = value

        if 'import' in rule:
            # Find the path of the next file.
            if os.path.isabs(rule['import']):
                filename = rule['import']
            else:
                filename = os.path.join(
                    os.path.dirname(filename), rule['import']
                )
            del(rule['import'])  # or we could go on forever!
        else:
            break

    return rule


def yield_api_rules(conf, use_rule=None):
    if 'rules_api_host' not in conf:
        raise EAException("'api' rule type requires 'rules_api_host' config")

    rules_api_host = conf['rules_api_host']
    
    if 'rules_api_path' in conf:
        rules_api_path = conf['rules_api_path']
    else:
        rules_api_path = ''

    if 'rules_api_method' in conf:
        rules_api_method = conf['rules_api_method'].strip().lower()
    else:
        rules_api_method = 'get'

    if 'rules_api_port' in conf:
        rules_api_port = int(conf['rules_api_port'])
    else:
        rules_api_port = 80

    conn = HttpConnection(rules_api_host, port=rules_api_port)
    if rules_api_method not in ["get", "post", "delete", "put"]:
        raise EAException(
            'rules_api_method "{method}" is invalid'.format(
                method=rules_api_method
            )
        )

    configs = getattr(conn, rules_api_method)(
        rules_api_path, headers={'Connection':'close'}
    ).response.decode_json()
    
    for k, v in configs.items():
        yield k, v


def yield_dir_rules(conf, use_rule=None):
    rule_keys = get_file_paths(conf, use_rule)

    for rule_key in rule_keys:
        with open(rule_key) as fh:
            try:
                yield rule_key, yaml_loader(fh.read())        
            except yaml.scanner.ScannerError as e:
                raise EAException('Could not parse file %s: %s' % (rule_key, e))


def yield_rules(conf, use_rule=None):
    if conf['rules_type'] == "api":
        rules = yield_api_rules(conf, use_rule=use_rule)
    elif conf['rules_type'] == "dir":
        rules = yield_dir_rules(conf, use_rule=use_rule)
    else:
        raise EAException(
            "'{rules_type}' is an invalid_rules_type".format(
                rules_type=rules_type
            )
        )

    for k, v in rules:
        yield k, parse_rule(k, v)


def load_rule_configuration(key, conf, use_rule=None):
    for rule_key, rule in yield_rules(conf, use_rule=use_rule):
        if rule_key == key:
            return load_configuration(key, rule, conf)

    raise EAException("Unable to find rule with key: '{key}'".format(key=key))


def get_rule_hashes(conf, use_rule=None):
    rule_mod_times = {}

    for k, v in yield_rules(conf, use_rule=use_rule):
        rule_mod_times[k] = hashlib.sha1(str(v)).digest()
    
    return rule_mod_times
