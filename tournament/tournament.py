#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import print_function
import sys, os
import json

try:
    import argparse
except ImportError:
    from pelita.compat import argparse


parser = argparse.ArgumentParser(description='Run a tournament',
                                 add_help=False,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
prog = parser.prog
parser._positionals = parser.add_argument_group('Arguments')
parser.add_argument('pelitagame', help='The pelitagame script')

parser._optionals = parser.add_argument_group('Options')
parser.add_argument('--help', '-h', help='show this help message and exit',
                    action='store_const', const=True)

parser.add_argument('--teams', help='load teams from TEAMFILE',
                    metavar="TEAMFILE.json", default="teams.json")

parser.epilog = """
TEAMFILE.json must be of the form:
    { "group0": ["Name0", "Name1", "Name2"],
      "group1": ["Name0", "Name1", "Name2"],
      "group2": ["Name0", "Name1", "Name2"],
      "group3": ["Name0", "Name1", "Name2"],
      "group4": ["Name0", "Name1", "Name2"]
    }
"""

args = parser.parse_args()
if args.help:
    parser.print_help()
    sys.exit(0)

PELITA = args.pelitagame
if not os.path.exists(PELITA) or not os.path.isfile(PELITA):
    sys.stderr.write(PELITA+' not found!\n')
    sys.exit(2)

# FIXME: fit that for tournament
CMD_STUB = PELITA+' --rounds=300 --tk'
#CMD_STUB = PELITA+' --rounds=10 --null'
SPEAK = '/usr/bin/flite'

# the 'real' names of the teams (instead of group0 .. group4). they are
# collected while the tournament goes
rnames = {'group0' : 'group0',
          'group1' : 'group1',
          'group2' : 'group2',
          'group3' : 'group3',
          'group4' : 'group4' }

with open(args.teams) as teamfile:
    group_members = json.load(teamfile)

from subprocess import Popen, PIPE, STDOUT, check_call
import random
import time
import tempfile
import cStringIO

# check for festival support
if not os.path.exists(SPEAK.split()[0]):
    SPEAK=False

random.seed(42) # -> guaranteed to be random

# Number of points a teams gets for matches in the first round
POINTS_DRAW = 1
POINTS_WIN = 2

def get_seed():
    return random.randint(0, sys.maxint)

def print(*args, **kwargs):
    """Speak while you print. To disable set speak=False.
    You need the program 'flite' to be able to speak.
    Set wait=X to wait X seconds after speaking."""
    if len(args) == 0:
        __builtins__.print()
        return
    stream = cStringIO.StringIO()
    wait = kwargs.pop('wait', 0.5)
    want_speak = kwargs.pop('speak', SPEAK)
    if want_speak:
        __builtins__.print(*args, file=stream, **kwargs)
        string = stream.getvalue()
        __builtins__.print(string, end='')
        sys.stdout.flush()
        speak(string, wait=wait)
    else:
        __builtins__.print(*args, **kwargs)
    
def speak(string, wait=0.5):
    with tempfile.NamedTemporaryFile() as text:
        text.write(string+'\n')
        text.flush()
        festival = check_call(SPEAK.split()+[text.name])
    time.sleep(wait)

def present_teams():
    print('Hello master, I am the Python drone. I am here to serve you.', 
          wait=1.5)
    print('Welcome to the Pelita tournament', wait=1.5)
    print('This evening the teams are:', wait=1.5)
    for group in sorted(rnames.keys()):
        print(group, rnames[group])
        [print(member, wait=0.1) for member in group_members[group]]
        time.sleep(1)
        print('This was', group, rnames[group],wait=1.5)
    print('These were the teams. Now you ready for the fight?')
    
def set_name(team):
    """Get name of team using a dry-run pelita game"""
    global rnames
    args = CMD_STUB.split()
    args.extend(['--dry-run', team, 'random'])
    stdout, stderr = Popen(args, stdout=PIPE, stderr=PIPE).communicate()
    for line in stdout.splitlines():
        if line.startswith("Using factory '"):
            split = line.split("'")
            tname, rname = split[1], split[3]
            if tname in rnames:
                rnames[tname] = rname
    if stderr != '':
        print("*** ERROR: I could not load team", team, ". Please help!", 
              speak=False)
        print(stderr, speak=False)
        sys.exit(1)

def start_match(team1, team2):
    """Start a match between team1 and team2. Return which team won (1 or 2) or
    0 if there was a draw.
    """
    global rnames
    print()
    print('Starting match: '+ rnames[team1]+' vs ' + rnames[team2])
    print()
    raw_input('--- Press ENTER to continue ---\n')
    args = CMD_STUB.split()
    dumpfile = 'dumpstore/'+time.strftime('%Y%m%d-%H%M%S') 
    args.extend([team1, team2, '--dump', dumpfile,'--seed', str(get_seed())])
    stdout, stderr = Popen(args, stdout=PIPE, stderr=PIPE).communicate()
    tmp = reversed(stdout.splitlines())
    lastline = None
    for line in tmp:
        if line.startswith('Finished.'):
            lastline = line
            break
    if not lastline:
        print("*** ERROR: Apparently the game crashed. At least I could not find the outcome of the game.")
        print("*** Maybe stderr helps you to debug the problem")
        print(stderr, speak=False)
        print("***", speak=False)
        return 0
    if stderr != '':
        print("***", stderr, speak=False)
    print('***', lastline)
    if lastline.find('had a draw.') >= 0:
        return 0
    else:
        tmp = lastline.split("'")
        winner = tmp[1]
        loser = tmp[3]
        if winner == rnames[team1]:
            print(rnames[team1], 'wins.')
            return 1
        elif winner == rnames[team2]:
            print(rnames[team2], 'wins.')
            return 2
        else:
            print("Unable to parse winning result :(")
            return 0

def start_deathmatch(team1, team2):
    """Start a match between team1 and team2 until one of them wins (ie no
    draw.)
    """
    # FIXME: What if there is *always* a draw? We're in K.O. mode so we cannot
    # let both teams proceed.
    # do at most 3 death matches:
    for i in range(3):
        r = start_match(team1, team2)
        if r == 0:
            print('Draw -> Now go for a Death Match!')
            continue
        winner = team1 if r == 1 else team2
        return winner
    # if we are here, we have no winner after 3 death matches
    # just asisgn a random winner
    print('No winner after 3 Death Matches. Choose a winner at random:', wait=2)
    winner = random.choice((team1, team2))
    print('And the winner is', winner)
    return winner

def pp_round1_results(teams, points):
    """Pretty print the current result of the matches."""
    global rnames
    result = sorted(zip(points, teams), reverse=True)
    print('Current Ranking:')
    for p, t in result:
        print("  %25s %d" % (rnames[t], p))
    print()


def round1(teams):
    """Run the first round and return a sorted list of team names.

    teams is the sorted list [group0, group1, ...] and not the actual names of
    the agents. This is necessary to start the agents.
    """
    raw_input('--- Press ENTER to continue ---\n')
    print()
    print("ROUND 1 (Everybody vs Everybody)")
    print('================================', speak=False)
    print()
    points = [0 for i in range(len(teams))]
    round1 = []
    for i in range(5):
        for j in range(i+1, 5):
            ij = [i, j]
            random.shuffle(ij)
            round1.append(ij)
    #round1 = [[i, j] for i in range(5) for j in range(i+1, 5)]
    # shuffle the matches for more fun
    random.shuffle(round1)
    for t1, t2 in round1:
        winner = start_match(teams[t1], teams[t2])
        if winner == 0:
            points[t1] += POINTS_DRAW
            points[t2] += POINTS_DRAW
        else:
            points[[t1, t2][winner-1]] += POINTS_WIN
        pp_round1_results(teams, points)
    
    # Sort the teams by points and return the team names as a list
    result = sorted(zip(points, teams), reverse=True)
    result = [t for p, t in result]
    return result


def pp_round2_results(teams, w1, w2, w3, w4):
    """Pretty print the results for the K.O. round.

    teams is the list [group0, group1, ...] not the names of the agens, sorted
    by the result of the first round.
    """
    names = dict(rnames)
    names['???'] = '???'
    feed = max(len(item) for item in rnames.values())+2
    lengths={}
    for name in names:
        lengths[name] = feed - len(names[name])

    semifinal_top_up = names[teams[0]]+' '+"─"*lengths[teams[0]]+'┐' 
    final_top = " "*feed+' ├─ '+names[w1]+' '+'─'*lengths[w1]+'┐' 
    semifinal_top_down = names[teams[3]]+' '+"─"*lengths[teams[3]]+'┘' 
    preliminary_winner = (" "*(2*feed+5)+'├─ '+names[w3]+' '+
                          '─'*lengths[w3]+'┐ ')
    semifinal_bottom_up = names[teams[1]]+' '+"─"*lengths[teams[1]]+'┐'
    final_bottom = " "*feed+' ├─ '+names[w2]+' '+'─'*lengths[w2]+'┘' 
    semifinal_bottom_down = names[teams[2]]+' '+"─"*lengths[teams[2]]+'┘'
    looser = names[teams[4]]+' '+"─"*lengths[teams[4]]+'─'*(2*feed+8)+'┘'
    winner = " "*(3*feed+9)+'├─ '+names[w4]
    print()
    print(semifinal_top_up, speak=False)
    print(final_top, speak=False)
    print(semifinal_top_down+' '*(feed+3)+'│', speak=False)
    print(preliminary_winner, speak=False)
    print(semifinal_bottom_up+' '*(feed+3)+'│'+' '*(feed+3)+'│', speak=False)
    print(final_bottom+' '*(feed+3)+'└ '+names[w4], speak=False)
    print(semifinal_bottom_down+' '*(feed+3)+' '+' '*(feed+3)+
          '┌ '+'═'*len(names[w4]), speak=False)
    print(" "*(3*feed+9)+'│')
    print(looser, speak=False)
    print()



def round2(teams):
    """Run the second round and return the name of the winning team.

    teams is the list [group0, group1, ...] not the names of the agens, sorted
    by the result of the first round.
    """
    print()
    print('ROUND 2 (K.O.)')
    print('==============', speak=False)
    print()
    raw_input('--- Press ENTER to continue ---\n')
    w1, w2, w3, w4 = "???", "???", "???", "???"
    pp_round2_results(teams, w1, w2, w3, w4)
    # 1 vs 4
    w1 = start_deathmatch(teams[0], teams[3])
    pp_round2_results(teams, w1, w2, w3, w4)
    # 2 vs 3
    w2 = start_deathmatch(teams[1], teams[2])
    pp_round2_results(teams, w1, w2, w3, w4)
    # w1 vs w2
    w3 = start_deathmatch(w1, w2)
    pp_round2_results(teams, w1, w2, w3, w4)
    # W vs team5
    w4 = start_deathmatch(w3, teams[4])
    pp_round2_results(teams, w1, w2, w3, w4)
    raw_input('--- Press ENTER to continue ---\n')
    return w4

if __name__ == '__main__':
    # create a directory for the dumps
    if not os.path.exists('dumpstore'):
        os.mkdir('dumpstore')
    teams = rnames.keys()
    random.shuffle(teams)
    # load team names
    for team in teams:
        set_name(team)
    present_teams()
    result = round1(teams)
    winner = round2(result)
    print('The winner of the St Andrews Pelita tournament is...', wait=2)
    print(rnames[winner], '. Congratulations!', wait=2)
    print('Good evening master. It was a pleasure to serve you.')
