from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta


class WellnessClass(models.Model):
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        # Only teachers show up in the list
        limit_choices_to={'is_staff': True},
        related_name='classes_taught',
        null=True,  # Allows existing classes to stay for now
        blank=True
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    start_time = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    duration_minutes = models.PositiveIntegerField(default=60)
    end_time = models.DateTimeField()

    # For automation
    is_recurring = models.BooleanField(default=False)
    day_of_week = models.IntegerField(choices=[
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
    ], null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class Booking(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    wellness_class = models.ForeignKey(WellnessClass, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=[
        ('drop_in', 'Drop-in'),
        ('prepaid', 'Pre-paid (Discounted)')
    ], default='drop_in')
    payment_proof = models.CharField(max_length=100, blank=True, null=True)
    amount_paid = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.client.username} - {self.wellness_class.title} ({self.payment_type})"
