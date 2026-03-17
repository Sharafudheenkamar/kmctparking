from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # User URLs
    path('user/register/', views.user_register, name='user_register'),
    path('user/login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='logout'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('book/', views.book_slot, name='book_slot'),
    path('cancel/<uuid:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('payment/<uuid:booking_id>/', views.payment, name='payment'),
    
    # Admin URLs
    path('administrator/register/', views.admin_register, name='admin_register'),
    path('administrator/login/', views.admin_login, name='admin_login'),
    path('administrator/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('administrator/slots/', views.manage_slots, name='manage_slots'),
    path('administrator/slots/update/<int:slot_id>/', views.update_slot, name='update_slot'),
    path('administrator/slots/delete/<int:slot_id>/', views.delete_slot, name='delete_slot'),
    
    # API URLs for Arduino
    path('api/slots/status/', views.get_slot_status, name='get_slot_status'),
    path('api/slots/update/', views.update_slot_status, name='update_slot_status'),

    # API URLs for Arduino integration
    path('api/slots/status/', views.get_slot_status, name='get_slot_status'),
    path('api/slots/update/', views.update_slot_status_api, name='update_slot_status_api'),
]
