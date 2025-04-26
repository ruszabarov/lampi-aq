import datetime
import json
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from app.models import SensorReading

@login_required
def history(request):
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

def _get_chart_data(user, field_name):
    qs = SensorReading.objects.filter(lampi__user=user).order_by('-timestamp')
    data = list(qs.values_list('timestamp', field_name))
    # reverse so oldest→newest
    timestamps = [ts.strftime("%Y-%m-%d %H:%M") for ts, _ in reversed(data)]
    values     = [val for _, val in reversed(data)]
    return json.dumps(timestamps), json.dumps(values)


def pressure_chart(request):
    labels, values = _get_chart_data(request.user, 'pressure')
    return render(request, 'partials/chart.html', {
        'chart_id':    'pressureChart',
        'chart_label': 'Pressure (hPa)',
        'labels':      labels,
        'values':      values,
    })


def temperature_chart(request):
    labels, values = _get_chart_data(request.user, 'temperature')
    return render(request, 'partials/chart.html', {
        'chart_id':    'temperatureChart',
        'chart_label': 'Temperature (°C)',
        'labels':      labels,
        'values':      values,
    })


def humidity_chart(request):
    labels, values = _get_chart_data(request.user, 'humidity')
    return render(request, 'partials/chart.html', {
        'chart_id':    'humidityChart',
        'chart_label': 'Humidity (%)',
        'labels':      labels,
        'values':      values,
    })


def pm25_chart(request):
    labels, values = _get_chart_data(request.user, 'pm25')
    return render(request, 'partials/chart.html', {
        'chart_id':    'pm25Chart',
        'chart_label': 'PM2.5 (µg/m³)',
        'labels':      labels,
        'values':      values,
    })


def pm10_chart(request):
    labels, values = _get_chart_data(request.user, 'pm10')
    return render(request, 'partials/chart.html', {
        'chart_id':    'pm10Chart',
        'chart_label': 'PM10 (µg/m³)',
        'labels':      labels,
        'values':      values,
    })