from django.core.mail.message import EmailMultiAlternatives


class HTMLEmail(EmailMultiAlternatives):
    def __init__(self, *args, html, **kwargs):
        super().__init__(*args, **kwargs)
        self.attach_alternative(
            html,
            'text/html'
        )
