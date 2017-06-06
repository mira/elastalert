import re


def convert_to_camel_case(snake_str, capitalize_first=False):

	def capitalize_letter(match):
		return match.group(1).upper()

	camel_str = re.sub(
		r'[_\-\s]+(\w|$)',
		capitalize_letter,
		snake_str.lower().strip()
	)

	if capitalize_first:
		return camel_str[0:1].upper() + camel_str[1:]
	else:
		return camel_str[0:1].lower() + camel_str[1:]


def convert_to_snake_case(camel_str):
	return re.sub(
		r'^[_\s\-]+|[_\s\-]+$',
		r'',
		re.sub(
			r'[\s\-_]+',
			r'_',
			re.sub(r'(?<!^)([A-Z])', r'_\1', camel_str.strip())
		)
	).lower()
