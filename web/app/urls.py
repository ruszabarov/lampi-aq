from django.urls import path
from django.contrib.auth import views as auth_views
from .forms import LoginForm
from . import views

urlpatterns = [
  path('login/', auth_views.LoginView.as_view(template_name='login.html', authentication_form=LoginForm), name='login'),
  path('logout/', auth_views.LogoutView.as_view(), name='logout'),
  path('', views.index, name='index'),
	path('history/', views.history, name='history'),
  path('dashboard/', views.dashboard, name='dashboard'),
  path('reading/<int:reading_id>/', views.reading_detail, name='reading_detail'),
  path('add/', views.AddLampiView.as_view(), name='add'),
]
