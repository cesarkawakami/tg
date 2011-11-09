import router
import util

import base
from db import D


class ContestantBaseHandler(base.BaseHandler):
    @util.authenticated_as("contestant")
    def prepare(self):
        pass


@router.route(r"/contestant")
class ContestantRootHandler(ContestantBaseHandler):
    def get(self):
        self.render(
            "contestant/root.html",
            user=self.current_user
        )


@router.route(r"/contestant/problems")
class ContestantProblemsHandler(ContestantBaseHandler):
    def get(self):
        problems = list(D.problems.find())
        self.render(
            "contestant/problems.html",
            user=self.current_user,
            problems=problems
        )

