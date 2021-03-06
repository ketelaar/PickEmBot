import pandas as pd
import sqlite3
import time


class ScoreManager:
    def __init__(self, db_location):
        connection = sqlite3.connect(db_location)

        self.db = db_location
        self.matches = pd.read_sql('select * from Matches', connection)
        self.picks = pd.read_sql('select * from Picks', connection)
        self.scores = pd.read_sql('select * from Scores', connection)
        self.multipliers = pd.read_sql('select * from Stage_Multipliers', connection)

        connection.close()

    def get_multipliers(self):
        """
        Gets multipliers from the multipliers data frame and stores the values in a dictionary

        :return: dictionary with the name of the stage being the key and the multiplier being the value
        """
        multipliers = {}
        for i, j in zip(self.multipliers['Stage'], self.multipliers['Multiplier']):
            multipliers[i] = j
        return multipliers

    def get_scores(self):
        """
        Gets scores from the scores data frame and stores the values in a dictionary

        :return: dictionary with the Discord ID being the key and the score being the value
        """
        scores = {}
        for i, j in zip(self.scores['NameID'], self.scores['Score']):
            scores[i] = j
        return scores

    def get_matches(self):
        """
        Gets a lists of Match objects from the matches data frame

        :return: A list of Match objects
        """
        matches = []

        class Match:
            """
            Object containing all the database variables from the Matches table
            """
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
        """
        Gets a lists of Pick objects from the picks data frame

        :return: A list of Pick objects
        """
        picks = []

        class Pick:
            """
            Objects containing all the database variables from the pick table
            Pick.match should always correspond to a match number in the Matches table
            """
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
        """
        List of unique users from the picks data frame
        :return: Set of strings
        """
        return set([pick.user for pick in self.get_picks()])

    def register_pick(self, match_number, user, userpick):
        """
        Registers the pick in the database

        :param match_number: index of the match in the Match table
        :param user: Discord ID to who the pick belongs
        :param userpick: The team that the user picked
        :return: False if the match is done or has started, True if the operation succeeds
        """
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()
        current_match = 0
        for m in self.get_matches():
            if m.number == match_number:
                current_match = m
                break

        if time.time() > current_match.time:  # user cannot change if match has started
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
        """
        Calculates the scores for every user in the picks data frame

        :return: void
        """
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
        """
        Makes a string that displays the score of every user in the picks data frame

        :return: string
        """
        self._calculate_scores()  # update the scores before display
        # score string that will be returned, ``` so that it will display in a discord code block
        score_string = '```Scores in descending order:'

        scores = [(k, v) for k, v in self.get_scores().items()]  # retrieves scores from the df and sorts on value
        scores = sorted(scores, key=lambda t: t[0])

        for n, i in enumerate(scores):
            score_string += "\n{}: {} has a score of {}".format(n + 1, i[0], i[1])

        score_string += "```"
        return score_string

    def change_match_variable(self, variable, value, match):
        """
        Changes a certain match variable in the Matches table

        :param variable: The variable of which the value should be changed
        :param value: The value to which the variable should be changed
        :param match: The match for which the value of the variable should be changed
        :return: void
        """
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()

        cur.execute("UPDATE Matches set {}=? WHERE Match=?".format(variable), [value, match])
        connection.commit()

        self.matches = pd.read_sql('select * from Matches', connection)
        connection.close()

    def add_match(self, team1, team2, stage, timestamp):
        """
        Adds a match to the Matches table

        :param team1: 1st team
        :param team2: 2nd team
        :param stage: stage in which the 2 teams are playing
        :param timestamp: the starting time of the match
        :return: void
        """
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()

        values = [len(self.get_matches()) + 1, team1, team2, '0-0', stage, timestamp, 0, 0, None]
        cur.execute("INSERT INTO Matches VALUES(?,?,?,?,?,?,?,?,?)", values)

        connection.commit()
        self.matches = pd.read_sql('select * from Matches', connection)
        connection.close()

    def find_match(self, match_number):
        """
        Finds Match object by the match number

        :param match_number: index number of the match
        :return: Match object
        """
        for match in self.get_matches():
            if int(match_number) == int(match.number):
                return match
        return False

    def end_match(self, match_number, result):
        """
        Ends the match by writing the results and setting the winning team

        :param match_number: number of the match in question
        :param result: the result between the two teams
        :return: True if succeeded, else False
        """
        connection = sqlite3.connect(self.db)
        cur = connection.cursor()

        match = self.find_match(match_number)

        if not match:
            connection.close()
            return False

        result_1, result_2 = result.split("-")
        if int(result_1) > int(result_2):
            winner = match.team1
        else:
            winner = match.team2

        values = [result, winner, match_number]
        cur.execute("UPDATE Matches set Result=?, Winner=?, Done=1 WHERE Match=?", values)
        connection.commit()

        self.matches = pd.read_sql('select * from Matches', connection)
        connection.close()

        return True


if __name__ == '__main__':
    manager = ScoreManager('template_db')
    manager.get_multipliers()
    manager.display_scores()
