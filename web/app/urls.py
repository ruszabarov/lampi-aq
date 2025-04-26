from django.urls import path
from . import views

urlpatterns = [
	path('history', views.history, name='history'),
	path('dashboard/', views.dashboard, name='dashboard'),
	path('dashboard/pressure/', views.pressure_chart, name='pressure_chart'),
	path('dashboard/temperature/', views.temperature_chart, name='temperature_chart'),
	path('dashboard/humidity/', views.humidity_chart, name='humidity_chart'),
	path('dashboard/pm25/', views.pm25_chart, name='pm25_chart'),
	path('dashboard/pm10/', views.pm10_chart, name='pm10_chart'),
]
