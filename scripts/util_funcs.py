import re
import unicodedata
import time
import random
from datetime import datetime

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def sleep_if_quick(last_request_time, s_thresh=1, s_from=1, s_to=3):
    """Sleep if `last_request_time` is lower than `s_thresh`.
    Time to sleep is chosen randomly between `s_from` and `s_to`
    """
    if time.time() - last_request_time < s_thresh:
        # Random delay between requests
        delay = random.uniform(s_from, s_to)
        print(f"Waiting for {delay:.2f} seconds before the next request...")
        time.sleep(delay)

def check_months_ago(date_str):
    target_date = datetime.strptime(date_str, "%Y-%m")
    current_date = datetime.now()
    
    # Calculate difference in months accounting for year changes
    months_ago = (current_date.year - target_date.year) * 12 + (current_date.month - target_date.month)
    
    if months_ago > 3:
        print(f"WARNING: Holdings extraction date of {date_str} was {months_ago} months ago. Consider updating holdings cache.")
