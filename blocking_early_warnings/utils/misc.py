"""
    Miscelaneous utility functions
"""
# Django imports
from django.db.models import Model

# Local imports
from blocking_early_warnings.settings import DATE_FORMAT

# Python imports
from typing import Type, List, Callable, Any
from datetime import datetime, timedelta
from pytz import utc


def get_hour_from_str(str_time: str) -> datetime:
    """
    Return a datetime with the same datetime in the str
    but with minutes, seconds, and microseconds truncated
    """
    time = datetime.strptime(str_time, DATE_FORMAT)
    hour = get_hour(time)

    return hour.replace(tzinfo=utc)


def get_hour(time: datetime) -> datetime:
    """
    Return the same datetime object but with minutes, seconds,
    microseconds truncated
    """
    return time.replace(minute=0, second=0, microsecond=0)


class Accumulator:
    """
    Object holding a set of
    elements to be processed by a function once a
    certain ammount of elements is reached
    """

    def __init__(
        self,
        callback: Callable[[List[Any]], Any],
        queue: List[Any] = [],
        treshold: int = 1000,
    ):
        """
        Parameters:
            + callback : Function([Any]) -> Any = function to call in stored queue once it's full
            + queue : [Any] = default object set
            + treshold : int = how many elements until a flush occurs
        """
        assert treshold > 0, "Treshold should be positive"
        self.queue = queue
        self.treshold = treshold
        self.callback = callback

    def add(self, m: Model):
        """
        Add an object to be bulk-processed by the given
        callback function.
        """
        self.queue.append(m)
        if len(self.queue) > self.treshold:
            self.flush()

    def flush(self):
        """
        Call callback function and empty stored queue
        """
        self.callback(self.queue)
        self.queue = []

    def __del__(self):
        self.flush()
