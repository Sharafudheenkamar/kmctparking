from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class ParkingSlot(models.Model):
    SLOT_TYPES = [
        ('regular', 'Regular'),
        ('vip', 'VIP'),
        ('disabled', 'Disabled'),
    ]
    parking_map = models.ImageField(upload_to='parking_slots/', null=True, blank=True)
    slot_number = models.CharField(max_length=10, unique=True)
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPES, default='regular')
    is_occupied = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    arduino_pin = models.IntegerField(null=True, blank=True)  # For Arduino integration
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return f"Slot {self.slot_number} - {'Occupied' if self.is_occupied else 'Vacant'}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.user.username} - {self.vehicle_number}"

class Booking(models.Model):
    PAYMENT_TYPES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def calculate_amount(self):
        if self.end_time:
            duration = self.end_time - self.start_time
            if self.payment_type == 'hourly':
                hours = duration.total_seconds() / 3600
                return round(hours * float(self.slot.hourly_rate), 2)
            else:  # daily
                days = duration.days + (1 if duration.seconds > 0 else 0)
                return days * float(self.slot.daily_rate)
        return 0.00
    
    def __str__(self):
        return f"Booking {self.booking_id} - {self.user.username}"

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=50)
    
    def __str__(self):
        return f"Admin: {self.user.username}"
