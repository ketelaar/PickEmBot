import discord
from discord.ext import commands
from ScoreManager import ScoreManager

Client = discord.Client()
client = commands.Bot(command_prefix='&')
manager = ScoreManager('template.db')

with open('token') as file:
    token = file.read()

# from https://stackoverflow.com/questions/3277503/in-python-how-do-i-read-a-file-line-by-line-into-a-list
with open('admin') as file:
    admins = [line.rstrip('\n') for line in file]


def user_is_admin(user):
    """
    Checks if user is in the admin list
    :param user: string which is the Discord ID of the user
    :return: True if user is in the admin list, else False
    """
    return user in admins


@client.event
async def on_ready():
    print("Bot operational")


@client.event
async def on_message(message):
    if message.content.startswith("&pick"):
        # TODO: Incorporate timestamps in order to stop users from picking after the match has started
        pick_message = message.content[6:].split(' ')
        match = pick_message[0]
        pick = pick_message[1]
        if not manager.register_pick(int(match), str(message.author), pick):
            await client.send_message(message.channel, "Error, match has already started or finished")
        else:
            await client.send_message(message.channel, "You picked {} for match {}".format(pick, match))

    if message.content.startswith("&matches"):
        matches = "```Current Matches:"
        done_matches = 'Done Matches:'
        for match in manager.get_matches():
            if not match.done:
                matches += "\n {}: {} vs {} starting at {} in {}".format(match.number, match.team1, match.team2,
                                                                         match.time, match.stage)
            else:
                done_matches += "\n {}: {} vs {} in {} ({})".format(match.number, match.team1, match.team2,
                                                                    match.stage, match.result)

        if matches == "```Current Matches:":
            matches = "```No current matches in the database"

        matches += '\n' + done_matches
        matches += '```'

        print("User {} used the matches command".format(message.author))
        await client.send_message(message.channel, matches)

    if message.content.startswith("&set"):
        set_message = message.content[5:].split(" ")
        match = set_message[0]
        variable = set_message[1]
        value = set_message[2]
        user = str(message.author)

        if user_is_admin(user):
            manager.change_match_variable(variable, value, match)
            print("User {} changed {} to {} for Match {}".format(user, variable, value, match))
        else:
            await client.send_message(message.channel, "You do not have permission to set variables.")

    if message.content.startswith("&scores"):
        print("User {} used the scores command".format(message.author))
        await client.send_message(message.channel, manager.display_scores())

    if message.content.startswith("&help"):
        prefix_commands = ['&pick x y    : picks team y for match x',
                           '&matches     : displays all current and past matches',
                           '&userpicks   : displays the picks made by users per match',
                           '&scores      : displays the scores in descending order for all participants',
                           '&multipliers : displays the points gained per stage of the tournament']

        admin_commands = ['&set x y z           : sets the value z for the variable y for match x',
                          '&addmatch x, y, z, a : adds x vs y in stage z for time a']

        string = "```Commands:"
        for c in prefix_commands:
            string += "\n" + c
        string += "\n \nCommands for admins:"
        for c in admin_commands:
            string += "\n" + c
        string += "```"

        print("User {} used the help command".format(message.author))
        await client.send_message(message.channel, string)

    if message.content.startswith("&multipliers"):
        multipliers_string = "```Multipliers:"
        multipliers = [(k, v) for k, v in manager.get_multipliers().items()]

        for m in multipliers:
            if m[1] == 1:
                multipliers_string += "\n {:15}: {} point".format(m[0], m[1])
            else:
                multipliers_string += "\n {:15}: {} points".format(m[0], m[1])

        multipliers_string += "```"

        await client.send_message(message.channel, multipliers_string)

    if message.content.startswith("&userpicks"):
        picks_string = "```Picks per match:"
        matches = manager.get_matches()
        picks = manager.get_picks()

        for m in matches:
            picks_string += "\n \n Match {}: {} vs {} in {}".format(m.number, m.team1, m.team2, m.stage)
            match_picks = [p for p in picks if p.match == m.number]
            for mp in match_picks:
                picks_string += "\n  {} picked {}".format(mp.user, mp.pick)

        picks_string += "```"

        await client.send_message(message.channel, picks_string)

    if message.content.startswith("&addmatch"):
        match_string = message.content[10:].split(" ")
        team1 = match_string[0]
        team2 = match_string[1]
        stage = match_string[2]
        time = match_string[3]
        user = str(message.author)

        if user_is_admin(user):
            manager.add_match(team1, team2, stage, time)
            print("User {} has added {} vs {} in {} on {}".format(message.author, team1, team2, stage, time))
            await client.send_message(message.channel, "You have added {} vs {} in {} on {}".format(team1, team2, stage,
                                                                                                    time))
        else:
            await client.send_message(message.channel, "You do not have permission to use this command")


client.run(token)
