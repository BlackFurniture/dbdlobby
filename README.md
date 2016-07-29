# dbdlobby

![Demonstration GIF](http://i.imgur.com/mR75hkp.gif)

Having trouble joining lobbies in Dead by Daylight, especially in
"survive with friends"? This may be a tool for you.

`dbdlobby` supports the following:
- Sending of Steam Friends invitations
- Lobby list
- Listing of lobby host name and rank

### Usage

First, fill `players.txt` with Steam IDs for players that you want to invite.

Then, with either Python 3 or Python 2, run

```
python dbdlobby.py --players 3 --location close --rank lowest
```

to search for lobbies with 3 slots, nearby region, and with the lowest rank
possible. You can also do

```
python dbdlobby.py --interactive
```

to make the program ask interactively for parameters.

If you are running Python 32bit, you will have to place `steam_api.dll` in the
local directory.

### Why did you create this?

With "survive with friends", joining a working lobby could in our case take up
to 1 hour. This tool was made to fix that.

This is partly a message to the developer, partly a temporary workaround.
Please fix the matchmaking system!