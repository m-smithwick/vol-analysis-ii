import datetime
import pytz
from datetime import datetime, timedelta

# Create a naive datetime (no timezone info)
d1 = datetime(2025, 10, 17, 0, 0, 0)
print(f'Naive: {d1}, timestamp: {d1.timestamp()}')

# Create a timezone-aware datetime
eastern_tz = pytz.timezone('US/Eastern')
d2 = datetime(2025, 10, 16, 12, 19, 57, tzinfo=eastern_tz)
print(f'Aware: {d2}, timestamp: {d2.timestamp()}')

# Try to compare (will fail)
try:
    print(f'Compare (will fail): {d1 > d2}')
except TypeError as e:
    print(f'Error: {e}')

# Proper comparison methods
print(f'Proper compare (naive to naive): {d1 > d2.replace(tzinfo=None)}')
print(f'Proper compare (aware to aware): {d1.replace(tzinfo=pytz.UTC) > d2.astimezone(pytz.UTC)}')

# Test with the specific dates from the error message
print("\nTesting the error case scenario:")
ts1 = 1760673600  # startDate from error
ts2 = 1760631597  # endDate from error
date1 = datetime.fromtimestamp(ts1)
date2 = datetime.fromtimestamp(ts2)
print(f'From timestamp 1: {date1} (naive)')
print(f'From timestamp 2: {date2} (naive)')
print(f'Naive comparison: {date1 > date2}')

# Check with timezone awareness
date1_aware = datetime.fromtimestamp(ts1, tz=pytz.UTC)
date2_aware = datetime.fromtimestamp(ts2, tz=pytz.UTC)
print(f'From timestamp 1: {date1_aware} (aware)')
print(f'From timestamp 2: {date2_aware} (aware)')
print(f'Aware comparison: {date1_aware > date2_aware}')

# Simulate the scenario in analyze_multiple_days function
current_date = datetime(2025, 10, 16)
date_from = current_date - timedelta(days=1)
date_to = current_date + timedelta(days=1)
print(f"\nIn analyze_multiple_days function:")
print(f"current_date: {current_date}")
print(f"date_from: {date_from}")
print(f"date_to: {date_to}")

# Add timezone info to one but not the other
current_date_aware = current_date.replace(tzinfo=pytz.UTC)
print(f"current_date with TZ: {current_date_aware}")

# Try to compare
try:
    result = date_from <= current_date_aware <= date_to
    print(f"Comparison result: {result}")
except TypeError as e:
    print(f"Comparison error: {e}")
