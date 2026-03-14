#We need to create a "view" that handles the logic of what happens when a user clicks that button.
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import WellnessClass, Booking
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User, Group
from .forms import ProfessionalSignUpForm
from decimal import Decimal

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
            instructor_group, created = Group.objects.get_or_create(name='Instructor')
            user.groups.add(instructor_group)

            # Give them 'Staff status' so they can log into the dashboard
            user.is_staff = True
            user.save()

        return super().form_valid(form)

def home(request):
    return render(request, 'scheduling/home.html')

def class_list(request):
    # This gets all classes to show to the clients
    classes = WellnessClass.objects.filter(start_time__gt=timezone.now()).order_by('start_time')

    # Logic to identify full classes
    for c in classes:
        # Calculate remaining spots: Total Capacity - Number of current Bookings
        c.spots_left = c.capacity - c.booking_set.count()
        c.is_full = c.spots_left <= 0

    # If user is logged in, get their booked class IDs to prevent double booking
    user_booked_ids = []
    if request.user.is_authenticated:
        user_booked_ids = request.user.booking_set.values_list('wellness_class_id', flat=True)

    return render(request, 'scheduling/class_list.html', {
        'classes': classes,
        'user_booked_ids': user_booked_ids
    })

@login_required
def book_session(request, class_id):
    # 1. Find the specific class the user wants to join
    wellness_class = get_object_or_404(WellnessClass, id=class_id)

    # 2. Create the booking record in the database
    # This automatically tracks who is coming for the instructor
    Booking.objects.get_or_create(
        client=request.user,
        wellness_class=wellness_class
    )

    # 3. Send them back to the class list
    return redirect('class_list')

@login_required
def client_dashboard(request):
    now = timezone.now()
    # Split classes into Upcoming and Past
    upcoming = Booking.objects.filter(client=request.user, wellness_class__start_time__gt=now).order_by('wellness_class__start_time')
    past = Booking.objects.filter(client=request.user, wellness_class__start_time__lte=now)

    return render(request, 'scheduling/dashboard.html', {
        'upcoming': upcoming,
        'past': past,
        'now_plus_24h': now + timedelta(hours=24)
    })

@login_required
def finalize_booking(request, class_id):
    wellness_class = get_object_or_404(WellnessClass, id=class_id)

    if request.method == "POST":
        payment_type = request.POST.get('payment_type')
        payment_proof = request.POST.get('payment_proof')

        # 1. SAFETY CHECK: Capacity
        if wellness_class.booking_set.count() >= wellness_class.capacity:
            messages.error(request, "Sorry, this class just filled up!")
            return redirect('class_list')

        # 2. SAFETY CHECK: Double Booking
        if Booking.objects.filter(client=request.user, wellness_class=wellness_class).exists():
            messages.warning(request, "You have already booked this session!")
            return redirect('dashboard')

        # 3. PRICING LOGIC: 10% Discount
        original_price = wellness_class.price
        if payment_type == 'prepaid':
            final_price = original_price * Decimal('0.90')
        else:
            final_price = original_price

        # 4. CREATE BOOKING
        Booking.objects.create(
            client=request.user,
            wellness_class=wellness_class,
            payment_type=payment_type,
            payment_proof=payment_proof,
            amount_paid=final_price,
            is_paid=False
        )
        return render(request, 'scheduling/success.html', {
            'wellness_class': wellness_class  # We pass 'class' to match your template's {{ class.title }}
        })

    # Calculate discount for display in the GET request
    discount_price = wellness_class.price * Decimal('0.90')

    return render(request, 'scheduling/finalize_booking.html', {
        'wellness_class': wellness_class,
        'discount_price': discount_price
    })

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)

    # Check the 24-hour rule
    if booking.wellness_class.start_time > timezone.now() + timedelta(hours=24):
        booking.delete()
        messages.success(request, "Cancellation successful.")
    else:
        messages.error(request, "Cancellation denied: Less than 24h until class.")
    return redirect('dashboard')

@login_required
def instructor_attendance(request):
    # Only staff members (Instructors/Admins) can see this
    if not request.user.is_staff:
        return redirect('class_list')

    # Get classes and their students
    upcoming_classes = WellnessClass.objects.filter(start_time__gte=timezone.now())
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
    upcoming_classes = WellnessClass.objects.filter(start_time__gte=timezone.now()).order_by('start_time')

    return render(request, 'scheduling/instructor_overview.html', {
        'classes': upcoming_classes
    })

@login_required
def toggle_payment_status(request, booking_id):
    # Security: Ensure only instructors can touch payment data
    if not request.user.is_staff:
        return redirect('class_list')

    booking = get_object_or_404(Booking, id=booking_id)

    # Toggle the status: True becomes False, False becomes True
    booking.is_paid = not booking.is_paid
    booking.save()

    status = "verified" if booking.is_paid else "marked as unpaid"
    messages.info(request, f"Payment for {booking.client.username} {status}.")
    return redirect('instructor_dashboard')

class ExtendedSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=[('client', 'Practitioner'), ('instructor', 'Teacher')])

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Automatically assign to Group
            group_name = 'Instructors' if self.cleaned_data['role'] == 'instructor' else 'Clients'
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            if self.cleaned_data['role'] == 'instructor':
                user.is_staff = True # Give them staff status for instructor views
                user.save()
        return user


@staff_member_required
def create_class(request):
    if request.method == "POST":
        # Get the start time from the form
        start_time_str = request.POST.get('start_time')
        start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')

        # Logic: Always set end_time to start_time + 1 hour
        end_dt = start_dt + timedelta(hours=1)

        iterations = 4 if request.POST.get('is_recurring') == 'on' else 1

        for i in range(iterations):
            WellnessClass.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                start_time=start_dt + timedelta(weeks=i),
                end_time=end_dt + timedelta(weeks=i),  # Automatically 1 hour later
                price=request.POST.get('price'),
                capacity=request.POST.get('capacity'),
                instructor=request.user
            )
        return redirect('instructor_dashboard')

    return render(request, 'scheduling/create_class.html')