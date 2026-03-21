from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('welcome/', views.logged_out_landing, name='logged_out_landing'),
    path('classes/', views.class_list, name='class_list'),

    # Booking Workflow
    # Note: success.html is rendered INSIDE finalize_booking, so no separate URL is needed
    path('finalize-booking/<int:class_id>/',
         views.finalize_booking, name='finalize_booking'),

    # Dashboard & Profile
    path('dashboard/', views.dashboard, name='dashboard'),
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
    path('calendar/month/', views.calendar_month_view, name='calendar_month'),
    path('api/classes/', views.classes_json, name='classes_json'),

    # Community
    path('community/', views.community, name='community'),
    path('community/post/', views.create_post, name='create_post'),
    path('community/post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('community/post/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
    path('community/comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Settings hub
    path('settings/', views.settings_view, name='settings'),

    # Teaching hub (instructors only)
    path('teaching/', views.teaching_hub, name='teaching'),

    # Admin hub (superusers only)
    path('admin-hub/', views.admin_hub, name='admin_hub'),

    # Leaf Management
    path('leaves/', views.buy_leaves, name='buy_leaves'),
    path('leaves/admin/', views.admin_leaves, name='admin_leaves'),
    path('leaves/approve/<int:request_id>/',
         views.approve_leaf_request, name='approve_leaf_request'),
    path('leaves/reject/<int:request_id>/',
         views.reject_leaf_request, name='reject_leaf_request'),
]
