import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parent / "templates"


class SMTPService:
    def __init__(
            self,
            smtp_host: str,
            smtp_port: int,
            username: str,
            password: str,
            from_name: str,
            use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_name = from_name
        self.use_tls = use_tls
        self.template_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

    def render_template(self, template_name: str, **kwargs) -> str:
        template = self.template_env.get_template(template_name)
        return template.render(**kwargs)

    def send_email(self, to_email: str, subject: str, template_name: str, context: dict):
        body = self.render_template(template_name, **context)

        msg = MIMEMultipart()
        msg["From"] = f"{self.from_name} <{self.username}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_email, msg.as_string())
                print(f"Email sent to {to_email}")

        except smtplib.SMTPException as e:
            raise RuntimeError(f"Failed to send email: {str(e)}")
