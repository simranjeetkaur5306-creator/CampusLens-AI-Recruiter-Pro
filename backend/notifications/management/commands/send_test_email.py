from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from notifications.services import delivery_mode


class Command(BaseCommand):
    help = "Send one test email to check the SMTP settings in your .env file."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Address that should receive the test email")

    def handle(self, *args, **options):
        self.stdout.write(f"Email backend : {settings.EMAIL_BACKEND}")
        self.stdout.write(
            f"SMTP server   : {settings.EMAIL_HOST or '(EMAIL_HOST is empty)'}:{settings.EMAIL_PORT} "
            f"(TLS={settings.EMAIL_USE_TLS}, SSL={settings.EMAIL_USE_SSL})"
        )
        self.stdout.write(
            f"Login set     : user={'yes' if settings.EMAIL_HOST_USER else 'no'}, "
            f"password={'yes' if settings.EMAIL_HOST_PASSWORD else 'no'}"
        )
        self.stdout.write(f"From address  : {settings.DEFAULT_FROM_EMAIL}")

        mode = delivery_mode()
        if mode == "not_configured":
            raise CommandError("SMTP is not configured. Set EMAIL_HOST (and the login) in your .env file.")
        if mode == "console":
            self.stdout.write(self.style.WARNING("Console/file backend: the email will NOT be delivered."))

        try:
            sent = send_mail(
                "CampusLens AI test email",
                "If you can read this, your SMTP settings work.",
                settings.DEFAULT_FROM_EMAIL,
                [options["to"]],
                fail_silently=False,
            )
        except Exception as error:  # show the real reason; this command is for debugging
            raise CommandError(f"Sending failed: {type(error).__name__}: {error}")
        if not sent:
            raise CommandError("The mail backend reported that nothing was sent.")
        self.stdout.write(self.style.SUCCESS(f"Test email handed to the mail server for {options['to']}."))