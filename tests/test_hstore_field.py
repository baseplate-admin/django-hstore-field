from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import User
from cat.models import Cat
import pytest
from playwright.sync_api import sync_playwright, Error as PlaywrightError


@pytest.fixture
def admin_user(db):
    """Fixture to create an admin user."""
    user = User.objects.create(
        username="murphy",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    user.set_password("cat")
    user.save()
    return user


@pytest.fixture
def client_with_login(admin_user):
    """Fixture to log in the admin user."""
    client = Client()
    client.login(username=admin_user.username, password="cat")
    return client


@pytest.mark.django_db
def test_admin_cat_creation(client_with_login):
    """Test creating a Cat instance through the Django admin."""
    # Access the add view for the Cat model in the admin
    url = reverse("admin:cat_cat_add")
    response = client_with_login.get(url)
    assert response.status_code == 200  # Ensure the add view is accessible

    # POST data to create a new Cat instance
    data = {
        "name": "Whiskers",
        "data": '{"race": "Siamese", "gender": "female"}',
    }
    response = client_with_login.post(url, data, follow=True)


@pytest.mark.django_db
def test_hstore_field_edit_view_render_no_js(client_with_login):
    cat = Cat.objects.create(name="Murphy", data={"race": "", "gender": "male"})
    url = reverse("admin:cat_cat_change", args=(cat.pk,))
    response = client_with_login.get(url)

    assert response.status_code == 200
    assert "django-hstore-widget" in response.content.decode()


@pytest.mark.django_db
def test_hstore_field_edit_view_render_js(live_server, admin_user):
    """Playwright test to verify HStore widget renders correctly in the Django admin."""
    # Perform all Django ORM operations before starting Playwright,
    # since Playwright's sync API runs an internal asyncio loop that
    # triggers Django's SynchronousOnlyOperation check.
    cat = Cat.objects.create(name="Murphy", data={"race": "", "gender": "male"})
    change_url = f"{live_server.url}{reverse('admin:cat_cat_change', args=(cat.pk,))}"
    login_url = f"{live_server.url}/admin/login/"

    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
    except PlaywrightError as e:
        pytest.skip(str(e))

    context = browser.new_context()
    page = context.new_page()

    try:
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))

        # Open the admin login page
        page.goto(login_url)
        page.wait_for_selector('input[name="username"]')

        # Log in to admin
        page.fill('form input[name="username"]', admin_user.username)
        page.fill('form input[name="password"]', "cat")
        page.click('form input[type="submit"]')

        # Wait for login
        page.wait_for_selector("body.dashboard")

        # Go to the Cat change page
        page.goto(change_url)

        # Assert the widget is present
        hstore_widget = page.query_selector("django-hstore-widget")
        assert hstore_widget is not None

        # Assert that console is empty
        # If console is empty, there is no mounting issue
        assert not any(
            message
            for message in console_messages
            if message.type in ("warning", "error")
        )

        # Assert that there is the hidden textarea
        page.wait_for_selector("django-hstore-widget textarea", state="attached")
        hstore_widget_textarea = page.query_selector("django-hstore-widget textarea")
        assert hstore_widget_textarea is not None
    finally:
        context.close()
        browser.close()
        pw.stop()
