from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
]
