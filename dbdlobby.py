# Copyright (c) BlackFurniture.
# See LICENSE for details.

from __future__ import print_function
import ctypes
import os
try:
    import winreg
except ImportError:
    import _winreg as winreg
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                     'Software\\Valve\\Steam\\ActiveProcess')
dll_32 = winreg.QueryValueEx(key, 'SteamClientDll')[0]
dll_64 = winreg.QueryValueEx(key, 'SteamClientDll64')[0]
steam_path = os.path.dirname(dll_32)
os.environ["PATH"] += os.pathsep + steam_path

dbd_path = os.path.join(steam_path, 'steamapps', 'common',
                        'Dead by Daylight')
steamapi_path = os.path.join(dbd_path, 'Engine', 'Binaries', 'ThirdParty',
                             'Steamworks', 'Steamv136', 'Win64',
                             'steam_api64.dll')

os.environ['SteamAppId'] = '381210'
try:
    steam_api = ctypes.cdll.steam_api
    client_dll = dll_32
except OSError:
    try:
        steam_api = ctypes.cdll.steam_api64
        client_dll = dll_64
    except OSError:
        # load from DBD
        try:
            steam_api = ctypes.CDLL(steamapi_path)
            client_dll = dll_64
        except OSError as e:
            print('Could not load steam_api.dll or steam_api64.dll.')
            raise e

SteamAPI_Init = steam_api.SteamAPI_Init
GetHSteamUser = steam_api.SteamAPI_GetHSteamUser
GetHSteamPipe = steam_api.SteamAPI_GetHSteamPipe

try:
    CreateInterface = steam_api.SteamInternal_CreateInterface
    special_createinterface = False
except AttributeError:
    client_dll = ctypes.CDLL(client_dll)
    CreateInterface = client_dll.CreateInterface
    special_createinterface = True
CreateInterface.restype = ctypes.c_void_p

GetISteamMatchmaking = steam_api.SteamAPI_ISteamClient_GetISteamMatchmaking
GetISteamMatchmaking.restype = ctypes.c_void_p
GetISteamUtils = steam_api.SteamAPI_ISteamClient_GetISteamUtils
GetISteamUtils.restype = ctypes.c_void_p
AddRequestLobbyListResultCountFilter = \
    steam_api.SteamAPI_ISteamMatchmaking_AddRequestLobbyListResultCountFilter
AddRequestLobbyListFilterSlotsAvailable = \
    steam_api.SteamAPI_ISteamMatchmaking_AddRequestLobbyListFilterSlotsAvailable
AddRequestLobbyListDistanceFilter = \
    steam_api.SteamAPI_ISteamMatchmaking_AddRequestLobbyListDistanceFilter
RequestLobbyList = steam_api.SteamAPI_ISteamMatchmaking_RequestLobbyList
RequestLobbyList.restype = ctypes.c_ulonglong
IsAPICallCompleted = steam_api.SteamAPI_ISteamUtils_IsAPICallCompleted
IsAPICallCompleted.restype = ctypes.c_bool
GetAPICallResult = steam_api.SteamAPI_ISteamUtils_GetAPICallResult
GetAPICallResult.restype = ctypes.c_bool
GetLobbyByIndex = steam_api.SteamAPI_ISteamMatchmaking_GetLobbyByIndex
GetLobbyByIndex.restype = ctypes.c_ulonglong
GetNumLobbyMembers = steam_api.SteamAPI_ISteamMatchmaking_GetNumLobbyMembers
GetLobbyDataCount = steam_api.SteamAPI_ISteamMatchmaking_GetLobbyDataCount
GetLobbyDataByIndex = steam_api.SteamAPI_ISteamMatchmaking_GetLobbyDataByIndex
GetLobbyDataByIndex.restype = ctypes.c_bool
InviteUserToLobby = steam_api.SteamAPI_ISteamMatchmaking_InviteUserToLobby
InviteUserToLobby.restype = ctypes.c_bool

steam_api.SteamAPI_Init()
steam_user = GetHSteamUser()
steam_pipe = GetHSteamPipe()
if special_createinterface:
    ret = ctypes.c_int()
    SteamClient = ctypes.c_void_p(CreateInterface(b"SteamClient017",
                                                  ctypes.byref(ret)))
else:
    SteamClient = ctypes.c_void_p(CreateInterface(b"SteamClient017"))
SteamUtils = ctypes.c_void_p(GetISteamUtils(SteamClient, steam_pipe,
                                            b"SteamUtils008"))
SteamMatchmaking = ctypes.c_void_p(
    GetISteamMatchmaking(SteamClient, steam_user, steam_pipe,
                         b"SteamMatchMaking009")
)

BUFFER_SIZE = 256
PLAYERS_FILE = 'players.txt'

class Lobby:
    def __init__(self, lobby_id, members):
        self.lobby_id = lobby_id
        self.members = members
        self.data = {}
        self.get = self.data.get

    def get_int(self, key, default=None):
        try:
            return int(self.data[key])
        except KeyError:
            return default

    def get_near_rank(self):
        return self.get_int('NearRank_i')

def get_lobbies(slots, location):
    AddRequestLobbyListResultCountFilter(SteamMatchmaking, 500)
    AddRequestLobbyListFilterSlotsAvailable(SteamMatchmaking, slots)
    AddRequestLobbyListDistanceFilter(SteamMatchmaking, location)
    apicall = ctypes.c_ulonglong(RequestLobbyList(SteamMatchmaking))
    failed = ctypes.c_bool(False)
    while not IsAPICallCompleted(SteamUtils, apicall, ctypes.byref(failed)):
        pass
    ret = ctypes.c_uint32()
    GetAPICallResult(SteamUtils, apicall, ctypes.byref(ret),
                     ctypes.sizeof(ctypes.c_uint32), 510, ctypes.byref(failed))
    lobbies = []
    for i in range(ret.value):
        steam_id = ctypes.c_ulonglong(GetLobbyByIndex(SteamMatchmaking, i))
        members = GetNumLobbyMembers(SteamMatchmaking, steam_id)
        meta_count = GetLobbyDataCount(SteamMatchmaking, steam_id)
        if not meta_count:
            continue
        lobby = Lobby(steam_id.value, members)
        lobbies.append(lobby)
        for ii in range(meta_count):
            key = ctypes.create_string_buffer(BUFFER_SIZE)
            value = ctypes.create_string_buffer(BUFFER_SIZE)
            GetLobbyDataByIndex(SteamMatchmaking, steam_id, ii,
                                key, BUFFER_SIZE,
                                value, BUFFER_SIZE)
            lobby.data[key.value.decode('utf-8')] = value.value.decode('utf-8')
    return lobbies

def send_invite(lobby_id, player):
    InviteUserToLobby(SteamMatchmaking,
                      ctypes.c_ulonglong(lobby_id),
                      ctypes.c_ulonglong(player))

tried = set()

def send_invites(lobby_id):
    players = []
    with open(PLAYERS_FILE, 'rb') as fp:
        for line in fp:
            players.append(int(line))
    for player in players:
        send_invite(lobby_id, player)

def find_lobby(players, location, rank):
    lobbies = get_lobbies(players, location)
    if rank in ('lowest', 'highest'):
        lobbies = sorted(lobbies, key=lambda x: x.get_near_rank(),
                         reverse=rank == 'lowest')
    else:
        rank = int(rank)
        print('near test:', rank)
        lobbies = sorted(lobbies,
                         key=lambda x: abs(rank - x.get_near_rank()))
    lobbies = list(lobbies)
    print('Ranks:', [lobby.get_int('NearRank_i') for lobby in lobbies])

    lobby_ret = None
    lobby_count = 0
    for lobby in lobbies:
        if lobby.lobby_id in tried:
            continue
        lobby_count += 1
        if lobby_ret:
            continue
        print('Joining "%s" game' % lobby.get('OWNINGNAME'))
        max_rank = lobby.get_int('MaxRank_i')
        min_rank = lobby.get_int('MinRank_i')
        near_rank = lobby.get_near_rank()
        print('Min, max, near ranks: %s, %s, %s' % (min_rank,
                                                    max_rank,
                                                    near_rank))
        tried.add(lobby.lobby_id)
        send_invites(lobby.lobby_id)
        lobby_ret = lobby.lobby_id

    print('Lobbies left, total: %s, %s' % (lobby_count, len(lobbies)))
    return lobby_ret

try:
    get_input = raw_input
except NameError:
    get_input = input

def main():

    import argparse

    parser = argparse.ArgumentParser(description='Dead by Daylight lobby tool')
    parser.add_argument('--players', type=int, default=1,
                        help='number of slots that needs to be available')
    parser.add_argument('--location', default='close',
                        help='area to search in ("close", "default", "far" '
                             'or "near")')
    parser.add_argument('--rank', default='lowest',
                        help='rank to sort by ("lowest", "highest", or a '
                             'number to match a similar rank)')
    parser.add_argument('--interactive', action='store_true',
                        help='interactive setup of search')
    args = parser.parse_args()

    if not os.path.isfile(PLAYERS_FILE):
        print('Missing %r file! Fill it with Steam IDs for players to invite.'
              % PLAYERS_FILE)
        if args.interactive:
            get_input()
        return
    if os.path.getsize(PLAYERS_FILE) == 0:
        print('Empty %r file! Fill it with Steam IDs for players to invite.'
              % PLAYERS_FILE)
        if args.interactive:
            get_input()
        return

    locations = {
        'close': 0,
        'default': 1,
        'far': 2,
        'near': 3
    }
    if args.interactive:
        def get_value(text):
            while True:
                value = get_input(text)
                if not value.strip():
                    continue
                return value

        players = int(get_value('Player slots needed (1-4): '))
        location = get_value('Location (close, default, far or near): ')
        location = locations[location]
        rank = get_value('Rank to sort by (lowest, highest, or rank number): ')
    else:
        players = args.players
        location = locations[args.location]
        rank = args.rank

    invite_loop(players, location, rank)

def invite_loop(*arg, **kw):
    last_lobby = None
    while True:
        if get_input("Press Enter to find lobby, or 'r' "
                     "to resend last invite: ") == 'r':
            send_invites(last_lobby)
            continue
        last_lobby = find_lobby(*arg, **kw)

if __name__ == '__main__':
    main()
