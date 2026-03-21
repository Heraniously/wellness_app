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
        ('leaf', 'Leaf (online)'),
        ('drop_in', 'Drop-in (in person)'),
    ], default='drop_in')
    payment_proof = models.CharField(max_length=100, blank=True, null=True)
    amount_paid = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.00)
    note = models.TextField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.client.username} - {self.wellness_class.title} ({self.payment_type})"


class UserProfile(models.Model):
    TOUCH_PREFERENCE_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('ask', 'Ask me first'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    touch_preference = models.CharField(
        max_length=10,
        choices=TOUCH_PREFERENCE_CHOICES,
        default='ask'
    )
    long_term_conditions = models.TextField(max_length=500, blank=True)
    movement_limitations = models.TextField(max_length=500, blank=True)

    PRACTICE_GOAL_CHOICES = [
        ('stress_relief', 'Stress relief'),
        ('mobility', 'Mobility'),
        ('strength', 'Strength'),
        ('pain_management', 'Pain management'),
        ('recovery', 'Recovery'),
    ]
    practice_goal = models.CharField(
        max_length=20,
        choices=PRACTICE_GOAL_CHOICES,
        blank=True
    )

    INTENSITY_PREFERENCE_CHOICES = [
        ('gentle', 'Gentle'),
        ('moderate', 'Moderate'),
        ('dynamic', 'Dynamic'),
    ]
    intensity_preference = models.CharField(
        max_length=12,
        choices=INTENSITY_PREFERENCE_CHOICES,
        blank=True
    )

    ADJUSTMENT_PREFERENCE_CHOICES = [
        ('ask_each_class', 'Ask each class'),
        ('verbal_only', 'Verbal only'),
        ('hands_off', 'Hands-off'),
    ]
    adjustment_preference = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_PREFERENCE_CHOICES,
        blank=True
    )

    instructor_notes = models.TextField(max_length=300, blank=True)
    consent_share_health_info = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} profile"

# Tracks how many leaves each user has


class LeafBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    leaves = models.PositiveIntegerField(default=0)

# When user requests to buy leaves


class LeafRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leaves_requested = models.PositiveIntegerField()
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2)
    payment_proof = models.ImageField(upload_to='payment_proofs/')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def approve(self):
        balance, _ = LeafBalance.objects.get_or_create(user=self.user)
        balance.leaves += self.leaves_requested
        balance.save()
        self.status = 'approved'
        self.save()


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-pinned', '-created_at']

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post_id}"


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} likes {self.post_id}"
