from app.views.view import View

from flask import session

class AlgorithmView(View):
    def get_uploads_snippet(self):
        algorithms = []
        runningAlgorithms = []
        user_id = session.get('user_id')

        # Search Algorithm table for filenames of algorithms pertaining to a user
        sql = """
            SELECT Status, Name 
            FROM Algorithm 
            WHERE UserId = %s;
        """            
        self.database_cursor.execute(sql, (user_id,))
        algs = self.database_cursor.fetchall()

        for alg in algs:
            if alg[0] == 1:
                runningAlgorithms.append(alg[1])
            algorithms.append(alg[1])

        return self.render('snippets/uploads_list_snippet.html', 
            algorithms=algorithms,
            runningAlgorithms=runningAlgorithms)

