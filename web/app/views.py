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
