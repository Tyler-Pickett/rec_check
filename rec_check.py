import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
#import datetime

from itertools import count, groupby
#from dateutil.rrule import rrule
import dateutil

from clients.rec_client import RecClient
from enumerations.date_format import DateFormat
from enumerations.outcome import Outcome
from utilities import date_formater
from utilities.argument_parser_camping import ArgumentParserCamping

LOG = logging.getLogger(__name__)
log_formatter = logging.Formatter("%(asctime)s - %(process)s - %(levelname)s - %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(log_formatter)
LOG.addHandler(sh)

def park_info(park_id, start_date, end_date, campsite_type=None, campsite_ids=()):
    start_of_month = datetime(start_date.year, start_date.month, 1)
    months = list(rrule.rrule(rrule.MONTHLY, dtstart=start_of_month, until=end_date))
   
    api_data = []
    for month_date in months:
        api_data.append(RecClient.get_availability(park_id, month_date))
   
    data = {}
    for month_data in api_data:
        for campsite_id, campsite_data in month_data["campsites"].items():
            available = []
            a = data.setdefault(campsite_id, [])
            for date, availability_value in campsite_data["availabilities"].items():
                if availability_value != "Available":
                    continue
                if (campsite_type and campsite_type != campsite_data["campsite_type"]):
                    continue
                if (len(campsite_ids) > 0
                    and int(campsite_data["campsite_id"]) not in campsite_ids):
                    continue
                available.append(date)
            if available:
                a += available
    return data

def total_sites(park_information, start_date, end_date, nights=None):
    maximum = len(park_information)
    total_available = 0
    total_days = (end_date - start_date).days
    dates = [end_date - timedelta(days=i) for i in range(1, total_days+1)]
    dates = set(
            date_formater.date_format_api(
                i, format_string=DateFormat.ISO_DATE_FORMAT_RESPONSE.value
                )
            for i in dates
            )
    if nights not in range(1, total_days+1):
        nights = total_days
        LOG.debug("Setting number of nights to {}.".format(nights))
    
    available_dates_by_id = defaultdict(list)
    for site, availabilites in park_information.items():
        dates_available = []
        for date in availabilites:
            if date not in dates:
                continue
            dates_available.append(date)
            if not dates_available:
                continue
            correct_consecutive_ranges = consecutive(dates_available, nights)
            if correct_consecutive_ranges:
                total_available += 1
                LOG.debug("Available site {}: {}".format(total_available, site))
            
            for r in correct_consecutive_ranges:
                start, end = r
                available_dates_by_id[int(site)].append({"start": start, "end": end})
            
            return total_available, maximum, available_dates_by_id

def consecutive(available, nights):
    ordinal_dates = [
        datetime.strptime(dstr, DateFormat.ISO_DATE_FORMAT_RESPONSE.value).toordinal()
        for dstr in available
    ]
    
    c = count()
    consecutive_ranges = list(list(n) for _, n in groupby(ordinal_dates, lambda x: x - next(c)))
    enough_consecutive = []
    
    for r in consecutive_ranges:
        if len(r) < nights:
            continue
        for start_index in range(0, len(r) - nights + 1):
            start_night = date_formater.format_date(
                datetime.fromordinal(r[start_index]),
                format_string=DateFormat.INPUT_DATE_FORMAT.value
                )
            end_night = date_formater.format_date(
                datetime.fromordinal(r[start_index + nights - 1] + 1),
                format_string=DateFormat.INPUT_DATE_FORMAT.value
            )
            enough_consecutive.append(start_night, end_night)
    
    return enough_consecutive

def park_check(park_id, start_date, end_date, campsite_type, campsite_ids=(), nights=None):
    park_information = park_info(park_id, start_date, end_date, campsite_type, campsite_ids)
    LOG.debug("Info for park {}: {}".format(park_id, json.dumps(park_information, indent=3)))

    park_name = RecClient.get_park_name(park_id)
    current, maximum, availabilities_filtered = total_sites(park_information, start_date, end_date, nights=nights)

    return current, maximum, availabilities_filtered, park_name

def user_output(info_by_park_id, start_date, end_date, gen_campsite_info=False):
    out = []
    has_availabilities = False

    for park_id, info in info_by_park_id.items():
        current, maximum, available_dates_site_id, park_name = info
        if current:
            emoji = Outcome.succes.value
            has_availabilities = True
        else:
            emoji = Outcome.failure.value
        out.append(
            "{emoji} {park_name} ({park_id}): {current} sites available out of {maximum} sites".format(
                emoji = emoji,
                park_name = park_name,
                park_id = park_id,
                current = current,
                maximum = maximum
            )
        )

        if gen_campsite_info and available_dates_site_id:
            for site_id, dates in available_dates_site_id.items():
                out.append(" * Site {site_id} is available on the following dates:".format(site_id = site_id))
                for date in dates:
                    out.append(" * {start} -> {end}".format(start = date["start"], end = date["end"]))
        
    if has_availabilities:
        out.insert(
            0,
            "Campsites available from {start} to {end}.".format(
                start = start_date.strftime(DateFormat.INPUT_DATE_FORMAT.value),
                end = end_date.strftime(DateFormat.INPUT_DATE_FORMAT.value),
            ),
        )
    else:
        out.insert(0, "No campsites available: ")
    return "\n".join(out), has_availabilities

def json_data(info_by_park_id):
    available_by_park_id = {}
    has_availabilities = False
    for park_id, info in info_by_park_id.items():
        current, _, available_dates_site_id, _ = info
        if current:
            has_availabilities = True
            available_by_park_id[park_id] = available_dates_site_id
    return json.dumps(available_by_park_id), has_availabilities

def main(parks, json_output=False):
    info_by_park_id = {}
    for park_id in parks:
        info_by_park_id[park_id] = park_check(
            park_id,
            args.start_date,
            args.end_date,
            args.campsite_type,
            args.campsite_ids,
            nights=args.nights
        )
    if json_output:
        output, has_availabilities = json_data(info_by_park_id)
    else:
        output, has_availabilities = user_output(
            info_by_park_id,
            args.start_date,
            args.end_date,
            args.show_campsite_info
        )
    print(output)
    return has_availabilities

if __name__ == "__main__":
    parser = ArgumentParserCamping()
    args = parser.parse_args()

    if args.debug:
        LOG.setLevel(logging.DEBUG)
    
    main(args.parks, json_output=args.json_output)