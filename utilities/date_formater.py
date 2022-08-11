from datetime import datetime
from enumerations.date_format import DateFormat

def date_format_api(date_object, format_string=DateFormat.ISO_DATE_FORMAT_REQUEST.value):
    date_formatted = datetime.strftime(date_object, format_string)
    return date_formatted

def api_date_to_user_date(date_string):
    date_object = datetime.strptime(date_string, DateFormat.ISO_DATE_FORMAT_RESPONSE)
    return date_format_api(date_object, format_string=DateFormat.INPUT_DATE_FORMAT.value)