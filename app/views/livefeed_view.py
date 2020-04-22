from app.views.view import View

class LivefeedView(View):
    def get_rendered_template(self):
        return self.render("livefeed.html")

