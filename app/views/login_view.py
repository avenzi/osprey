from app.views.view import View
from app.views.forms import LoginForm

class LoginView(View):
    def get_rendered_template(self):
        return self.render("login.html", title="Sign In", form=LoginForm())