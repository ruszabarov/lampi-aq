from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name='index'),
	path('dashboard/', views.dashboard, name='dashboard'),
	path('dashboard/graph/pressure/', views.graph_pressure, name='graph_pressure'),
	path('dashboard/graph/temperature/', views.graph_temperature, name='graph_temperature'),
	path('dashboard/graph/humidity/', views.graph_humidity, name='graph_humidity'),
	path('dashboard/graph/pm25/', views.graph_pm25, name='graph_pm25'),
	path('dashboard/graph/pm10/', views.graph_pm10, name='graph_pm10'),
]
