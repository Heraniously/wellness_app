from django.contrib import admin
from .models import WellnessClass, Booking

@admin.register(WellnessClass)
class WellnessClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'start_time', 'capacity', 'is_recurring')
    list_filter = ('instructor', 'start_time')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # Remove 'preference_tag' from this list
    list_display = ('client', 'wellness_class', 'payment_type', 'amount_paid', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'payment_type', 'created_at')
    search_fields = ('client__username', 'wellness_class__title')