import json
import os
import sys

from riotwatcher import LolWatcher
from config import *


def to_dump(xs):
    """Removes white space within lists of json dump"""
    formatted_dump = ''
    brackets = 0
    for x in xs:
        if x == '[':
            brackets += 1
        elif x == ']':
            brackets -= 1
        if brackets == 0 or x not in '\n \t':
            formatted_dump += x
    return formatted_dump


# central api object
lol_watcher = LolWatcher(api_key)

# gather all the dicts
me = lol_watcher.summoner.by_name(region, summoner_name)
for ranked_stat in lol_watcher.league.by_summoner(region, me['id']):
    if ranked_stat['queueType'] == 'RANKED_SOLO_5x5':
        ranked_stats = ranked_stat
last_match = lol_watcher.match.matchlist_by_account(region, me['accountId'], queue={'420'}, end_index=1)['matches'][0]
match_stats = lol_watcher.match.by_id(region, last_match['gameId'])
timeline = lol_watcher.match.timeline_by_match(region, last_match['gameId'])

# champion data to parse ids
versions = lol_watcher.data_dragon.versions_for_region(region)
champions_version = versions['n']['champion']
champions_data = lol_watcher.data_dragon.champions(champions_version)['data']

# champion names and ids
enemy_champion = sys.argv[1]
my_championId = last_match['champion']
for k, v in champions_data.items():
    if int(v['key']) == my_championId:
        my_champion = k
        break
if enemy_champion == 'Wukong':
    enemy_championId = int(champions_data['MonkeyKing']['key'])
else:
    enemy_championId = int(champions_data[enemy_champion]['key'])

# participant ids and match stats
for participant in match_stats['participants']:
    if participant['championId'] == my_championId:
        my_participantId = participant['participantId']
        my_match_stats = participant['stats']
    if participant['championId'] == enemy_championId:
        enemy_participantId = participant['participantId']
        enemy_match_stats = participant['stats']

# only way to track LP loss/gain per game
# count points from Iron IV 0 LP = 0 total LP to Master Promos = 2400 total LP
points = {'IRON': 0, 'BRONZE': 400, 'SILVER': 800, 'GOLD': 1200, 'PLATINUM': 1600, 'DIAMOND': 2000,
          'IV': 0, 'III': 100, 'II': 200, 'I': 300}

# compiling ranked and match data
data = {
    'lp': points[ranked_stats['tier']] + points[ranked_stats['rank']] + ranked_stats['leaguePoints'],
    'wins': ranked_stats['wins'],
    'losses': ranked_stats['losses'],
    'gameId': match_stats['gameId'],
    'timestamp': last_match['timestamp'],
    'gameDuration': match_stats['gameDuration'],
    'win': my_match_stats['win'],
    'my_champion': my_champion,
    'enemy_champion': enemy_champion,
    'total_kills': my_match_stats['kills'],
    'total_deaths': my_match_stats['deaths'],
    'total_assists': my_match_stats['assists'],
    'visionScore': my_match_stats['visionScore'],
    'wardsPlaced': my_match_stats['wardsPlaced'],
    'wardsKilled': my_match_stats['wardsKilled'],
    'my_gold': [],
    'enemy_gold': [],
    'my_xp': [],
    'enemy_xp': [],
    'my_cs': [],
    'enemy_cs': [],
    'kills': [],
    'deaths': [],
    'assists': []
}

# compiling timeline data
for frame in timeline['frames']:
    for frame_stats in frame['participantFrames'].values():
        if frame_stats['participantId'] == my_participantId:
            data['my_gold'].append(frame_stats['totalGold'])
            data['my_xp'].append(frame_stats['xp'])
            data['my_cs'].append(frame_stats['minionsKilled'] + frame_stats['jungleMinionsKilled'])
        if frame_stats['participantId'] == enemy_participantId:
            data['enemy_gold'].append(frame_stats['totalGold'])
            data['enemy_xp'].append(frame_stats['xp'])
            data['enemy_cs'].append(frame_stats['minionsKilled'] + frame_stats['jungleMinionsKilled'])
    for event in frame['events']:
        if event['type'] == 'CHAMPION_KILL':
            if event['killerId'] == my_participantId:
                data['kills'].append((event['timestamp'], len(event['assistingParticipantIds'])))
            if event['victimId'] == my_participantId:
                data['deaths'].append((event['timestamp'], len(event['assistingParticipantIds'])))
            if my_participantId in event['assistingParticipantIds']:
                data['assists'].append((event['timestamp'], len(event['assistingParticipantIds'])))

# update data
if os.path.exists('data.json'):
    with open('data.json', 'r') as f:
        total_data = json.load(f)
        total_data[str(len(total_data) + 1)] = data
else:
    total_data = {'1': data}
with open('data.json', 'w') as f:
    f.write(to_dump(json.dumps(total_data, indent=2)))

# give feedback so user can check if entry is correct
print(to_dump(json.dumps(data, indent=2)))
