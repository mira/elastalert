#!/bin/bash


function write_config_key {
	local key=$1
	local value=$2
	echo "$key: $value" >> $CONFIG_PATH
}


function write_config_key_if_exists {	
	if [ -z ${!2} ]; then
		echo "$2 is unset."
	else
		echo "$1: ${!2}" >> $CONFIG_PATH
	fi
}


function validate_key {
	if [ -z ${!1} ]; then
		echo "$1 is unset."
		exit 1
	else
		echo "$1 is set to '${!1}'"
	fi
}


validate_key "ES_HOST"
validate_key "ES_PORT"

rm -f $CONFIG_PATH
touch $CONFIG_PATH

write_config_key "rules_folder" "rules"
write_config_key "rules_type" "${RULES_TYPE:-"dir"}"

write_config_key_if_exists "rules_api_host" "RULES_API_HOST"
write_config_key_if_exists "rules_api_port" "RULES_API_PORT"
write_config_key_if_exists "rules_api_path" "RULES_API_PATH"
write_config_key_if_exists "rules_api_method" "RULES_API_METHOD"

RUN_EVERY=""

if [ -z $RUN_EVERY_MINUTES ]; then
	echo "RUN_EVERY_MINUTES not set."
else
	RUN_EVERY="$RUN_EVERY
  minutes: $RUN_EVERY_MINUTES"
fi

if [ -z $RUN_EVERY_SECONDS ]; then
	echo "RUN_EVERY_SECONDS not set."
else
	RUN_EVERY="$RUN_EVERY
  seconds: $RUN_EVERY_SECONDS"
fi

if [ -z $RUN_EVERY_HOURS ]; then
	echo "RUN_EVERY_HOURS not set."
else
	RUN_EVERY="$RUN_EVERY
  hours: $RUN_EVERY_HOURS"
fi

if [ -z $RUN_EVERY_DAYS ]; then
	echo "RUN_EVERY_DAYS not set."
else
	RUN_EVERY="$RUN_EVERY
  days: $RUN_EVERY_DAYS"
fi

BUFFER_TIME=""
if [ -z $BUFFER_TIME_SECONDS ]; then
	echo "BUFFER_TIME_SECONDS not set."
else
	BUFFER_TIME="$BUFFER_TIME
  seconds: $BUFFER_TIME_SECONDS"
fi

if [ -z $BUFFER_TIME_HOURS ]; then
	echo "BUFFER_TIME_HOURS not set."
else
	BUFFER_TIME="$BUFFER_TIME
  hours: $BUFFER_TIME_HOURS"
fi

if [ -z $BUFFER_TIME_DAYS ]; then
	echo "BUFFER_TIME_DAYS not set."
else
	BUFFER_TIME="$BUFFER_TIME
  days: $BUFFER_TIME_DAYS"
fi

if [ -z $BUFFER_TIME ]; then
	BUFFER_TIME_MINUTES=${BUFFER_TIME_MINUTES:-"15"}
fi

if [ -z $BUFFER_TIME_MINUTES ]; then
	echo "BUFFER_TIME_MINUTES not set."
else
	BUFFER_TIME="$BUFFER_TIME
  minutes: $BUFFER_TIME_MINUTES"
fi

ALERT_TIME_LIMIT=""

if [ -z $ALERT_TIME_LIMIT_SECONDS ]; then
	echo "ALERT_TIME_LIMIT_SECONDS not set."
else
	ALERT_TIME_LIMIT="$ALERT_TIME_LIMIT
  seconds: $ALERT_TIME_LIMIT_SECONDS"
fi

if [ -z $ALERT_TIME_LIMIT_HOURS ]; then
	echo "ALERT_TIME_LIMIT_HOURS not set."
else
	ALERT_TIME_LIMIT="$ALERT_TIME_LIMIT
  hours: $ALERT_TIME_LIMIT_HOURS"
fi

if [ -z $ALERT_TIME_LIMIT_MINUTES ]; then
	echo "ALERT_TIME_LIMIT_MINUTES not set."
else
	ALERT_TIME_LIMIT="$ALERT_TIME_LIMIT
  minutes: $ALERT_TIME_LIMIT_MINUTES"
fi

if [ -z $ALERT_TIME_LIMIT ]; then
	ALERT_TIME_LIMIT_DAYS=${ALERT_TIME_LIMIT_DAYS:-"2"}
fi

if [ -z $ALERT_TIME_LIMIT_DAYS ]; then
	echo "ALERT_TIME_LIMIT_DAYS not set."
else
	ALERT_TIME_LIMIT="$ALERT_TIME_LIMIT
  days: $ALERT_TIME_LIMIT_DAYS"
fi

write_config_key "run_every" "$RUN_EVERY"
write_config_key "buffer_time" "$BUFFER_TIME"
write_config_key "es_host" "$ES_HOST"
write_config_key "es_port" "$ES_PORT"
write_config_key "writeback_index" "$ES_INDEX"
write_config_key "alert_time_limit" "$ALERT_TIME_LIMIT"

write_config_key_if_exists "es_url_prefix" "ES_URL_PREFIX"
write_config_key_if_exists "use_ssl" "ES_USE_SSL"
write_config_key_if_exists "verify_certs" "VERIFY_TLS_CERTS"
write_config_key_if_exists "es_send_get_body_as" "ES_HTTP_METHOD"
write_config_key_if_exists "es_username" "ES_USERNAME"
write_config_key_if_exists "es_password" "ES_PASSWORD"
