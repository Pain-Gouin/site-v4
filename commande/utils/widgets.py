import json
from datetime import date, datetime

from django import forms


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


class DateRangeWidget(forms.widgets.MultiWidget):
    template_name = "widgets/range_date_picker.html"

    def __init__(self, attrs=None, options={}):
        # We define two internal widgets for the two inputs
        widgets = [
            forms.widgets.DateInput(attrs={"hidden": True}),
            forms.widgets.DateInput(attrs={"hidden": True}),
        ]
        self.options = options
        super().__init__(widgets, attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        context["widget"]["options"] = self.options
        return context

    def decompress(self, value):
        if value:
            return value

        return [None, None]

    class Media:
        js = [
            forms.widgets.Script(
                "externe/js/vendor/cally.0.9.0.js",
                type="module",
            ),
            "js/range-picker-bind.js",
        ]


class DateRangeField(forms.MultiValueField):
    widget = DateRangeWidget

    def __init__(self, min_date=None, max_date=None, *args, **kwargs):
        # Store the callable/value without calculating yet
        self.min_date_source = min_date
        self.max_date_source = max_date
        options = {}
        # Define the fields that make up the range
        fields = (
            forms.DateField(error_messages={"incomplete": "Enter a start date."}),
            forms.DateField(error_messages={"incomplete": "Enter an end date."}),
        )
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        """
        data_list is a list containing [date_obj_1, date_obj_2].
        This method merges them into a single value for form.cleaned_data.
        """
        if data_list:
            start_date, end_date = data_list

            # Logic: If both are provided, ensure the range is logical
            if start_date and end_date and start_date > end_date:
                raise forms.ValidationError(
                    "The start date cannot be after the end date."
                )

            return [start_date, end_date]
        return [None, None]

    def get_bound_field(self, form, field_name):
        """Runs every time the form is initialized in a view."""
        bound_field = super().get_bound_field(form, field_name)

        if self.min_date_source:
            bound_field.field.widget.options["minDate"] = (
                self.min_date_source()
                if callable(self.min_date_source)
                else self.min_date_source
            )

        if self.max_date_source:
            bound_field.field.widget.options["maxDate"] = (
                self.max_date_source()
                if callable(self.max_date_source)
                else self.max_date_source
            )

        return bound_field
