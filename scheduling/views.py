# We need to create a "view" that handles the logic of what happens when a user clicks that button.
from urllib import request
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import WellnessClass, Booking, LeafBalance, LeafRequest, Post, Comment, Like
from django.urls import reverse_lazy
from django.views import generic
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import timedelta, datetime
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .forms import ProfessionalSignUpForm
from decimal import Decimal
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from django.db.models import Count

BUCHAREST = ZoneInfo('Europe/Bucharest')


class SignUpView(generic.CreateView):
    form_class = ProfessionalSignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # Save the user to the database first
        user = form.save()
        # ALWAYS add every new user to the 'Clients' group
        client_group, created = Group.objects.get_or_create(name='Client')
        user.groups.add(client_group)

        # 3. If they checked the 'instructor' box, add extra powers
        if form.cleaned_data.get('is_instructor'):
            # Assign them to the Instructors group
            instructor_group, created = Group.objects.get_or_create(
                name='Instructor')
            user.groups.add(instructor_group)

            messages.info(
                self.request,
                "Thanks! Your instructor account is pending admin approval."
            )

        return super().form_valid(form)


def home(request):
    return render(request, 'scheduling/home.html')


def class_list(request):
    # This gets all classes to show to the clients
    classes = WellnessClass.objects.filter(
        start_time__gt=timezone.now()).order_by('start_time')

    # Logic to identify full classes
    for c in classes:
        # Calculate remaining spots: Total Capacity - Number of current Bookings
        c.spots_left = c.capacity - c.booking_set.count()
        c.is_full = c.spots_left <= 0

    # If user is logged in, get their booked class IDs to prevent double booking
    user_booked_ids = []
    if request.user.is_authenticated:
        user_booked_ids = request.user.booking_set.values_list(
            'wellness_class_id', flat=True)

    return render(request, 'scheduling/class_list.html', {
        'classes': classes,
        'user_booked_ids': user_booked_ids
    })


def client_dashboard(request):
    now = timezone.now()
    if not request.user.is_authenticated:
        # Logged-out dashboard: welcome + CTAs
        return render(request, 'scheduling/dashboard.html', {
            'is_guest': True,
        })

    # Logged-in: compute upcoming/past, streak, totals, favorite class type
    upcoming = Booking.objects.filter(
        client=request.user,
        wellness_class__start_time__gt=now
    ).order_by('wellness_class__start_time')
    past = Booking.objects.filter(
        client=request.user,
        wellness_class__start_time__lte=now
    )
    leaf_balance, _ = LeafBalance.objects.get_or_create(user=request.user)

    # Total attended classes
    total_attended = past.count()

    # Favorite class type (by title)
    favorite_class = (
        past.values('wellness_class__title')
        .annotate(c=Count('id'))
        .order_by('-c')
        .first()
    )
    favorite_class_title = favorite_class['wellness_class__title'] if favorite_class else None

    # Weekly streak: consecutive calendar weeks with >=1 booking
    week_set = set()
    for booking in past:
        dt = booking.wellness_class.start_time
        year, week, _ = dt.isocalendar()
        week_set.add((year, week))

    if week_set:
        current_year, current_week, _ = now.isocalendar()
        streak = 0
        year, week = current_year, current_week
        while (year, week) in week_set:
            streak += 1
            week -= 1
            if week == 0:
                year -= 1
                week = 52
    else:
        streak = 0

    # Instructor section: upcoming classes they teach
    instructor_classes = []
    if request.user.is_staff:
        instructor_classes = WellnessClass.objects.filter(
            instructor=request.user,
            start_time__gt=now
        ).order_by('start_time')

    return render(request, 'scheduling/dashboard.html', {
        'is_guest': False,
        'upcoming': upcoming,
        'past': past,
        'now_plus_24h': now + timedelta(hours=24),
        'leaf_balance': leaf_balance,
        'leaf_price_eur': settings.LEAF_PRICE_EUR,
        'total_attended': total_attended,
        'favorite_class_title': favorite_class_title,
        'streak_weeks': streak,
        'instructor_classes': instructor_classes,
    })


@login_required
def finalize_booking(request, class_id):
    wellness_class = get_object_or_404(WellnessClass, id=class_id)
    balance, _ = LeafBalance.objects.get_or_create(user=request.user)

    if request.method == "POST":
        payment_type = request.POST.get('payment_type')

        # Capacity check
        if wellness_class.booking_set.count() >= wellness_class.capacity:
            messages.error(request, "Sorry, this class just filled up!")
            return redirect('class_list')

        # Double booking check
        if Booking.objects.filter(client=request.user, wellness_class=wellness_class).exists():
            messages.warning(request, "You have already booked this session!")
            return redirect('dashboard')

        # Leaf payment
        if payment_type == 'leaf':
            if balance.leaves < 1:
                messages.error(request, "You don't have enough leaves!")
                return redirect('buy_leaves')
            balance.leaves -= 1
            balance.save()
            amount_paid = settings.LEAF_PRICE_EUR

        # Drop-in
        else:
            amount_paid = settings.DROP_IN_PRICE_EUR

        Booking.objects.create(
            client=request.user,
            wellness_class=wellness_class,
            payment_type=payment_type,
            amount_paid=amount_paid,
            is_paid=True if payment_type == 'leaf' else False,
        )
        return render(request, 'scheduling/success.html', {
            'wellness_class': wellness_class
        })

    return render(request, 'scheduling/finalize_booking.html', {
        'wellness_class': wellness_class,
        'balance': balance,
        'leaf_price_eur': settings.LEAF_PRICE_EUR,
        'drop_in_price_eur': settings.DROP_IN_PRICE_EUR,
    })


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)

    # Check the 24-hour rule
    if booking.wellness_class.start_time > timezone.now() + timedelta(hours=24):
        # If the user paid with a leaf, refund it before cancelling
        if booking.payment_type == 'leaf':
            balance, _ = LeafBalance.objects.get_or_create(user=booking.client)
            balance.leaves += 1
            balance.save()

        booking.delete()
        messages.success(
            request,
            "Cancellation successful. Your leaf has been refunded."
        )
    else:
        messages.error(
            request, "Cancellation denied: Less than 24h until class.")
    return redirect('dashboard')


@login_required
def instructor_attendance(request):
    # Only staff members (Instructors/Admins) can see this
    if not request.user.is_staff:
        return redirect('class_list')

    # Get classes and their students
    upcoming_classes = WellnessClass.objects.filter(
        start_time__gte=timezone.now())
    return render(request, 'scheduling/instructor_view.html', {'classes': upcoming_classes})


@login_required
def instructor_dashboard(request):
    # Security check: Only staff (instructors) can enter
    if not request.user.is_staff:
        return redirect('class_list')

    # Get classes specifically assigned to this instructor
    my_classes = WellnessClass.objects.filter(
        instructor=request.user,
        start_time__gt=timezone.now()
    ).order_by('start_time')

    return render(request, 'scheduling/instructor_dashboard.html', {'classes': my_classes})


@login_required
def instructor_overview(request):
    # Only allow staff members (Instructors/Admins) to see this page
    if not request.user.is_staff:
        return redirect('class_list')

    # Get all upcoming classes to show attendance
    upcoming_classes = WellnessClass.objects.filter(
        start_time__gte=timezone.now()).order_by('start_time')

    return render(request, 'scheduling/instructor_overview.html', {
        'classes': upcoming_classes
    })


@login_required
def toggle_payment_status(request, booking_id):
    # Security: Only admins can change payment data
    if not request.user.is_superuser:
        return redirect('class_list')

    booking = get_object_or_404(Booking, id=booking_id)

    # Toggle the status: True becomes False, False becomes True
    booking.is_paid = not booking.is_paid
    booking.save()

    status = "verified" if booking.is_paid else "marked as unpaid"
    messages.info(request, f"Payment for {booking.client.username} {status}.")
    return redirect('instructor_dashboard')

@staff_member_required
def create_class(request):
    if request.method == "POST":
        start_date_str = request.POST.get('start_date')
        start_time_str = request.POST.get('start_time_only')
        end_time_str = request.POST.get('end_time_only')

        start_naive = datetime.strptime(
            f"{start_date_str} {start_time_str}", '%Y-%m-%d %H:%M')

        start_dt = start_naive.replace(tzinfo=BUCHAREST)

        if end_time_str:
            end_naive = datetime.strptime(
                f"{start_date_str} {end_time_str}", '%Y-%m-%d %H:%M')
            end_dt = end_naive.replace(tzinfo=BUCHAREST)
            if end_dt <= start_dt:
                end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = start_dt + timedelta(hours=1)

        iterations = 4 if request.POST.get('is_recurring') == 'on' else 1

        for i in range(iterations):
            WellnessClass.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                start_time=start_dt + timedelta(weeks=i),
                end_time=end_dt + timedelta(weeks=i),
                capacity=request.POST.get('capacity'),
                instructor=request.user,
                is_recurring=bool(request.POST.get('is_recurring')),
                day_of_week=start_dt.weekday() if request.POST.get('is_recurring') else None
            )
        return redirect('instructor_dashboard')

    return render(request, 'scheduling/create_class.html')


def calendar_view(request):
    return render(request, 'scheduling/calendar.html')


def classes_json(request):
    classes = WellnessClass.objects.filter(start_time__gt=timezone.now())

    # Assign a color per instructor
    instructor_colors = {}
    colors = ['#6d8b74', '#e07a5f', '#3d405b', '#81b29a', '#f2cc8f', '#a8dadc']

    events = []
    for c in classes:
        instructor_id = c.instructor_id
        if instructor_id not in instructor_colors:
            instructor_colors[instructor_id] = colors[len(
                instructor_colors) % len(colors)]

        color = instructor_colors[instructor_id]
        spots_left = c.capacity - c.booking_set.count()

        events.append({
            'id': c.id,
            'title': c.title,
            'start': c.start_time.isoformat(),
            'end': c.end_time.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'instructor': c.instructor.get_full_name() or c.instructor.username if c.instructor else 'TBA',
                'description': c.description,
                'spots_left': spots_left,
                'is_full': spots_left <= 0,
                'class_id': c.id,
                'color': color,
            }
        })

    return JsonResponse(events, safe=False)


def _login_prompt(request, title, message, next_url_name):
    return render(request, 'scheduling/login_prompt.html', {
        'prompt_title': title,
        'prompt_message': message,
        'next_url_name': next_url_name,
    })


@login_required
def community_feed(request):
    posts = Post.objects.select_related('user').prefetch_related('comments__user', 'likes')
    user_likes = set(
        Like.objects.filter(user=request.user, post__in=posts).values_list('post_id', flat=True)
    )

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            today = timezone.now().date()
            already_posted = Post.objects.filter(user=request.user, created_at__date=today).exists()
            if already_posted:
                messages.error(request, "You can only share one mindful moment per day.")
            else:
                Post.objects.create(user=request.user, text=text)
                messages.success(request, "Your mindful moment has been shared.")
                return redirect('community')

    return render(request, 'scheduling/community.html', {
        'posts': posts,
        'user_likes': user_likes,
    })


def community(request):
    if not request.user.is_authenticated:
        return _login_prompt(
            request,
            "Join the Community",
            "Log in or sign up to share mindful moments and connect with others.",
            'community',
        )
    return community_feed(request)


@login_required
def create_post(request):
    if request.method != 'POST':
        return redirect('community')
    text = request.POST.get('text', '').strip()
    if text:
        today = timezone.now().date()
        already_posted = Post.objects.filter(user=request.user, created_at__date=today).exists()
        if already_posted:
            messages.error(request, "You can only share one mindful moment per day.")
        else:
            Post.objects.create(user=request.user, text=text)
            messages.success(request, "Your mindful moment has been shared.")
    return redirect('community')


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if not (request.user == post.user or request.user.is_superuser):
        return HttpResponseForbidden()
    if request.method == 'POST':
        post.delete()
        messages.info(request, "Post deleted.")
    return redirect('community')


@login_required
def toggle_like(request, post_id):
    if request.method != 'POST':
        return redirect('community')
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return redirect('community')


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if not (request.user == comment.user or request.user.is_superuser):
        return HttpResponseForbidden()
    if request.method == 'POST':
        comment.delete()
        messages.info(request, "Comment deleted.")
    return redirect('community')


@login_required
def settings_view(request):
    if request.method == 'POST' and request.POST.get('action') == 'update_email':
        new_email = request.POST.get('email', '').strip()
        if new_email:
            request.user.email = new_email
            request.user.save()
            messages.success(request, "Email updated.")

    leaf_balance, _ = LeafBalance.objects.get_or_create(user=request.user)
    leaf_requests = LeafRequest.objects.filter(user=request.user).order_by('-created_at')[:20]

    teaching_classes = []
    if request.user.is_staff:
        teaching_classes = WellnessClass.objects.filter(
            instructor=request.user,
            start_time__gt=timezone.now()
        ).order_by('start_time')

    pending_leaf_count = 0
    if request.user.is_superuser:
        pending_leaf_count = LeafRequest.objects.filter(status='pending').count()

    return render(request, 'scheduling/settings.html', {
        'leaf_balance': leaf_balance,
        'leaf_requests': leaf_requests,
        'teaching_classes': teaching_classes,
        'pending_leaf_count': pending_leaf_count,
    })


# Purchasing leaves
@login_required
def buy_leaves(request):
    balance, _ = LeafBalance.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        leaves_requested = int(request.POST.get('leaves_requested', 1))
        payment_proof = request.FILES.get('payment_proof')
        amount_paid = leaves_requested * settings.LEAF_PRICE_EUR

        LeafRequest.objects.create(
            user=request.user,
            leaves_requested=leaves_requested,
            amount_paid=amount_paid,
            payment_proof=payment_proof,
        )
        messages.success(
            request, f"Request for {leaves_requested} leaf(ves) submitted! Admin will approve shortly.")
        return redirect('buy_leaves')

    # Get pending requests
    pending_requests = LeafRequest.objects.filter(
        user=request.user, status='pending')

    return render(request, 'scheduling/buy_leaves.html', {
        'balance': balance,
        'pending_requests': pending_requests,
        'revolut_link': 'YOUR_REVOLUT_LINK_HERE',  # ← replace with your Revolut link
        'leaf_price_eur': settings.LEAF_PRICE_EUR,
    })


@login_required
def admin_leaves(request):
    if not request.user.is_superuser:
        return redirect('class_list')

    pending = LeafRequest.objects.filter(
        status='pending').order_by('created_at')
    approved = LeafRequest.objects.filter(
        status='approved').order_by('-created_at')[:10]

    return render(request, 'scheduling/admin_leaves.html', {
        'pending': pending,
        'approved': approved,
    })


@login_required
def approve_leaf_request(request, request_id):
    if not request.user.is_superuser:
        return redirect('class_list')

    leaf_request = get_object_or_404(LeafRequest, id=request_id)
    leaf_request.approve()
    messages.success(
        request, f"Approved {leaf_request.leaves_requested} leaf(ves) for {leaf_request.user.username}!")
    return redirect('admin_leaves')


@login_required
def reject_leaf_request(request, request_id):
    if not request.user.is_superuser:
        return redirect('class_list')

    leaf_request = get_object_or_404(LeafRequest, id=request_id)
    leaf_request.status = 'rejected'
    leaf_request.save()
    messages.warning(
        request, f"Rejected leaf request for {leaf_request.user.username}.")
    return redirect('admin_leaves')
