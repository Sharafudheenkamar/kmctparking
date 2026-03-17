from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import ParkingSlot, UserProfile, AdminProfile, Booking
from .forms import UserRegistrationForm, AdminRegistrationForm, ParkingSlotForm, BookingForm
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.contrib.auth import logout

ARDUINO_SLOT_CACHE = {'S1': False, 'S2': False, 'S3': False, 'S4': False}
ARDUINO_LAST_UPDATE = None

def home(request):
    return render(request, 'parking/base.html')


def _compute_vacant_slots_count():
    live_occupied = _get_live_occupied_by_slot_number()
    active_booking_slot_ids = set(Booking.objects.filter(status='active').values_list('slot_id', flat=True))
    vacant_count = 0
    for slot in ParkingSlot.objects.all():
        is_occupied = live_occupied.get(slot.slot_number, False)
        is_booked = slot.id in active_booking_slot_ids
        if not (is_occupied or is_booked):
            vacant_count += 1
    return vacant_count

# User Authentication Views
def user_register(request):
    if request.method == 'POST':
        print("ok1")
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                phone=form.cleaned_data['phone'],
                vehicle_number=form.cleaned_data['vehicle_number'],
                vehicle_type=form.cleaned_data['vehicle_type']
            )
            print("ok")
            login(request, user)
            messages.success(request, 'Registration successful!')
            print("OK")
            return redirect('user_dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'parking/user_register.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home') 

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user and hasattr(user, 'userprofile'):
            login(request, user)
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not a user account')
    return render(request, 'parking/user_login.html')

# Admin Authentication Views
@staff_member_required
def admin_register(request):
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_staff = True
            user.save()
            AdminProfile.objects.create(
                user=user,
                employee_id=form.cleaned_data['employee_id'],
                department=form.cleaned_data['department']
            )
            messages.success(request, 'Admin registration successful!')
            return redirect('admin_dashboard')
    else:
        form = AdminRegistrationForm()
    return render(request, 'parking/admin_register.html', {'form': form})

def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid admin credentials')
    return render(request, 'parking/admin_login.html')

# Dashboard Views
@login_required
def user_dashboard(request):
    if not hasattr(request.user, 'userprofile'):
        return redirect('admin_dashboard')
    
    user_bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    vacant_slots = _compute_vacant_slots_count()
    
    context = {
        'user_bookings': user_bookings,
        'vacant_slots': vacant_slots
    }
    return render(request, 'parking/user_dashboard.html', context)

@staff_member_required
def admin_dashboard(request):
    total_slots = ParkingSlot.objects.count()
    vacant_slots = _compute_vacant_slots_count()
    occupied_slots = total_slots - vacant_slots
    total_users = UserProfile.objects.count()
    active_bookings = Booking.objects.filter(status='active').count()
    
    context = {
        'total_slots': total_slots,
        'vacant_slots': vacant_slots,
        'occupied_slots': occupied_slots,
        'total_users': total_users,
        'active_bookings': active_bookings
    }
    return render(request, 'parking/admin_dashboard.html', context)

# Parking Slot Management
@staff_member_required
def manage_slots(request):
    slots = ParkingSlot.objects.all()
    if request.method == 'POST':
        form = ParkingSlotForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parking slot added successfully!')
            return redirect('manage_slots')
    else:
        form = ParkingSlotForm()

    context = {
        'slots': slots,
        'form': form
    }
    return render(request, 'parking/slot_management.html', context)


@staff_member_required
def update_slot(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)
    if request.method == 'POST':
        form = ParkingSlotForm(request.POST, request.FILES, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Slot updated successfully!')
            return redirect('manage_slots')
    else:
        form = ParkingSlotForm(instance=slot)

    return render(request, 'parking/slot_management.html', {
        'form': form,
        'slot': slot
    })


@staff_member_required
def delete_slot(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)
    if request.method == 'POST':
        slot.delete()
        messages.success(request, 'Slot deleted successfully!')
    return redirect('manage_slots')

# Booking Management

@login_required
def book_slot(request):
    if not hasattr(request.user, 'userprofile'):
        return redirect('admin_dashboard')

    now = timezone.now()

    if request.method == 'POST':
        selected_slot_id = request.POST.get('selected_slot')
        payment_type = request.POST.get('payment_type')
        requested_start_time = request.POST.get('start_time')
        requested_end_time = request.POST.get('end_time')

        if not selected_slot_id or payment_type not in {'hourly', 'daily'}:
            messages.error(request, 'Please select a slot and payment type to continue.')
            return redirect('book_slot')

        if not requested_start_time or not requested_end_time:
            messages.error(request, 'Please select both booking start and end time.')
            return redirect('book_slot')

        try:
            start_time = timezone.make_aware(timezone.datetime.fromisoformat(requested_start_time))
            end_time = timezone.make_aware(timezone.datetime.fromisoformat(requested_end_time))
        except ValueError:
            messages.error(request, 'Invalid booking time selected.')
            return redirect('book_slot')

        if start_time < now or start_time > (now + timedelta(minutes=30)):
            messages.error(request, 'You can only set the start time from now up to 30 minutes ahead.')
            return redirect('book_slot')

        if end_time <= start_time:
            messages.error(request, 'End time must be greater than start time.')
            return redirect('book_slot')

        minimum_end_time = start_time + timedelta(hours=1)
        if end_time < minimum_end_time:
            messages.error(request, 'End time must be at least 1 hour after start time.')
            return redirect('book_slot')

        slot = get_object_or_404(ParkingSlot, id=selected_slot_id)
        has_active_booking = Booking.objects.filter(slot=slot, status='active').exists()

        live_occupied = _get_live_occupied_by_slot_number()
        if live_occupied.get(slot.slot_number, False) or has_active_booking:
            messages.error(request, f'Slot {slot.slot_number} is not vacant for booking.')
            return redirect('book_slot')

        booking = Booking.objects.create(
            user=request.user,
            slot=slot,
            payment_type=payment_type,
            start_time=start_time,
            end_time=end_time,
        )

        messages.success(request, f'Slot {slot.slot_number} booked successfully!')
        return redirect('booking_confirmation', booking_id=booking.booking_id)

    slots = ParkingSlot.objects.all().order_by('slot_number')
    active_booking_slot_ids = set(
        Booking.objects.filter(status='active').values_list('slot_id', flat=True)
    )

    live_occupied = _get_live_occupied_by_slot_number()

    slot_states = []
    for slot in slots:
        is_occupied = live_occupied.get(slot.slot_number, False)
        is_booked = slot.id in active_booking_slot_ids
        is_vacant = not (is_occupied or is_booked)

        if is_vacant:
            state = 'vacant'
            status_label = 'Vacant'
        elif is_occupied:
            state = 'occupied'
            status_label = 'Occupied (physical)'
        else:
            state = 'booked'
            status_label = 'Occupied (booked)'

        slot_states.append({
            'slot': slot,
            'is_occupied': is_occupied,
            'is_booked': is_booked,
            'is_vacant': is_vacant,
            'is_available': is_vacant,
            'state': state,
            'status_label': status_label,
        })

    context = {
        'slot_states': slot_states,
        'min_start_time': now.strftime('%Y-%m-%dT%H:%M'),
        'max_start_time': (now + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
        'default_end_time': (now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
    }
    return render(request, 'parking/book_slot.html', context)


@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'parking/booking_confirmation.html', {'booking': booking})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    if booking.status == 'active':
        booking.status = 'cancelled'
        booking.end_time = timezone.now()
        booking.save()
        
        messages.success(request, 'Booking cancelled successfully!')
    return redirect('user_dashboard')

@login_required
def payment(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    if request.method == 'POST':
        # Simulate payment processing
        booking.paid = True
        booking.save()
        messages.success(request, 'Payment successful!')
        return redirect('user_dashboard')
    
    # Calculate amount based on current time
    booking.end_time = timezone.now()
    amount = booking.calculate_amount()
    booking.total_amount = amount
    booking.save()
    
    context = {
        'booking': booking,
        'amount': amount
    }
    return render(request, 'parking/payment.html', context)


# API Views for Arduino Integration

def _to_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_arduino_payload(request):
    """Accept JSON, normal form data, or comma-form payload like 'S1=1,S2=0,S3=1,S4=0'."""
    content_type = request.headers.get('Content-Type', '')

    if 'application/json' in content_type:
        return json.loads(request.body or b'{}')

    if request.POST:
        return dict(request.POST.items())

    raw = (request.body or b'').decode('utf-8', errors='ignore').strip()
    data = {}
    if raw:
        for pair in raw.replace('&', ',').split(','):
            if '=' in pair:
                key, value = pair.split('=', 1)
                data[key.strip()] = value.strip()
    return data



def _slot_mapping():
    """Map Arduino channels S1..S4 to DB slot numbers."""
    mapping = {'S1': 'A1', 'S2': 'A2', 'S3': 'B1', 'S4': 'B2'}

    # Fallback: if named slots don't exist, map to first 4 DB slots by order.
    existing_numbers = set(ParkingSlot.objects.values_list('slot_number', flat=True))
    required = set(mapping.values())
    if not required.issubset(existing_numbers):
        ordered_slots = list(ParkingSlot.objects.order_by('slot_number')[:4])
        if len(ordered_slots) == 4:
            mapping = {
                'S1': ordered_slots[0].slot_number,
                'S2': ordered_slots[1].slot_number,
                'S3': ordered_slots[2].slot_number,
                'S4': ordered_slots[3].slot_number,
            }
    return mapping


def _get_live_occupied_by_slot_number():
    mapping = _slot_mapping()
    reverse_mapping = {slot_number: sensor for sensor, slot_number in mapping.items()}
    occupied = {}
    for slot in ParkingSlot.objects.all():
        sensor_key = reverse_mapping.get(slot.slot_number)
        occupied[slot.slot_number] = bool(ARDUINO_SLOT_CACHE.get(sensor_key, False)) if sensor_key else False
    return occupied


def get_slot_status(request):
    """Frontend polling endpoint: returns Arduino-live slot status + booking flags."""
    slots = ParkingSlot.objects.all().order_by('slot_number')
    live_occupied = _get_live_occupied_by_slot_number()
    active_booking_slot_ids = set(Booking.objects.filter(status='active').values_list('slot_id', flat=True))

    slot_data = []
    for slot in slots:
        is_occupied = live_occupied.get(slot.slot_number, False)
        is_booked = slot.id in active_booking_slot_ids
        is_vacant = not (is_occupied or is_booked)
        slot_data.append({
            'slot_id': slot.id,
            'slot_number': slot.slot_number,
            'arduino_pin': slot.arduino_pin,
            'is_occupied': is_occupied,
            'is_booked': is_booked,
            'is_vacant': is_vacant,
            'slot_type': slot.slot_type,
            'hourly_rate': float(slot.hourly_rate),
            'daily_rate': float(slot.daily_rate),
        })

    return JsonResponse({
        'status': 'success',
        'slots': slot_data,
        'total_slots': len(slot_data),
        'vacant_slots': len([s for s in slot_data if s['is_vacant']]),
        'arduino_last_update': ARDUINO_LAST_UPDATE,
    })


@csrf_exempt
def update_slot_status_api(request):
    """Arduino POST endpoint that updates in-memory live occupancy (not DB)."""
    global ARDUINO_LAST_UPDATE

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        data = _parse_arduino_payload(request)
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': f'Invalid payload: {exc}'}, status=400)

    mapping = _slot_mapping()
    updated_slots = []

    for sensor_key in ('S1', 'S2', 'S3', 'S4'):
        if sensor_key not in data:
            continue

        new_state = _to_bool(data[sensor_key])
        ARDUINO_SLOT_CACHE[sensor_key] = new_state
        updated_slots.append({
            'sensor': sensor_key,
            'slot_number': mapping.get(sensor_key),
            'is_occupied': new_state,
        })

    ARDUINO_LAST_UPDATE = timezone.now().isoformat()

    return JsonResponse({
        'status': 'success',
        'updated_slots': updated_slots,
        'received': data,
        'last_update': ARDUINO_LAST_UPDATE,
    })


def update_slot_status(request):
    """Backward-compatible update endpoint."""
    return update_slot_status_api(request)


@staff_member_required
def view_users(request):
    users = UserProfile.objects.select_related('user').all()
    return render(request, 'parking/view_users.html', {'users': users})
