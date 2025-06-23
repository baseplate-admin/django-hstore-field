# yourapp/tests/test_fields.py
from django.test import TestCase
from django_hstore_field import HStoreField
from django_hstore_widget.forms import HStoreFormField
from django_hstore_widget.widgets import HStoreFormWidget


class AdminHStoreFieldTest(TestCase):
    def setUp(self):
        self.field = HStoreField(blank=True, null=True)

    def test_formfield_uses_hstore_widget(self):
        formfield = self.field.formfield()
        self.assertIsInstance(formfield, HStoreFormField)
        self.assertIsInstance(formfield.widget, HStoreFormWidget)
