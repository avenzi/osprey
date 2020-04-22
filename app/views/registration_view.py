from app.views.view import View
from app.views.forms import RegistrationForm

class RegistrationView(View):
    def get_rendered_template(self):
        return self.render("registration.html", title="Registration", form=RegistrationForm())