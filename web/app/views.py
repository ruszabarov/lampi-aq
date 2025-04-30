from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from app.models import Lampi, SensorReading
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.embed import components
from bokeh.plotting import figure
from math import pi
from bokeh.layouts import gridplot
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
from app.forms import AddLampiForm
from django.views import generic


@login_required
def index(request):
    devices = Lampi.objects.filter(user=request.user)
    # default to first device if none selected
    device_id = request.GET.get(
        "device",
        devices.first().device_id if devices.exists() else None
    )
    # fetch the most recent reading
    reading = SensorReading.objects.filter(
        lampi__device_id=device_id
    ).order_by("-timestamp").first()

    context = {
        "devices": devices,
        "device_id": device_id,
        "reading": reading,
    }

    template = (
        "partials/sensor-readings-grid.html"
        if request.htmx
        else "index.html"
    )
    return render(request, template, context)

@login_required
def history(request):
    devices = Lampi.objects.filter(user=request.user)
    device = request.GET.get("device", devices.first().device_id)
    
    print(device)

    sensor_readings = SensorReading.objects.filter(lampi=device).order_by('-timestamp')

    start_date_str = request.GET.get('start_date', '')
    if start_date_str:
        sd = parse_date(start_date_str)
        if sd:
            sensor_readings = sensor_readings.filter(
                timestamp__date__gte=sd
            )

    end_date_str = request.GET.get('end_date', '')
    if end_date_str:
        ed = parse_date(end_date_str)
        if ed:
            sensor_readings = sensor_readings.filter(
                timestamp__date__lte=ed
            )

    paginator = Paginator(sensor_readings, 100)
    page_number = request.GET.get('page', 1)
    sensor_readings_page = paginator.get_page(page_number)

    context = {
        'devices': devices,
        "device": device,
        'sensor_readings': sensor_readings_page,
    }

    # HTMX fragment
    if request.headers.get('HX-Request'):
        return render(
            request,
            'partials/sensor-readings-rows.html',
            context
        )

    return render(request, 'history.html', context)


@login_required
def dashboard(request):
    devices = Lampi.objects.filter(user=request.user)
    device = request.GET.get("device", devices.first().device_id)

    readings = (
        SensorReading.objects
        .filter(lampi=device)
        .order_by("-timestamp")
    )
    timestamps = [r.timestamp for r in readings]

    metrics = [
        ("Temperature", "temperature", "°C", "0.0"),
        ("Pressure", "pressure", "hPa", "0.0"),
        ("Humidity", "humidity", "%", "0.0"),
        ("Altitude", "altitude", "m", "0.0"),
        ("PM2.5", "pm25", "µg/m³", "0.0"),
        ("PM10", "pm10", "µg/m³", "0.0"),
    ]

    figs = []
    for title, field, unit, fmt in metrics:
        values = [getattr(r, field) for r in readings]
        cds = ColumnDataSource(data=dict(ts=timestamps, val=values))

        p = figure(
            height=240,
            x_axis_type="datetime",
            toolbar_location=None,
            sizing_mode="stretch_width",
        )

        # minimal styling
        p.line(
            source=cds,
            x="ts",
            y="val",
            line_width=2,
            line_color="#0072B2",
        )
        p.outline_line_color = None
        p.background_fill_color = None
        p.min_border = 5

        # axes
        for ax in (p.xaxis, p.yaxis):
            ax.axis_line_color = None
            ax.major_tick_line_color = None
            ax.major_label_text_font_size = "9pt"
            ax.major_label_text_color = "#555"

        p.xaxis.major_label_orientation = pi / 4

        # optional lightweight title
        p.title.text = f"{title}"
        p.title.text_font_size = "10pt"
        p.title.align = "left"
        p.title.text_color = "#333"

        hover = HoverTool(
            tooltips=[
                ("Time", "@ts{%F %T}"),
                (title, f"@val{{0,{fmt}}}{unit}"),
            ],
            formatters={"@ts": "datetime"},
            mode="vline",
        )
        p.add_tools(hover)

        figs.append(p)

    # 2-column responsive grid
    grid = gridplot(figs, ncols=2, sizing_mode="stretch_width")

    script, div = components(grid)
    context = {
        "devices": devices,
        "device": device,
        "bokeh_script": script,
        "bokeh_div": div,
    }

    template = "partials/sensor-readings-plot.html" if request.htmx \
               else "dashboard.html"
    return render(request, template, context)

@login_required
def reading_detail(request, reading_id):
    # Get the specific reading
    reading = SensorReading.objects.get(id=reading_id)

    # Security check - only allow access to readings from user's devices
    if reading.lampi.user != request.user:
        return HttpResponseForbidden("You don't have permission to view this reading")

    # Get the selected metric from query parameters
    metric = request.GET.get("metric", "temperature")
    
    # Define metric parameters
    metric_params = {
        'temperature': {'name': 'Temperature', 'field': 'temperature', 'unit': '°C', 'fmt': '0.0'},
        'pressure': {'name': 'Pressure', 'field': 'pressure', 'unit': 'hPa', 'fmt': '0.0'},
        'humidity': {'name': 'Humidity', 'field': 'humidity', 'unit': '%', 'fmt': '0.0'},
        'altitude': {'name': 'Altitude', 'field': 'altitude', 'unit': 'm', 'fmt': '0.0'},
        'pm25': {'name': 'PM2.5', 'field': 'PM2.5', 'unit': 'µg/m³', 'fmt': '0.0'},
        'pm10': {'name': 'PM10', 'field': 'PM10', 'unit': 'µg/m³', 'fmt': '0.0'},
    }
    
    # Get parameters for the selected metric
    params = metric_params.get(metric, metric_params['temperature'])
    field = params['field']
    
    # Get more readings for historical graph (about a day's worth but limit to 1000)
    time_threshold = timezone.now() - timezone.timedelta(days=1)
    historical_readings = SensorReading.objects.filter(
        lampi=reading.lampi,
        timestamp__gte=time_threshold
    ).order_by('timestamp')[:1000]
    
    # Create the Bokeh plot
    timestamps = [r.timestamp for r in historical_readings]
    values = [getattr(r, metric) for r in historical_readings]
    
    cds = ColumnDataSource(data=dict(ts=timestamps, val=values))
    
    p = figure(
        height=300,
        x_axis_type="datetime",
        toolbar_location="above",
        sizing_mode="stretch_width",
    )
    
    # Add the line
    p.line(
        source=cds,
        x="ts",
        y="val",
        line_width=2,
        line_color="#0072B2",
    )
    
    # Style the plot
    p.outline_line_color = None
    p.background_fill_color = None
    p.min_border = 20
    
    # Axes styling
    for ax in (p.xaxis, p.yaxis):
        ax.axis_line_color = None
        ax.major_tick_line_color = None
        ax.major_label_text_font_size = "9pt"
        ax.major_label_text_color = "#555"
    
    p.xaxis.major_label_orientation = pi / 4
    
    # Add title
    p.title.text = f"{params['name']} History"
    p.title.text_font_size = "12pt"
    p.title.align = "center"
    p.title.text_color = "#333"
    
    # Add hover tool
    hover = HoverTool(
        tooltips=[
            ("Time", "@ts{%F %T}"),
            (params['name'], f"@val{{0,{params['fmt']}}}{params['unit']}"),
        ],
        formatters={"@ts": "datetime"},
        mode="vline",
    )
    p.add_tools(hover)
    
    # Highlight the current reading
    current_timestamp = reading.timestamp
    current_value = getattr(reading, metric)
    p.circle([current_timestamp], [current_value], size=8, color="red", alpha=0.8)
    
    # Generate the script and div components for the template
    script, div = components(p)
    
    context = {
        'reading': reading,
        'metric_name': params['name'],
        'value': getattr(reading, metric),
        'unit': params['unit'],
        'bokeh_script': script,
        'bokeh_div': div,
    }
    
    return render(request, 'reading_detail.html', context)

class AddLampiView(LoginRequiredMixin, generic.FormView):
    template_name = 'addlampi.html'
    form_class = AddLampiForm
    success_url = ''

    def get_context_data(self, **kwargs):
        context = super(AddLampiView, self).get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        device = form.cleaned_data['device']
        device.associate_and_publish_associated_msg(self.request.user)

        return super(AddLampiView, self).form_valid(form)