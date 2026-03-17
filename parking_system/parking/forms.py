from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, AdminProfile, ParkingSlot, Booking

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15)
    vehicle_number = forms.CharField(max_length=20)
    vehicle_type = forms.CharField(max_length=50)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class AdminRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    employee_id = forms.CharField(max_length=20)
    department = forms.CharField(max_length=50)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ParkingSlotForm(forms.ModelForm):
    class Meta:
        model = ParkingSlot
        fields = ('slot_number', 'slot_type', 'hourly_rate', 'daily_rate', 'arduino_pin', 'parking_map')
        widgets = {
            'slot_number': forms.TextInput(attrs={'class': 'form-control'}),
            'slot_type': forms.Select(attrs={'class': 'form-control'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'arduino_pin': forms.NumberInput(attrs={'class': 'form-control'}),
            'parking_map': forms.ClearableFileInput(attrs={'class': 'form-control parking-image-field'}),
        }
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('slot', 'payment_type')
        widgets = {
            'slot': forms.Select(attrs={'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slot'].queryset = ParkingSlot.objects.filter(is_occupied=False)

