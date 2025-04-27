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
from bokeh.layouts import column, gridplot


@login_required
def history(request):
    # All of this user’s devices
    devices = Lampi.objects.filter(user=request.user)

    # Base queryset: only readings from this user’s devices
    sensor_readings = SensorReading.objects.filter(
        lampi__user=request.user
    ).order_by('-timestamp')

    # Optional device filter
    device_id = request.GET.get('device_id', '')
    if device_id.isdigit():
        sensor_readings = sensor_readings.filter(lampi_id=device_id)

    # Date filters as before
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

    # Pagination
    paginator = Paginator(sensor_readings, 100)
    page_number = request.GET.get('page', 1)
    sensor_readings_page = paginator.get_page(page_number)

    context = {
        'devices': devices,
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