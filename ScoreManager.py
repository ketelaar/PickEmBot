import pandas as pd
import sqlite3


class ScoreManager:
    def __init__(self, db_location):
        connection = sqlite3.connect(db_location)
        cur = connection.cursor()

        self.db = db_location
        self.matches = pd.read_sql('select * from Matches', connection)
        self.picks = pd.read_sql('select * from Picks', connection)
        self.scores = pd.read_sql('select * from Scores', connection)
        self.multipliers = pd.read_sql('select * from Stage_Multipliers', connection)

        connection.commit()

        connection.close()

    def get_multipliers(self):
        multipliers = {}
        for i, j in zip(self.multipliers['Stage'], self.multipliers['Multiplier']):
            multipliers[i] = j
        return multipliers

    def get_scores(self):
        scores = {}
        for i, j in zip(self.scores['NameID'], self.scores['Score']):
            scores[i] = j
        return scores

    def get_matches(self):
        matches = []

        class Match:
            def __init__(self, series):
                self.number = series[0]
                self.team1 = series[1]
                self.team2 = series[2]
                self.result = series[3]
                self.stage = series[4]
                self.time = series[5]
                self.done = bool(series[6])
                self.started = bool(series[7])
                self.winner = series[8]

            def __repr__(self):
                return "Match {}: {} vs {}, result:{} , stage:{}, starting time:{}, done:{}, started:{}" \
                       ", winner: {}".format(self.number, self.team1, self.team2, self.result, self.stage,
                                             self.time, self.done, self.started, self.winner)

        for i in range(self.matches.shape[0]):
            matches.append(Match(self.matches.iloc[i]))
        return matches

    def get_picks(self):
        picks = []

        class Pick:
            def __init__(self, series):
                self.match = int(series[0])
                self.user = series[1]
                self.pick = series[2]

            def __repr__(self):
                return "{} picked {} for Match {}".format(self.user, self.pick, self.match)

        for i in range(self.picks.shape[0]):
            picks.append(Pick(self.picks.iloc[i]))
        return picks

    def get_users_from_picks(self):
        return set([pick.user for pick in self.get_picks()])

    def register_pick(self, match_number, user, userpick):
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()
        current_match = 0
        for m in self.get_matches():
            if m.number == match_number:
                current_match = m
                break

        if current_match.done or current_match.started:  # user cannot change if match is done or has started
            return False

        for pick in self.get_picks():  # checking to see if the picks has already been made
            if match_number == pick.match and user == pick.user:  # if there is already a pick made by the user
                print("User {} changed pick of match {} to {}".format(user, match_number, userpick))
                values = [str(userpick), str(user), match_number]
                cur.execute("UPDATE Picks SET Pick=? WHERE NameID=? AND Match=?", values)
                connection.commit()

                connection.close()
                return True

        # if the pick has not already been made, the value is inserted
        cur.execute("INSERT INTO Picks VALUES(?, ?, ?)", [match_number, str(user), str(userpick)])
        print("User {} picked {} for match {}".format(user, userpick, match_number))
        connection.commit()

        self.picks = pd.read_sql('select * from Picks', connection)  # refreshes the contents of the picks data frame
        connection.close()
        return True

    def _calculate_scores(self):
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()

        done_matches = [match for match in self.get_matches() if match.done]

        for user in self.get_users_from_picks():
            user_picks = [pick for pick in self.get_picks() if pick.user == user]
            score = 0

            for match in done_matches:
                stage = match.stage

                for pick in user_picks:
                    if pick.match == match.number and pick.pick == match.winner:
                        score += self.get_multipliers()[stage]

            print('User {} has a score of {}'.format(user, score))

            if user not in self.get_scores().keys():  # if user does not have an entry in the scores table
                cur.execute("INSERT INTO Scores VALUES(?, ?)", [user, score])
            else:
                cur.execute("UPDATE Scores set Score=? WHERE NameID=?", [score, user])

        connection.commit()

        self.scores = pd.read_sql('select * from Scores', connection)  # updates the data frame (df) from the db
        connection.close()

    def display_scores(self):
        self._calculate_scores()  # update the scores before display
        # score string that will be returned, ``` so that it will display in a discord code block
        score_string = '```Scores in descending order:'

        scores = [(k, v) for k, v in self.get_scores().items()]  # retrieves scores from the df and sorts on value

        for n, i in enumerate(scores):
            score_string += "\n{}: {} has a score of {}".format(n + 1, i[0], i[1])

        score_string += "```"
        return score_string

    def change_match_variable(self, variable, value, match):
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()

        cur.execute("UPDATE Matches set {}=? WHERE Match=?".format(variable), [value, match])
        connection.commit()

        self.matches = pd.read_sql('select * from Matches', connection)
        connection.close()

    def add_match(self, team1, team2, stage, time):
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()

        values = [len(self.get_matches()) + 1, team1, team2, stage, '0-0', time, 0, 0, None]
        cur.execute("INSERT INTO Matches VALUES(?,?,?,?,?,?,?,?,?)", values)

        connection.commit()
        self.matches = pd.read_sql('select * from Matches', connection)
        connection.close()


if __name__ == '__main__':
    manager = ScoreManager('template_db')
    manager.get_multipliers()
    manager.display_scores()
