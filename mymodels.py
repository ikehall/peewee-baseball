from peewee import *

database = MySQLDatabase('pbp', **{'passwd': 'thisisatotallyrandompasswordnoreally', 'user': 'bob'})

class UnknownFieldType(object):
    pass

class BaseModel(Model):
    class Meta:
        database = database

class Players(BaseModel):
    eliasid = IntegerField(primary_key=True)
    first = CharField()
    height = IntegerField()
    lahmanid = CharField()
    last = CharField()
    throws = CharField()

    class Meta:
        db_table = 'players'

class GameTypes(BaseModel):
    type = CharField()
    desc = CharField()
    
    class Meta:
        db_table = 'game_types'

class Stadiums(BaseModel):
    elevation = IntegerField()
    lat = FloatField()
    long = FloatField()
    name = CharField()

    class Meta:
        db_table = 'stadiums'

class Umpires(BaseModel):
    first = CharField()
    last = CharField()

    class Meta:
        db_table = 'umpires'


class Games(BaseModel):
    away = CharField()
    date = DateField()
    errors_away = IntegerField()
    errors_home = IntegerField()
    game = IntegerField()
    game_pk = IntegerField()
    gid_string = CharField()
    hits_away = IntegerField()
    hits_home = IntegerField()
    home = CharField()
    local_time = TimeField()
    manager_away = CharField()
    manager_home = CharField()
    runs_away = IntegerField()
    runs_home = IntegerField()
    temperature = IntegerField()
    type = ForeignKeyField(rel_model=GameTypes, db_column='type')
    ump = ForeignKeyField(rel_model=Umpires, db_column='ump')
    venue = ForeignKeyField(rel_model=Stadiums, db_column='venue')
    wind = IntegerField()
    wind_dir = CharField()

    class Meta:
        db_table = 'games'

class Atbats(BaseModel):
    ball = IntegerField()
    batter = ForeignKeyField(rel_model=Players, db_column='batter')
    bbtype = CharField()
    def2 = ForeignKeyField(rel_model=Players, db_column='def2')
    def3 = ForeignKeyField(rel_model=Players, db_column='def3')
    def4 = ForeignKeyField(rel_model=Players, db_column='def4')
    def5 = ForeignKeyField(rel_model=Players, db_column='def5')
    def6 = ForeignKeyField(rel_model=Players, db_column='def6')
    def7 = ForeignKeyField(rel_model=Players, db_column='def7')
    def8 = ForeignKeyField(rel_model=Players, db_column='def8')
    def9 = ForeignKeyField(rel_model=Players, db_column='def9')
    des = CharField()
    event = CharField()
    gameid = ForeignKeyField(rel_model=Games, db_column='gameid')
    half = IntegerField()
    hit_type = CharField()
    hit_x = FloatField()
    hit_y = FloatField()
    inning = IntegerField()
    num = IntegerField()
    outs = IntegerField()
    pitcher = ForeignKeyField(rel_model=Players, db_column='pitcher')
    pitcher_ab_seq = IntegerField()
    pitcher_seq = IntegerField()
    stand = CharField()
    start_time = DateTimeField()
    strike = IntegerField()
    sz_bot = FloatField()
    sz_top = FloatField()

    class Meta:
        db_table = 'atbats'

class PitchTypes(BaseModel):
    pitch = CharField()

    class Meta:
        db_table = 'pitch_types'

class Pitches(BaseModel):
    ab = ForeignKeyField(db_column='ab_id', rel_model=Atbats)
    air_density = FloatField()
    ax = FloatField()
    ay = FloatField()
    az = FloatField()
    ball = IntegerField()
    break_angle = FloatField()
    break_length = FloatField()
    break_y = FloatField()
    des = CharField()
    end_speed = FloatField()
    ingameid = IntegerField()
    my_pfx_x = FloatField()
    my_pfx_z = FloatField()
    my_pitch_type = IntegerField()
    nasty = IntegerField()
    on_1b = ForeignKeyField(rel_model=Players, db_column='on_1b')
    on_2b = ForeignKeyField(rel_model=Players, db_column='on_2b')
    on_3b = ForeignKeyField(rel_model=Players, db_column='on_3b')
    pfx_x = FloatField()
    pfx_z = FloatField()
    pitch_type = CharField()
    px = FloatField()
    pz = FloatField()
    spin = FloatField()
    spin_angle = FloatField()
    start_speed = FloatField()
    strike = IntegerField()
    sv = IntegerField(db_column='sv_id')
    timestamp = DateTimeField()
    type = CharField()
    type_confidence = FloatField()
    vx0 = FloatField()
    vy0 = FloatField()
    vz0 = FloatField()
    x = FloatField()
    x0 = FloatField()
    y = FloatField()
    y0 = FloatField()
    z0 = FloatField()

    class Meta:
        db_table = 'pitches'

