import smtplib
from email.message import EmailMessage
from .config import settings

def send_mail(to: str, subject: str, body: str):
    if not settings.smtp_host:
        # Pas de SMTP configuré : le message est affiché dans les logs (dev uniquement).
        print(f"[MAIL NON ENVOYÉ - SMTP absent] à {to} | {subject}\n{body}", flush=True)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    try:
        if settings.smtp_port == 465:
            s = smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=20)
        else:
            s = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)
        s.quit()
    except Exception as e:
        print("Erreur envoi e-mail:", e, flush=True)
