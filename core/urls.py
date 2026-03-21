from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from scheduling.views import PendingAwareLoginView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', PendingAwareLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('scheduling.urls')), # This makes the home page your class list
]