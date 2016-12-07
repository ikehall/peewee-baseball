from peewee import *

#database = MySQLDatabase('pbp', **{'passwd': 'thisisatotallyrandompasswordnoreally', 'user': 'bob'})

database = SqliteDatabase('/home/isaac/pfx.db')

class UnknownFieldType(object):
    pass

class BaseModel(Model):
    class Meta:
        database = database

class Players(BaseModel):
    eliasid = IntegerField(primary_key=True)
    first = CharField()
    height = IntegerField(null=True)
    lahmanid = CharField(null=True)
    last = CharField()
    throws = CharField()

    #class Meta:
        #db_table = 'players'

class GameTypes(BaseModel):
    type = CharField()
    desc = CharField(null=True)
    
    #class Meta:
        #db_table = 'game_types'

class Stadiums(BaseModel):
    elevation = IntegerField(null=True)
    lat = FloatField(null=True)
    long = FloatField(null=True)
    name = CharField()

    #class Meta:
        #db_table = 'stadiums'

class Umpires(BaseModel):
    first = CharField()
    last = CharField()

    #class Meta:
        #db_table = 'umpires'


class Games(BaseModel):
    away = CharField(null=True)
    date = DateField(null=True)
    errors_away = IntegerField(null=True)
    errors_home = IntegerField(null=True)
    game = IntegerField(null=True)
    game_pk = IntegerField()
    gid_string = CharField(null=True)
    hits_away = IntegerField(null=True)
    hits_home = IntegerField(null=True)
    home = CharField(null=True)
    local_time = TimeField(null=True)
    manager_away = CharField(null=True)
    manager_home = CharField(null=True)
    runs_away = IntegerField(null=True)
    runs_home = IntegerField(null=True)
    temperature = IntegerField(null=True)
    type = ForeignKeyField(GameTypes, related_name='bgames', null=True)
    ump = ForeignKeyField(Umpires, related_name='ugames', null=True)
    venue = ForeignKeyField(Stadiums, related_name='vgames', null=True)
    wind = IntegerField(null=True)
    wind_dir = CharField(null=True)

    #class Meta:
        #db_table = 'games'
        

class Atbats(BaseModel):
    ball = IntegerField(null=True)
    batter = ForeignKeyField(Players, related_name='patbats')
    bbtype = CharField(null=True)
    def2 = ForeignKeyField(Players, related_name='def_c_ab',null=True)
    def3 = ForeignKeyField(Players, related_name='def_1b_ab',null=True)
    def4 = ForeignKeyField(Players, related_name='def_2b_ab',null=True)
    def5 = ForeignKeyField(Players, related_name='def_3b_ab',null=True)
    def6 = ForeignKeyField(Players, related_name='def_ss_ab',null=True)
    def7 = ForeignKeyField(Players, related_name='def_lf_ab',null=True)
    def8 = ForeignKeyField(Players, related_name='def_cf_ab',null=True)
    def9 = ForeignKeyField(Players, related_name='def_rf_ab',null=True)
    des = CharField(null=True)
    event = CharField(null=True)
    gameid = ForeignKeyField(Games, related_name='ab_in_game')
    half = IntegerField(null=True)
    hit_type = CharField(null=True)
    hit_x = FloatField(null=True)
    hit_y = FloatField(null=True)
    inning = IntegerField(null=True)
    num = IntegerField()
    outs = IntegerField(null=True)
    pitcher = ForeignKeyField(Players, related_name='pitched_ab',null=True)
    pitcher_ab_seq = IntegerField(null=True)
    pitcher_seq = IntegerField(null=True)
    stand = CharField(null=True)
    start_time = DateTimeField(null=True)
    strike = IntegerField(null=True)
    sz_bot = FloatField(null=True)
    sz_top = FloatField(null=True)

    #class Meta:
        #db_table = 'atbats'

class PitchTypes(BaseModel):
    pitch = CharField()

    #class Meta:
        #db_table = 'pitch_types'

class Pitches(BaseModel):
    ab = ForeignKeyField(Atbats, related_name='ab_pitched')
    air_density = FloatField(null=True)
    ax = FloatField(null=True)
    ay = FloatField(null=True)
    az = FloatField(null=True)
    ball = IntegerField(null=True)
    break_angle = FloatField(null=True)
    break_length = FloatField(null=True)
    break_y = FloatField(null=True)
    des = CharField(null=True)
    end_speed = FloatField(null=True)
    ingameid = IntegerField()
    my_pfx_x = FloatField(null=True)
    my_pfx_z = FloatField(null=True)
    my_pitch_type = IntegerField(null=True)
    nasty = IntegerField(null=True)
    on_1b = ForeignKeyField(Players, related_name='runner_1b', null=True)
    on_2b = ForeignKeyField(Players, related_name='runner_2b', null=True)
    on_3b = ForeignKeyField(Players, related_name='runner_3b', null=True)
    pfx_x = FloatField(null=True)
    pfx_z = FloatField(null=True)
    pitch_type = CharField(null=True)
    px = FloatField(null=True)
    pz = FloatField(null=True)
    spin = FloatField(null=True)
    spin_angle = FloatField(null=True)
    start_speed = FloatField(null=True)
    strike = IntegerField(null=True)
    sv = IntegerField(db_column='sv_id',null=True)
    timestamp = DateTimeField(null=True)
    type = CharField(null=True)
    type_confidence = FloatField(null=True)
    vx0 = FloatField(null=True)
    vy0 = FloatField(null=True)
    vz0 = FloatField(null=True)
    x = FloatField(null=True)
    x0 = FloatField(null=True)
    y = FloatField(null=True)
    y0 = FloatField(null=True)
    z0 = FloatField(null=True)

    #class Meta:
        #db_table = 'pitches'

def create_tables():
    database.connect()
    database.create_tables([Players, GameTypes, Stadiums, Umpires,
                            Games, Atbats, PitchTypes, Pitches])
