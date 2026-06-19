from django import forms

GROUP_CHOICES = [
    ('d1:rrhh',   'D1 — RRHH'),
    ('d1:worker', 'D1 — Worker'),
    ('d1:admin',  'D1 — Admin'),
    ('d2:viewer', 'D2 — Viewer'),
    ('d2:editor', 'D2 — Editor'),
    ('d2:admin',  'D2 — Admin'),
]


class UserProvisionForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    groups = forms.MultipleChoiceField(
        choices=GROUP_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    role = forms.ChoiceField(required=False)

    def __init__(self, *args, role_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [('', '— No role —')] + (role_choices or [])
