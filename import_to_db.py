from peewee import *
from mymodels import *
from urllib2 import urlopen, HTTPError, URLError
import re
import xml.etree.ElementTree as ET
import logging
import os
import datetime, time
from threading import Thread
from Queue import Queue


logpath = '~/Baseball/logs'
logfile = 'PFX_DB.log'

pos_desc = {
            'C':['catcher','c'],
            '1B':['first base', 'first','1b', 'first baseman'],
            '2B':['second base', 'second','2b','second baseman'],
            '3B':['third base', 'third','3b', 'third baseman'],
            'SS':['shortstop', 'short stop', 'short','ss'],
            'LF':['left field', 'left','lf','left fielder'],
            'CF':['center field', 'center','cf','center fielder'],
            'RF':['right field', 'right','rf','right fielder'],
            }

logging.basicConfig(filename='/'.join([logpath,logfile]), level=logging.INFO)

class PFXDBError(Exception):
    pass

class GameFinder(Thread):
    #TODO: Make threaded object for fetching gameday data.
    pass


def discover_games(month, year, level='mlb', start_date = 1):
    url = '/'.join(['http://12.130.102.59/components/game',level])
    yearstr = '_'.join(['year',str(year)])
    if month>=10:
        monthstr = '_'.join(['month',str(month)])
    else:
        m=''.join(['0',str(month)])
        monthstr = '_'.join(['month',m])
    monthurl = '/'.join([url, yearstr, monthstr])
    #print monthurl
    #monthpage = urlopen(monthurl)
    monthpage = _get_url(monthurl)
    monthpagestr = ' '.join(monthpage.readlines())
    monthpage.close()

    daylist = []
    for i in range(start_date,32):
        if i<10:
            dstr='_'.join(['day',''.join(['0',str(i)])])
        else:
            dstr='_'.join(['day',str(i)])
        if dstr in monthpagestr:
            daylist.append(dstr)
    gameurls=[]
    for day in daylist:
        dayurl = '/'.join([monthurl, str(day)])
        #daypage = urlopen(dayurl)
        daypage = _get_url(dayurl)
        daypagelist = daypage.readlines()
        daypage.close()
        for line in daypagelist:
            if 'gid' in line and level in line:
                gameurls.append('/'.join([dayurl, re.split('"',line)[1]]))
    return gameurls

class GamedayTree(object):
    complete = False
    box_tree = None
    game_tree = None
    inning_tree = None
    player_tree = None
    hit_tree = None
    def __init__(self, url, level, gametype=None):
        mygame = _get_url(url)
        lines = mygame.read()
        
        if not 'boxscore.xml' in lines or not 'game.xml' in lines or not 'players.xml' in lines or not 'inning' in lines:
            logging.info('%s missing critical elements.  Skipping')
            return
        box_url = '/'.join([url, 'boxscore.xml'])
        game_url = '/'.join([url,'game.xml'])
        inning_all_url = '/'.join([url, 'inning','inning_all.xml'])
        players_url = '/'.join([url, 'players.xml'])
        hit_url = '/'.join([url,'inning','inning_hit.xml'])
        box = _get_url(box_url)
        if box is not None:
            self.box_tree = ET.parse(box).getroot()
            box.close()
        game = _get_url(game_url)
        if game is not None:
            self.game_tree = ET.parse(game).getroot()
            game.close()
        players = _get_url(players_url)
        if players is not None:
            self.player_tree = ET.parse(players).getroot()
            players.close()
        
        innings = _get_url(inning_all_url)
        self.complete = box is not None and game is not None and players is not None
        if innings is not None:
            self.inning_tree = ET.parse(innings).getroot()
            innings.close()
        #in some early years, inning_all does not exist:
        elif self.complete:
            first_inning = int(
                self.box_tree.find('linescore')[0].attrib['inning'])
            last_inning = int(
                self.box_tree.find('linescore')[-1].attrib['inning'])
            if self.box_tree.find('linescore')[last_inning-1].attrib['inning'] == 'x':
                for inng in xrange(last_inning, first_inning-1,-1):
                    if self.box_tree.find('linescore')[inng].attrib['inning'] != 'x':
                        last_inning = inng
                        break
            the_innings=[]
            for i in range(first_inning,last_inning+1):
                this_inning = _get_url('/'.join([url, 'inning',
                                '_'.join(['inning',str(i)+'.xml'])]))
                if this_inning is not None:
                    the_innings.append(this_inning.read())
                    this_inning.close()
                else:
                    break
            if len(the_innings)==last_inning-first_inning+1:
                inningstr = ''.join([inning for inning in the_innings])
                innings = ''.join(['<game>',inningstr,'</game>'])
                self.inning_tree = ET.fromstring(innings)
            else:
                self.complete = False
                self.inning_tree = None
        
        hits = _get_url(hit_url)
        if self.complete and hits is not None:
            self.hit_tree = ET.parse(hits).getroot()
            hits.close()
        if not self.complete:
            logging.warn('%s : could not get complete data.  Will not process',
                         url)

    

def load_game(gameday):
    if not isinstance(gameday, GamedayTree):
        raise PFXDBError("I can't work with this")
    if not gameday.complete:
        logging.error("Cannot convert a non-complete-gameday object, skipping %s",url)
        #raise PFXDBError("Gameday Object not complete")
        return
    logging.info("\n\nprocessing game %s: ", gameday.box_tree.attrib['game_id'])
    GAME = None
    PLAYERS = {}
    UMPIRE = None
    GAMETYPE = None
    STADIUM = None
    defensive_players = {'home':{},'away':{}}
    batting_order={'home':{},'away':{}}
    #Get/Create the objects that don't have any foreign keys first:
    #Game Type:
    GAMETYPE = GameTypes.get_or_create(type = gameday.game_tree.attrib['type'])
    #Umpire:  If we cannot get umpire info for this game, create/get "Unknown"
    home_ump = None
    for ump in gameday.player_tree.find('umpires').findall('umpire'):
        if ump.attrib['position'] =='home':
            home_ump = ump.attrib['name']
    if home_ump is None or home_ump==' ' or home_ump == '':
        UMPIRE = Umpires.get_or_create(first = "Unknown", last = "Unknown")
    else:
        first = home_ump[:home_ump.rfind(' ')]
        last = home_ump.split()[-1]
        UMPIRE = Umpires.get_or_create(first = first, last = last)
    #Insert umpire into DB
    UMPIRE.save()
    #Stadium
    stadium_name = gameday.player_tree.attrib['venue']
    STADIUM = Stadiums.get_or_create(name = stadium_name)
    #Insert or update stadium into DB
    STADIUM.save()
    #Game
    GAME, gid_string = get_or_create_game(gameday.box_tree, gameday.player_tree, 
                              gameday.game_tree, UMPIRE, GAMETYPE)
    GAME.venue = STADIUM
    GAME.save()
    #Loop over players in players.xml
    for team in gameday.player_tree.findall('team'):
        homeaway = team.attrib['type']
        for player in team.findall('player'):
            id = int(player.attrib['id'])
            try:
                PLAYERS[id]=Players.get( Players.eliasid == id)
            except Players.DoesNotExist:
                PLAYERS[id]=Players.create( eliasid = id, 
                                            first = player.attrib['first'],
                                            last = player.attrib['last'],
                                            throws = player.attrib['rl'] )
            try: 
                position = player.attrib['game_position']
                #print position
                batorder = int(player.attrib['bat_order'])
                if position in pos_desc:
                    defensive_players[homeaway][position] = PLAYERS[id]
                batting_order[homeaway][batorder] = PLAYERS[id]
            except KeyError:
                #player did not play in game
                pass
            PLAYERS[id].save()
    
    #Loop over at bats, filling those
    abcount = 0
    inningcount = 0
    pitchcount = 0
    for inning in gameday.inning_tree.findall('inning'):
        inningnum = int(inning.attrib['num'])
        inningcount +=1
        for ihalf in inning:
            half = ihalf.tag
            if half=='top':
                defn = 'home'
                offn = 'away'
            else:
                defn = 'away'
                offn = 'home'
            for event in ihalf:
                #expect these to be atbats
                #but they could be 'action' items that 
                #signal a lineup/defensive change
                if event.tag == 'action':
                    action_event = event.attrib['event'].lower()
                    action_des = event.attrib['des']
                    if action_event == "defensive sub":
                        pid, pos, b_pos = decode_def_subst(event)
                        #Due to the complicated nature of some switches,
                        #we will simply insert the entering player into the
                        #proper places, and save sanity checks for each atbat
                        try:
                            assert pos is not None
                            assert b_pos is not None
                        except:
                            logging.error(
                                'couldn\'t handle \"%s\", dying without '
                                'saving %s',action_des, gid_string)
                            raise
                        
                        batting_order[defn][b_pos] = PLAYERS[pid]
                        if pos != 'DH' and pos != 'P':
                            defensive_players[defn][pos] = PLAYERS[pid]
                    elif action_event == 'defensive switch':
                        pid, pos = decode_def_switch(event)
                        try: 
                            assert pos is not None
                            if pos != 'DH' and pos != 'P':
                                defensive_players[defn][pos] = pid

                        except:
                            logging.info(
                                'couldn\'t handle \"%s\", doing nothing '
                                '',action_des, gid_string)
                            pass
                        
                    elif action_event == "offensive sub":
                        # pinch hitter
                        #expect: Pinch hitter <player> replaces <player>
                        #For now, I'm not going to care about this.
                        #Just use what the at-bat information determines to be
                        # the hitter
                        pass
                    elif action_event == "pitching substitution":
                        # change pitchers.
                        # expect <player> replaces <player>
                        #        <player> replaces <player> batting <n>th
                        #Again, not going to bother.  The AB description should
                        # be enough.
                        pass
                    else:
                        logging.info("doing nothing on \"%s\"", action_des)
                
                if event.tag == 'atbat':
                    #print event.tag
                    #First, check that we haven't fucked up the defense
                    #If we have for some reason, bomb off.
                    try:
                        assert len(set(defensive_players[defn])) == 8
                    except:
                        #print defensive_players
                        #print len(defensive_players[defn])
                        #print len(set(defensive_players[defn]))
                        logging.error('Defense is fubar, %s not saved', gid_string)
                        raise
                    atbat = process_atbat(event, GAME, inningnum, 
                                          half, PLAYERS, defensive_players[defn])
                    atbat.save()
                    abcount +=1
                    balls = 0
                    strikes = 0
                    for tpitch in event:
                        if tpitch.tag == 'pitch':
                            pitch, balls, strikes = process_pitch(
                                tpitch, atbat, balls, strikes, PLAYERS)
                            pitch.save()
                            pitchcount+=1
                        else:
                            pass
    logging.info("processed %d innings, %d players, %d atbats, %d pitches",
                 inningcount, len(PLAYERS), abcount, pitchcount)

def get_or_create_game(box_tree, player_tree, game_tree, umpire, gametype):
    gid_string = box_tree.attrib['game_id']
    game_pk = box_tree.attrib['game_pk']
    print gid_string
    try:
        GAME = Games.get(Games.game_pk == game_pk)
        logging.warn('Game %s already exists in the database, not altering')
    except Games.DoesNotExist:
        GAME = Games()
        GAME.gid_string = gid_string
        GAME.game = gid_string[-1]
        GAME.game_pk = box_tree.attrib['game_pk']
        GAME.away = box_tree.attrib['away_team_code']
        GAME.home = box_tree.attrib['home_team_code']
        datestring = box_tree.attrib['date']
        timestring = game_tree.attrib['local_game_time']
        GAME.date = datetime.date.fromtimestamp(time.mktime(time.strptime(
                    datestring, "%B %d, %Y")))
        GAME.errors_away=int(
            box_tree.find('linescore').attrib['away_team_errors'])
        GAME.errors_home=int(
            box_tree.find('linescore').attrib['home_team_errors'])
        GAME.hits_home=int(
            box_tree.find('linescore').attrib['home_team_hits'])
        GAME.hits_away=int(
            box_tree.find('linescore').attrib['away_team_hits'])
        GAME.runs_away=int(
            box_tree.find('linescore').attrib['away_team_runs'])
        GAME.runs_home=int(
            box_tree.find('linescore').attrib['home_team_runs'])
        GAME.ump = umpire
        GAME.type = gametype
        GAME.local_time = timestring
        #Skip the temperature and wind entries for now.
        #Get manager names
        for team in player_tree.findall('team'):
            for coach in team.findall('coach'):
                if coach.attrib['position'] == 'manager':
                    if team.attrib['type']=='away':
                        GAME.manager_away = ' '.join([coach.attrib['first'],
                                                      coach.attrib['last']])
                    else:
                        GAME.manager_home = ' '.join([coach.attrib['first'],
                                                      coach.attrib['last']])
    return GAME, gid_string

def process_pitch(xpitch, atbat, balls, strikes, players):
    ingameid = xpitch.attrib['id']
    pitch = Pitches.get_or_create(ab=atbat, ingameid=ingameid)
    pitch.ball = balls
    pitch.strike = strikes
    pitch.type = xpitch.attrib['type']
    if pitch.type == 'B':
        balls +=1
    elif pitch.type =='S' and strikes < 2:
        strikes +=1
    pitch.x = float(xpitch.attrib['x'])
    pitch.y = float(xpitch.attrib['y'])
    pitch.des = xpitch.attrib['des']
    #Now on to pitchf/x quantities!
    #ax,ay,az
    pitch.ax = try_attrib(xpitch,'ax',float)
    pitch.ay = try_attrib(xpitch,'ay',float)
    pitch.az = try_attrib(xpitch,'az',float)
    pitch.vx0 = try_attrib(xpitch,'vx0',float)
    pitch.vy0 = try_attrib(xpitch,'vy0',float)
    pitch.vz0 = try_attrib(xpitch,'vz0',float)
    pitch.x0 = try_attrib(xpitch,'x0',float)
    pitch.y0 = try_attrib(xpitch,'y0',float)
    pitch.z0 = try_attrib(xpitch,'z0',float)
    try:
        pitch.break_angle = try_attrib(xpitch,'break_angle',float)
        pitch.break_length = try_attrib(xpitch,'break_length',float)
        pitch.break_y = try_attrib(xpitch,'break_y',float)
    except UnicodeError:
        pitch.break_angle=None
        pitch.break_length=None
        pitch.break_y=None
    pitch.start_speed = try_attrib(xpitch,'start_speed',float)
    pitch.end_speed = try_attrib(xpitch,'end_speed',float)
    pitch.nasty = try_attrib(xpitch,'nasty',float)
    pitch.px = try_attrib(xpitch,'px',float)
    pitch.pz = try_attrib(xpitch,'pz',float)
    pitch.pfx_x = try_attrib(xpitch,'pfx_x',float)
    pitch.pfx_z = try_attrib(xpitch,'pfx_z',float)
    pitch.pitch_type = try_attrib(xpitch,'pitch_type')
    pitch.spin = try_attrib(xpitch,'spin',float)
    pitch.spin = try_attrib(xpitch,'spin_angle',float)
    svid = try_attrib(xpitch,'sv_id')
    if svid is not None:
        svid = int(svid.split('_')[-1])
        pitch.sv = svid
    pitch.type_confidence = try_attrib(xpitch, 'type_confidence',float)
    pitch.zone = try_attrib(xpitch, 'zone', int)
    on_1b = try_attrib(xpitch, 'on_1b',int)
    if on_1b is not None:
        pitch.on_1b = players[on_1b]
    on_2b = try_attrib(xpitch, 'on_2b',int)
    if on_2b is not None:
        pitch.on_2b = players[on_2b]
    on_3b = try_attrib(xpitch, 'on_3b',int)
    if on_3b is not None:
        pitch.on_3b = players[on_3b]
    pitch.timestamp = make_datetime(xpitch, 'tfs_zulu')
    return pitch, balls, strikes

def process_atbat(event, game, inning, half, players,defense):
    """Create or get an at-bat entry """
    # we don't want to submit a duplicate, so make sure
    # there isn't one in the database (but since we may have
    # died in processing pitches, we still want to return that instance
    try:
        atbat = Atbats.get(Atbats.gameid==game, Atbats.num==event.attrib['num'])
    except Atbats.DoesNotExist:
        atbat = Atbats.create(
            gameid = game, num = event.attrib['num'],
            pitcher = players[int(event.attrib['pitcher'])],
            batter = players[int(event.attrib['batter'])],
            ball = event.attrib['b'],
            strike = event.attrib['s'],
            out = event.attrib['o'],
            des = event.attrib['des'])
    b_height = try_attrib(event,'b_height')
    batter = atbat.batter
    if batter.height is None and b_height is not None:
        b_height = b_height.split('-')
        print b_height
        if len(b_height) == 2 and len(b_height[1])!=0 and len(b_height[0])!=0:
            bh = 12*int(b_height[0])+int(b_height[1])
            batter.height = bh
            batter.save()
    atbat.start_time = make_datetime(event,'start_tfs_zulu')
    atbat.def2 = defense['C']
    atbat.def3 = defense['1B']
    atbat.def4 = defense['2B']
    atbat.def5 = defense['3B']
    atbat.def6 = defense['SS']
    atbat.def7 = defense['LF']
    atbat.def8 = defense['CF']
    atbat.def9 = defense['RF']
    atbat.event = try_attrib(event,'event')
    atbat.inning = inning
    if half == 'top':
        atbat.half = 0
    else: 
        half=1
    atbat.stand = try_attrib(event,'stand')
    atbat.save()
    return atbat

def decode_def_subst(event):
    action_player_id = int(event.attrib['player'])
    action_des = event.attrib['des'].lower()
    #We have a defensive substitution.  Find out where
    #make the appropriate adjustment to defensive_players
    #expect:  <Player> replaces <postion> <player>
    #batting <n>th playing <position>.
    #         <player> replaces <player> batting <n>th playing <position>. 
    position_entering = None
    batting_order_entering = None
    #find position entering
    substr = action_des[action_des.find('playing')+8:]
   
    for key in pos_desc:
        if substr[:len(key)] == key:
            position_entering = key
            break
        else:
            for desc in pos_desc[key]:
                if substr[:len(desc)]==desc:
                    position_entering = key
                    break
        if position_entering is not None:
            break
        continue
    substr = action_des[action_des.find('as the')+7:]
    #logging.info('SUBSTRING %s',substr)
    for key in pos_desc:
        if substr[:len(key)]==key:
            position_entering = key
            break
        else:
            for desc in pos_desc[key]:
                if substr[:len(desc)] ==desc:
                    position_entering = key
                    break
        if position_entering is not None:
            break
        continue
        
    #find batting order position
    if 'designated hitter' in substr:
        position_entering = 'DH'
    substr = action_des[action_des.find('batting')+8:]
    batting_order_pos = int(substr[0])
    return action_player_id, position_entering, batting_order_pos

def decode_def_switch(event):
    action_player_id = int(event.attrib['player'])
    action_des = event.attrib['des'].lower()
    # We have a defensive switch
    #expect: from <position> to <position> for <player>
    #        <player> remains in the game as the <position>
    #Case 1:
    #Position entering
    position_to = None
    substr = action_des[action_des.find(' to ')+4:]
    if 'designated hitter' in substr:
        return action_player_id, 'DH'
    for key in pos_desc:
        if substr[:len(key)]==key:
            position_to = key
            break
        else:
            for desc in pos_desc[key]:
                if substr[:len(desc)] ==desc:
                    position_to = key
                    break
        if position_to is not None:
            break
        continue
    #Case 2:  
    substr = action_des[action_des.find('as the')+7:]
    logging.info('SUBSTRING %s',substr)
    for key in pos_desc:
        if substr[:len(key)]==key:
            position_to = key
            break
        else:
            for desc in pos_desc[key]:
                if substr[:len(desc)] ==desc:
                    position_to = key
                    break
        if position_to is not None:
            break
        continue
    if position_to is None:
        return None,None
    return action_player_id, position_to

def try_attrib(tree, desc, func=None):
    """try_attrib(tree, desc, func=None)  
    Tries to pull tree.attrib['desc'] from tree.  Applies func,
    so long as func can be called with only one string argument
    Returns None on KeyError """
    retval=None
    try:
        retval = tree.attrib[desc]
        if func is not None:
            retval=func(retval)
    except KeyError:
        pass
    return retval

def make_datetime(event, string):
    try:
        dts = event.attrib[string]
        #gameday gives datetimes in the format:
        #%Y-%m-%dT%H:%M%SZ
        #We are going to strip out the timezone info
        #and the letter T, and it seems the DB will accept that
        #We just have to remember it is a UTC time, and that when
        # we use it (like to get weather information), we need to
        # make sure we convert to the local timezone. (maybe)
        retval = ' '.join(dts[:19].split('T'))
    except KeyError:
        retval = None
    return retval

def _get_url(url):
    try:
        response = urlopen(url)
    except HTTPError as e:
        if e.code in [408, 504, 598, 599]:
            #try up to 10 more times to get the url
            for i in range(10):
                try:
                    response = urlopen(url)
                except HTTPError as e:
                    if e.code in [408, 504, 598, 599]:
                        continue
                    else:
                        logging.info('%s unavailable, aborting',url)
                        return
                 
                    return response
            logging.info('%s timed out on 10/10 tries.  Try later', url)
            return
        else:
            logging.info('%s unavailable, aborting',url)
            return
    except URLError:
        #try again up to 10 more times
        for i in range(10):
            try:
                response = urlopen(url)
            except URLError:
                continue
            return response
        logging.info('%s timed out on u10/10 tries.  Try later', url)
        raise
                     
    return response

if __name__ == '__main__':
    
            
    years = [2007, 2008, 2009, 2010, 2011, 2012, 2013]
    months = [1,2,3,4,5,6,7,8,9,10,11,12]
    database.connect()
    for year in years:
        for month in months:
            #if resuming from a previous run change the following conditions
            #and/or the start_date in the elif block to avoid repeating too
            #much.
            if year==2055 and month>3:
                #urls = diiscover_games(month, year, start_date=13)
                urls=[]
            elif year==2055 and month==6:
                urls = discover_games(month, year, start_date=27)
            else:
                urls = discover_games(month, year)
            for url in urls:
                print url
                #I keep the print statement here so I can check
                #progress.
                myGamedayTree = GamedayTree(url,'mlb')
                load_game(myGamedayTree)
