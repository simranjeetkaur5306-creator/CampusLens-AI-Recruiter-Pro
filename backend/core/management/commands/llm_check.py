"""python manage.py llm_check

Sends one tiny request to Gemini to check that GEMINI_API_KEY and GEMINI_MODEL in .env work.
Uses a negligible amount of quota.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import llm


class Command(BaseCommand):
    help = "Checks the Gemini API key and model with one tiny request."

    def handle(self, *args, **options):
        self.stdout.write(f"Model: {settings.GEMINI_MODEL}")
        messages = [
            {"role": "system", "content": "Reply with JSON only."},
            {"role": "user", "content": 'Return {"status": "ok"}'},
        ]
        try:
            result = llm.chat_json(messages, max_tokens=50)
        except llm.LLMError as error:
            raise CommandError(error.message)
        self.stdout.write(self.style.SUCCESS(
            f"Gemini works. Answer: {result.data}  (model {result.model}, "
            f"{result.prompt_tokens} prompt + {result.completion_tokens} output tokens)"
        ))
