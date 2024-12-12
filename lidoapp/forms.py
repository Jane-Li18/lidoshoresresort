from django import forms
from django.utils import timezone
from .models import GuestAccount, AdminAccount, Room, RoomImage, FrontdeskAccount
from django.contrib.auth.hashers import make_password

class GuestAccountForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)

    class Meta:
        model = GuestAccount
        fields = ['first_name', 'middle_name', 'last_name', 'birthdate', 'gender', 'custom_gender', 'refer_as', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        # Do not hash the password here; let the model handle it
        return cleaned_data

    
class AdminAccountForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)

    class Meta:
        model = AdminAccount
        fields = ['first_name', 'middle_name', 'last_name', 'birthdate', 'gender', 'custom_gender', 'refer_as', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        else:
            cleaned_data['password'] = make_password(password)  # Hash the password

        return cleaned_data
    
    
class FrontdeskAccountForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)

    class Meta:
        model = FrontdeskAccount
        fields = ['first_name', 'middle_name', 'last_name', 'birthdate', 'gender', 'custom_gender', 'refer_as', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        else:
            cleaned_data['password'] = make_password(password)  # Hash the password

        return cleaned_data    
    
    

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_name', 'room_price', 'room_capacity', 'room_size', 'room_image', 'room_amenities', 'room_status', 'room_description', 'bed_type', 'discount']
        widgets = {
            'room_amenities': forms.CheckboxSelectMultiple(),
        }

class RoomImageForm(forms.ModelForm):
    class Meta:
        model = RoomImage
        fields = ['image']