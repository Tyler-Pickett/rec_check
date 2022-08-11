import argparse
import logging
import sys

from datetime import datetime
from enumerations.date_format import DateFormat

class ArgumentParserCamping(argparse.ArgumentParser):
    def __init(self):
        super().__init__()
        self.add_argument(
            "--debug", "-d", action="store_true", help="Debug log level"
        )
        self.add_argument(
            "--start--date",
            required=True,
            help="Start date [YYYY-MM-DD]",
            type=self.TypeConverter.date,
        )
        self.add_argument(
            "--end--date",
            required=True,
            help="End date [YYYY-MM-DD]. Departure Date.",
            type=self.TypeConverter.date,
        )
        self.add_argument(
            "--nights",
            required=True,
            help="Nights booked(default is all nights in given search).",
            type=self.TypeConverter.positive_int,
        )
        self.add_argument(
            "--campsite-ids",
            type=int,
            nargs="+",
            default=(),
            help="Site specific search",
        )
        self.add_argument(
            "--show-campsite-info",
            action="store_true",
            help="Campsite ID and Available Dates",
        )
        self.add_argument(
            "--campsite-type",
            help="Search by type of campsite.",
        )
        self.add_argument(
            "--json-output",
            action="store_true",
            help=(
                "Turns script's ouput to json file."
                "Output includes more info."
            ),
        )
        parks_group = self.add_mutually_exclusive_group(required=True)
        parks_group.add_argument(
            "--parks",
            dest="parks",
            metavar="park",
            nargs="+",
            help="Park IDs",
            type=int,
        )
        parks_group.add_argument(
            "--stdin",
            "-",
            action="store-_true",
            help="Read list of Park IDs from stdin indstead.",
        )
    
    def parse_args(self, args=None, namespace=None):
        args = super().parse_args(args, namespace)
        args.parks = args.parks or [p.strip() for p in sys.stdin]
        self._validate_args(args)
        return args
    
    @classmethod
    def _validate_args(cls, args):
        if len(args.parks) > 1 and len(args.campsite_ids) > 0:
            raise cls.ArgumentCombinationError(
                "--campsite-ids can only be used with a single park ID."
            )
    
    class TyperConverter:
        @classmethod
        def date(cls, date_str):
            try:
                return datetime.strptime(
                    date_str, DateFormat.INPUT_DATE_FORMAT.value
                )
            except ValueError as e:
                msg = "Not a valid date: '{0}'. ".format(date_str)
                logging.critical(e)
                raise argparse.ArgumentTypeError(msg)
        
        @classmethod
        def positive_int(cls, i):
            i = int(i)
            if i <= 0:
                msg = "Please select a number of Night(s), {0}".format(i)
                raise argparse.ArgumentTypeError(msg)
            return i
    
    class ArgumentCombinationError(Exception):
        pass