import discord
from discord.ext import commands
from ScoreManager import ScoreManager
from pytz import timezone
from datetime import datetime

Client = discord.Client()
client = commands.Bot(command_prefix='&')
manager = ScoreManager('template.db')
time_zone = timezone('Europe/Amsterdam')

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


def access_denied():
    return "You do not have access to this command"


@client.event
async def on_ready():
    print("Bot operational")
    await client.change_presence(game=discord.Game(name='FACEIT Major: London 2018 (&help for commands)'))


@client.event
async def on_message(message):
    if message.content.startswith("&pick"):
        pick_message = message.content[6:].split(' ')
        match = pick_message[0]
        pick = pick_message[1]
        if not manager.register_pick(int(match), str(message.author), pick):
            await client.send_message(message.channel, "Error, match has already started or finished")
        else:
            await client.send_message(message.channel, "You picked {} for match {}".format(pick, match))

    if message.content.startswith("&matches"):
        matches = "```Current Matches (timezone: {}):".format(time_zone)
        done_matches = 'Done Matches:'
        for match in manager.get_matches():
            time_string = datetime.fromtimestamp(match.time, tz=time_zone)
            if not match.done:
                matches += "\n {}: {} vs {} starting on {} in {}".format(match.number, match.team1, match.team2,
                                                                         time_string, match.stage)

        if matches == "```Current Matches (timezone: {}):".format(time_zone):
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
                          '&addmatch x, y, z, a : adds x vs y in stage z for time a (a is a Unix timestamp)',
                          '&newpicks            : sends a message that new picks can be made to ' +
                          'all members in the database',
                          '&endmatch x, y       : ends match x with result y']

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
        timestamp = match_string[3]
        user = str(message.author)

        if user_is_admin(user):
            manager.add_match(team1, team2, stage, timestamp)
            print("User {} has added {} vs {} in {} on {}".format(message.author, team1, team2, stage, timestamp))
            await client.send_message(message.channel, "You have added {} vs {} in {} on {}".format(team1, team2, stage,
                                                                                                    timestamp))
        else:
            await client.send_message(message.channel, access_denied())

    if message.content.startswith("&newpicks"):
        user = str(message.author)
        if user_is_admin(user):
            server = message.server

            user_names = manager.get_users_from_picks()
            user_mentions = []
            for member in server.members:
                if member.name in user_names:
                    user_mentions.append(member)

            message_string = ""
            for user in user_mentions:
                message_string += user.mention + " "
            message_string += " You can now pick for the following matches:\n"

            matches = "```"
            for match in manager.get_matches():
                time_string = datetime.fromtimestamp(match.time, tz=time_zone)
                if not match.done:
                    matches += "\n {}: {} vs {} starting on {} in {}".format(match.number, match.team1, match.team2,
                                                                             time_string, match.stage)

            message_string += matches + "```"

            await client.send_message(message.channel, message_string)
        else:
            await client.send_message(message.channel, access_denied())

    if message.content.startswith("&endmatch"):
        user = str(message.author)
        print("User {} used endmatch command".format(user))
        if user_is_admin(user):
            string = message.content[10:].split(" ")
            match_number, result = string
            if manager.end_match(match_number, result):
                await client.send_message(message.channel, "Match {} ended {}".format(match_number, result))
                print("User {} successfully ended match {}".format(user, match_number))
            else:
                await client.send_message(message.channel, "Incorrect match number")
        else:
            await client.send_message(message.channel, access_denied())


client.run(token)
