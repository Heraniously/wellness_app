from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('classes/', views.class_list, name='class_list'),

    # Booking Workflow
    # Note: success.html is rendered INSIDE finalize_booking, so no separate URL is needed
    path('finalize-booking/<int:class_id>/',
         views.finalize_booking, name='finalize_booking'),
    path('book/<int:class_id>/', views.book_session, name='book_session'),

    # Dashboard & Profile
    path('dashboard/', views.client_dashboard, name='dashboard'),
    path('signup/', views.SignUpView.as_view(), name='signup'),

    # Instructor Features
    path('instructor/dashboard/', views.instructor_dashboard,
         name='instructor_dashboard'),
    path('instructor-overview/', views.instructor_overview,
         name='instructor_overview'),
    path('instructor/create-class/', views.create_class,
         name='create_class'),  # Added this for your teachers

    # Booking Management
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('toggle-payment/<int:booking_id>/',
         views.toggle_payment_status, name='toggle_payment_status'),

    # Calendar view
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/classes/', views.classes_json, name='classes_json'),

    # Leaf Management
    path('leaves/', views.buy_leaves, name='buy_leaves'),
    path('leaves/admin/', views.admin_leaves, name='admin_leaves'),
    path('leaves/approve/<int:request_id>/',
         views.approve_leaf_request, name='approve_leaf_request'),
    path('leaves/reject/<int:request_id>/',
         views.reject_leaf_request, name='reject_leaf_request'),
]
