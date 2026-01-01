from datetime import date, datetime
from django import forms
import json


class MultiDateCalendarWidget(forms.HiddenInput):
    template_name = "widgets/multi_date_picker.html"

    def __init__(self, attrs=None, options=None):
        """
        options: A dictionary of configuration options for the JS plugin.
        e.g., {'multiSelect': 0, 'dateFormat': 'yyyy-mm-dd'}
        """
        self.options = options or {"multiSelect": 0}
        self.options["dateFormat"] = "yy-mm-dd"
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        # Create a FRESH copy of options for this specific request
        render_options = self.options.copy()

        # Handle the initial/selected dates
        if value:
            # If value is a string from POST, split it; if list from initial, use as is
            date_list = value if isinstance(value, list) else value.split(",")
            render_options["addDates"] = [
                d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else d.strip()
                for d in date_list
                if d
            ]

        context["widget"]["options"] = json.dumps(render_options)
        return context

    class Media:
        # Note: You should host these files locally or use reliable CDNs
        css = {
            "all": [
                "externe/css/jquery-ui.min.css",
                "externe/css/jquery-ui.multidatespicker.css",
            ]
        }
        js = [
            "externe/js/vendor/jquery-3.7.1.min.js",
            "externe/js/vendor/jquery-ui.min.js",
            "externe/js/vendor/datepicker-fr.js",
            "externe/js/vendor/jquery-ui.multidatespicker.js",
        ]


class MultiDateField(forms.Field):
    widget = MultiDateCalendarWidget

    def __init__(self, *, min_date=None, max_date=None, **kwargs):
        # Store the callable/value without calculating yet
        self.min_date_source = min_date
        self.max_date_source = max_date
        options = {}
        super().__init__(**kwargs)

    def get_bound_field(self, form, field_name):
        """Runs every time the form is initialized in a view."""
        bound_field = super().get_bound_field(form, field_name)

        # Calculate offsets NOW (during the request)
        today = date.today()

        if self.min_date_source:
            actual_min = (
                self.min_date_source()
                if callable(self.min_date_source)
                else self.min_date_source
            )
            bound_field.field.widget.options["minDate"] = (actual_min - today).days

        if self.max_date_source:
            actual_max = (
                self.max_date_source()
                if callable(self.max_date_source)
                else self.max_date_source
            )
            bound_field.field.widget.options["maxDate"] = (actual_max - today).days

        return bound_field

    def to_python(self, value):
        """Normalize data to a list of python date objects."""
        if not value:
            return []
        if isinstance(value, list):
            return value

        try:
            return [
                datetime.strptime(d.strip(), "%Y-%m-%d").date()
                for d in value.split(",")
            ]
        except (ValueError, TypeError):
            raise forms.ValidationError("Invalid date format detected.")

    def validate(self, value):
        """Check if required input is empty."""
        super().validate(value)
        # Add any extra logic here (e.g., maximum number of dates allowed)
        if self.required and not value:
            raise forms.ValidationError("Please select at least one date.")
