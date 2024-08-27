import csv
import phonenumbers
from phonenumbers import timezone
from datetime import datetime, timedelta
import pytz
from collections import deque

def read_phone_numbers(file_path):
    with open(file_path, newline='') as csvfile:
        return [row[0] for row in csv.reader(csvfile)]

def get_time_zones(phone_number):
    parsed_number = phonenumbers.parse(phone_number, "US")
    return timezone.time_zones_for_number(parsed_number)

def calculate_overlap_window(tz1, tz2):
    tz1_start = datetime.strptime("09:00:00", "%H:%M:%S").replace(tzinfo=pytz.timezone(tz1))
    tz1_end = datetime.strptime("20:00:00", "%H:%M:%S").replace(tzinfo=pytz.timezone(tz1))
    tz2_start = datetime.strptime("09:00:00", "%H:%M:%S").replace(tzinfo=pytz.timezone(tz2))
    tz2_end = datetime.strptime("20:00:00", "%H:%M:%S").replace(tzinfo=pytz.timezone(tz2))
    
    overlap_start = max(tz1_start, tz2_start)
    overlap_end = min(tz1_end, tz2_end)
    
    return overlap_start.astimezone(pytz.utc).time(), overlap_end.astimezone(pytz.utc).time()

def calculate_calling_window(phone_number):
    tzs = get_time_zones(phone_number)
    if len(tzs) == 1:
        start_window = datetime.strptime("09:00:00", "%H:%M:%S").replace(tzinfo=pytz.timezone(tzs[0]))
        end_window = datetime.strptime("20:00:00", "%H:%M:%S").replace(tzinfo=pytz.timezone(tzs[0]))
        start_window = start_window.astimezone(pytz.utc)
        end_window = end_window.astimezone(pytz.utc)
    else:
        start_time, end_time = calculate_overlap_window(tzs[0], tzs[1])
        start_window = datetime.combine(datetime.utcnow().date(), start_time).replace(tzinfo=pytz.utc)
        end_window = datetime.combine(datetime.utcnow().date(), end_time).replace(tzinfo=pytz.utc)
    
    return start_window, end_window

def schedule_calls(phone_numbers, start_time):
    call_queue = deque()
    for number in phone_numbers:
        try:
            start_window, end_window = calculate_calling_window(number)
        except phonenumbers.phonenumberutil.NumberParseException:
            continue
        except pytz.exceptions.UnknownTimeZoneError:
            continue
        call_queue.append((number, start_window, end_window))

    total_calling_minutes = 0
    total_waiting_minutes = 0
    current_time = datetime.strptime(start_time, "%H:%M:%S").replace(tzinfo=pytz.utc)
    
    while call_queue:
        initial_queue_size = len(call_queue)
        number, start_window, end_window = call_queue.popleft()

        # Adjust the calling window if the day has passed
        if current_time > start_window:
            start_window += timedelta(days=1)
            end_window += timedelta(days=1)
        
        if start_window.time() <= current_time.time() <= end_window.time():
            # If within the allowed calling window, make the call
            total_calling_minutes += 3
            current_time += timedelta(minutes=3)
        else:
            if current_time < start_window:
                # Calculate the wait time until the next available window
                wait_time = (start_window - current_time).total_seconds() / 60
                total_waiting_minutes += wait_time
                current_time = start_window  # Move current time to the start of the next window

            # Requeue the number
            call_queue.append((number, start_window, end_window))
        
        # If the queue size has not reduced after a full iteration, move time forward
        if len(call_queue) == initial_queue_size:
            next_start_time = min([start for _, start, _ in call_queue])
            wait_time = (next_start_time - current_time).total_seconds() / 60
            total_waiting_minutes += wait_time
            current_time = next_start_time

    return total_calling_minutes, total_waiting_minutes, current_time

def format_total_time(total_minutes):
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    return f"{days} days and {hours} hours"

# Input
start_time = "21:30:00"
phone_numbers = read_phone_numbers('phone_numbers.csv')

# Calculate
calling_minutes, waiting_minutes, end_time = schedule_calls(phone_numbers, start_time)

# Output
total_minutes = calling_minutes + waiting_minutes
total_time = format_total_time(total_minutes)

print("Agent Call Duration (in minutes):", calling_minutes)
print("Agent Wait Duration (in minutes):", waiting_minutes)
print("Total Time to Complete Calls:", total_time)
