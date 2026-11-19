"""Complete ISO country/dial-code choices where phone metadata exists."""
from django import forms
from django_countries import countries
import phonenumbers


def country_choices():
    choices = [("", "Select your country and dialing code")]
    for iso, country_name in countries:
        code = phonenumbers.country_code_for_region(iso)
        if code:
            choices.append((iso, f"{country_name} (+{code})"))
    return choices


def normalize_phone(local_number, country):
    try:
        parsed = phonenumbers.parse(local_number.strip(), country)
    except phonenumbers.NumberParseException as exc:
        raise forms.ValidationError("Enter a valid telephone number.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise forms.ValidationError("The telephone number is not valid for the selected country.")
    if not phonenumbers.is_valid_number_for_region(parsed, country):
        raise forms.ValidationError("Check the selected country and telephone number.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
