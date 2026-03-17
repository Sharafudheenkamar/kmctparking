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

def home(request):
    return render(request, 'parking/base.html')

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
    vacant_slots = ParkingSlot.objects.filter(is_occupied=False).count()
    
    context = {
        'user_bookings': user_bookings,
        'vacant_slots': vacant_slots
    }
    return render(request, 'parking/user_dashboard.html', context)

@staff_member_required
def admin_dashboard(request):
    total_slots = ParkingSlot.objects.count()
    vacant_slots = ParkingSlot.objects.filter(is_occupied=False).count()
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

        if not selected_slot_id or payment_type not in {'hourly', 'daily'}:
            messages.error(request, 'Please select a slot and payment type to continue.')
            return redirect('book_slot')

        if requested_start_time:
            try:
                start_time = timezone.make_aware(
                    timezone.datetime.fromisoformat(requested_start_time)
                )
            except ValueError:
                messages.error(request, 'Invalid booking start time selected.')
                return redirect('book_slot')
        else:
            start_time = now

        if start_time < now or start_time > (now + timedelta(minutes=30)):
            messages.error(request, 'You can only book for now or up to 30 minutes ahead.')
            return redirect('book_slot')

        slot = get_object_or_404(ParkingSlot, id=selected_slot_id)
        has_active_booking = Booking.objects.filter(slot=slot, status='active').exists()

        if slot.is_occupied or has_active_booking:
            messages.error(request, f'Slot {slot.slot_number} is not available for booking.')
            return redirect('book_slot')

        booking = Booking.objects.create(
            user=request.user,
            slot=slot,
            payment_type=payment_type,
            start_time=start_time,
        )

        slot.is_occupied = True
        slot.save()

        messages.success(request, f'Slot {slot.slot_number} booked successfully!')
        return redirect('payment', booking_id=booking.booking_id)

    slots = ParkingSlot.objects.all().order_by('slot_number')
    active_booking_slot_ids = set(
        Booking.objects.filter(status='active').values_list('slot_id', flat=True)
    )

    slot_states = []
    for slot in slots:
        has_active_booking = slot.id in active_booking_slot_ids
        unavailable = slot.is_occupied or has_active_booking
        if slot.is_occupied and has_active_booking:
            state = 'occupied_booked'
        elif slot.is_occupied:
            state = 'occupied'
        elif has_active_booking:
            state = 'booked'
        else:
            state = 'available'

        slot_states.append({
            'slot': slot,
            'has_active_booking': has_active_booking,
            'is_available': not unavailable,
            'state': state,
        })

    context = {
        'slot_states': slot_states,
        'min_start_time': now.strftime('%Y-%m-%dT%H:%M'),
        'max_start_time': (now + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
    }
    return render(request, 'parking/book_slot.html', context)

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    if booking.status == 'active':
        booking.status = 'cancelled'
        booking.end_time = timezone.now()
        booking.save()
        
        # Free up the slot
        slot = booking.slot
        slot.is_occupied = False
        slot.save()
        
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
def get_slot_status(request):
    """API endpoint for Arduino to get slot status"""
    slots = ParkingSlot.objects.all()
    slot_data = []
    for slot in slots:
        slot_data.append({
            'slot_number': slot.slot_number,
            'arduino_pin': slot.arduino_pin,
            'is_occupied': slot.is_occupied
        })
    return JsonResponse({'slots': slot_data})

def update_slot_status(request):
    """API endpoint for Arduino to update slot status"""
    if request.method == 'POST':
        data = json.loads(request.body)
        slot_number = data.get('slot_number')
        is_occupied = data.get('is_occupied')
        
        try:
            slot = ParkingSlot.objects.get(slot_number=slot_number)
            slot.is_occupied = is_occupied
            slot.save()
            return JsonResponse({'status': 'success'})
        except ParkingSlot.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Slot not found'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@staff_member_required
def view_users(request):
    users = UserProfile.objects.select_related('user').all()
    return render(request, 'parking/view_users.html', {'users': users})


@csrf_exempt
def update_slot_status_api(request):
    """API endpoint to receive slot status updates from Arduino"""
    if request.method == 'POST':
        try:
            # Parse JSON data
            data = json.loads(request.body)
            
            # Log received data
            print(f"📨 Received slot update: {data}")
            
            # Map Arduino slots to database slots
            slot_mapping = {
                'S1': 'A1',  # Adjust these to match your actual slot numbers
                'S2': 'A2',
                'S3': 'B1', 
                'S4': 'B2'
            }
            
            # Update each slot in database
            updated_slots = []
            for arduino_slot, is_occupied in data.items():
                if arduino_slot.startswith('S') and arduino_slot in slot_mapping:
                    db_slot_number = slot_mapping[arduino_slot]
                    
                    try:
                        slot = ParkingSlot.objects.get(slot_number=db_slot_number)
                        slot.is_occupied = bool(is_occupied)
                        slot.save()
                        updated_slots.append({
                            'slot_number': db_slot_number,
                            'is_occupied': bool(is_occupied)
                        })
                    except ParkingSlot.DoesNotExist:
                        pass
            
            return JsonResponse({
                'status': 'success',
                'updated_slots': updated_slots,
                'message': f'Updated {len(updated_slots)} slots'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

# Update the existing get_slot_status function
def get_slot_status(request):
    """API endpoint for Arduino and frontend to get current slot status"""
    slots = ParkingSlot.objects.all()
    slot_data = []
    
    for slot in slots:
        slot_data.append({
            'slot_number': slot.slot_number,
            'arduino_pin': slot.arduino_pin,
            'is_occupied': slot.is_occupied,
            'slot_type': slot.slot_type,
            'hourly_rate': float(slot.hourly_rate),
            'daily_rate': float(slot.daily_rate)
        })
    
    return JsonResponse({
        'status': 'success',
        'slots': slot_data,
        'total_slots': len(slot_data),
        'vacant_slots': len([s for s in slot_data if not s['is_occupied']])
    })
