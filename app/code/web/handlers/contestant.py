import router
import util

from base import BaseHandler

@router.route(r"/contestant")
class ContestantRootHandler(BaseHandler):
    @util.authenticated_as("contestant")
    def get(self):
        self.render(
            "contestant/root.html",
            contestant=self.current_user
        )
