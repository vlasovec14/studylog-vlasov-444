from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('course/add/', views.course_form, name='course_add'),
    path('course/<int:pk>/edit/', views.course_form, name='course_edit'),
    path('course/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('course/<int:course_pk>/note/', views.note_form, name='note_add'),
    path('note/<int:pk>/edit/', views.note_form, name='note_edit'),
    path('note/<int:pk>/delete/', views.note_delete, name='note_delete'),
]
