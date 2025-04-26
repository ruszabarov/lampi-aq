import datetime
import json
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from app.models import SensorReading

@login_required
def index(request):
    sensor_readings = SensorReading.objects.filter(
        lampi__user=request.user
    ).order_by('-timestamp')
    
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    if start_date_str:
        start_date = parse_date(start_date_str)
        if start_date:
            sensor_readings = sensor_readings.filter(timestamp__date__gte=start_date)
    
    if end_date_str:
        end_date = parse_date(end_date_str)
        if end_date:
            sensor_readings = sensor_readings.filter(timestamp__date__lte=end_date)
    
    paginator = Paginator(sensor_readings, 100)
    page_number = request.GET.get('page', 1)
    sensor_readings_page = paginator.get_page(page_number)
    
    context = {'sensor_readings': sensor_readings_page}
    
    if request.headers.get('HX-Request'):
        return render(request, 'partials/sensor-readings-rows.html', context)
    
    return render(request, 'history.html', context)

@login_required
def dashboard(request):
    return render(request, "dashboard.html")

def get_sensor_data(request):
    """
    Helper function that returns data for the past 24 hours in JSON-ready format.
    """
    now = timezone.now()
    yesterday = now - datetime.timedelta(days=1)
    sensor_readings = SensorReading.objects.filter(
        lampi__user=request.user, timestamp__gte=yesterday
    ).order_by('timestamp')
    # Prepare lists for timestamps and each sensor reading
    timestamps = [reading.timestamp.strftime("%Y-%m-%dT%H:%M:%S") for reading in sensor_readings]
    pressure_data = [reading.pressure for reading in sensor_readings]
    temperature_data = [reading.temperature for reading in sensor_readings]
    humidity_data = [reading.humidity for reading in sensor_readings]
    pm25_data = [reading.pm25 for reading in sensor_readings]
    pm10_data = [reading.pm10 for reading in sensor_readings]

    return {
        "timestamps": json.dumps(timestamps),
        "pressure_data": json.dumps(pressure_data),
        "temperature_data": json.dumps(temperature_data),
        "humidity_data": json.dumps(humidity_data),
        "pm25_data": json.dumps(pm25_data),
        "pm10_data": json.dumps(pm10_data),
    }

@login_required
def graph_pressure(request):
    data = get_sensor_data(request)
    return render(request, "partials/graph_pressure.html", data)

@login_required
def graph_temperature(request):
    data = get_sensor_data(request)
    return render(request, "partials/graph_temperature.html", data)

@login_required
def graph_humidity(request):
    data = get_sensor_data(request)
    return render(request, "partials/graph_humidity.html", data)

@login_required
def graph_pm25(request):
    data = get_sensor_data(request)
    return render(request, "partials/graph_pm25.html", data)

@login_required
def graph_pm10(request):
    data = get_sensor_data(request)
    return render(request, "partials/graph_pm10.html", data)