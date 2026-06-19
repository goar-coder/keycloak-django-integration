from django import forms


class UserProvisionForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    groups = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    role = forms.ChoiceField(required=False)

    def __init__(self, *args, group_choices=None, role_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].choices = group_choices or []
        self.fields['role'].choices = [('', '— No role —')] + (role_choices or [])
