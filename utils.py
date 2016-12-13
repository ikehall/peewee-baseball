import numpy as np
from peewee import *
from mymodels import *
from datetime import datetime

g = -32.174 #ft/s
K = 0.00544

pitch_dtype = np.dtype({
    'names':['x0','y0','z0','vx0','vy0','vz0','ax','ay','az','px','pz','ptype'],
    'formats':['f8','f8','f8','f8','f8','f8','f8','f8','f8','f8','f8','a2'],
    #'offsets':[0,8,16,24,32,40,48,56,64,72,80,88],
    #'itemsize':90
})

pitch_descriptors = {'FA': ('Four Seam Fastball', 'blue'),
                     'FF': ('Four Seam Fastball', 'blue'),
                     'SI':('Sinker','gray'),
                     'FT':('Sinker', 'gray'),
                     'FC':('Cutter','purple'),
                     'CT':('Cutter','purple'),
                     'FS':('Splitter','green'),
                     'SP':('Splitter','green'),
                     'FO':('Forkball','yellow'),
                     'SL':('Slider','red'),
                     'CU':('Curveball','cyan'),
                     'KC':('Curveball','cyan'),
                     'CH':('Changeup','magenta'),
                     'SC':('Screwball','lightseagreen'),
                     'KN':('Knuckleball','tomato'),
                     'UN':('Unknown','black')}

def get_all_pitches(last, first, years=None, stadium=None):
    pq = Pitches.select().join(Atbats).join(Players, on=Atbats.pitcher)
    pq = pq.where(Players.last==last,
                  Players.first==first)

    if years is not None or stadium is not None:
        pq = pq.switch(Atbats).join(Games)
    if years is not None:
        if isinstance(years, str) or isinstance(years, int):
            d1 = datetime(int(years), 1, 1)
            d2 = datetime(int(years)+1, 1, 1)
        else:
            d1 = datetime(int(years[0]),1,1)
            d2 = datetime(int(years[1]+1),1,1)
        pq = pq.where(Games.date > d1, Games.date < d2)
    if stadium is not None:
        if years is not None:
            pq = pq.switch(Games)
        pq=pq.join(Stadiums).where(Stadiums.name==stadium)
        
        
    #print len(pq)
    #print pq.sql()
    #gms = Games.filter(date__gt=datetime(year,1,1),
    #                   date__lt=datetime(year+1,1,1))
    #pq = Pitches.filter(ab__gameid__in=gms,
    #                            ab__pitcher__last=last,
    #                            ab__pitcher__first=first)

    pitches=[]
    pitch_types = []
    for pitch in pq:
        if 'Intent' in pitch.des or 'Pitchout' in pitch.des:
            continue
        if pitch.pfx_x is not None:
            pitches.append(
                (pitch.x0, pitch.y0, pitch.z0,
                 pitch.vx0, pitch.vy0, pitch.vz0,
                 pitch.ax, pitch.ay, pitch.az,
                 pitch.px, pitch.pz, pitch.pitch_type)
            )
            pitch_types.append(pitch.pitch_type)
    parray = np.array(pitches, dtype=pitch_dtype)
    return parray

def get_balls(last, first, year):
    gms = Games.filter(date__gt=datetime(year,1,1),
                       date__lt=datetime(year+1, 1,1))
    pitch_query = Pitches.filter(ab__gameid__in=gms,
                                 ab__pitcher__last=last,
                                 ab__pitcher__first=first,
                                 des="Ball")
    
def rowdot(a,b):
    return np.sum(a*b)

def remove_gravity(pitches):
    aminusg = pitches[:,np.newaxis][['ax','ay','az']].copy()
    aminusg['az'] -= g
    aminusg.dtype='f8'
    return aminusg
    
def drag(pitches):
    """drag(pitches) --> NdArray (shape=Nx3)
    returns an array of the x,y,z components of drag for each pitch
    -v*(|a.v|/|v.v|) where v = vbar
    """
    aminusg = remove_gravity(pitches)
    vbar = average_velocities(pitches)
    vbarmag = rowdot(vbar,vbar)
    adrag = rowdot(aminusg, vbar)
    adrag = -np.abs(adrag/vbarmag)*vbar
    return adrag

def magnus(pitches, nodrag=True):
    aminusg = remove_gravity(pitches)
    if not nodrag:
        return aminusg
    else:
        adrag = drag(pitches)
        return aminusg - adrag

def rotated_magnus(pitches, nodrag=True):
    adrag = drag(pitches)
    amagnus = magnus(nodrag)
    dxy = np.sqrt(rowdot(adrag[:,:2], adrag[:,:2]))
    dxyz = np.sqrt(rowdot(adrag, adrag))
    rmat11 = adrag[:,1]/dxy
    rmat12 = -adrag[:,0]/dxy
    rmat13 = np.zeros(pitches.shape[0],dtype='f8')
    rmat21 = adrag[:,0]/dxyz
    rmat22 = adrag[:,1]/dxyz
    rmat23 = adrag[:,2]/dxyz
    rmat31 = -adrag[:,0]*adrag[:,2]/(dxy*dxyz)
    rmat32 = -adrag[:,1]*adrag[:,2]/(dxy*dxyz)
    rmat33 = dxy/dxyz
    rmat = np.column_stack((rmat11, rmat12, rmat13,
                            rmat21, rmat22, rmat23,
                            rmat31, rmat32, rmat33)).reshape(pitches.shape[0],
                                                             3,3)
    return np.array([rmat[i,:,:].dot(amagnus[i,:]) for i in range(amagnus.shape[0])])


def movements(pitches, y0=40.0, yf=1.417, nodrag=True, rotated=True):
    newpitches = prop_to_y(pitches, y0)
    T = time_of_flight(newpitches, yf)
    #print T
    amagnus = rotated_magnus(newpitches, nodrag) if rotated else magnus(newpitches, nodrag)
    print amagnus
    pfx = 0.5*amagnus*T[:, np.newaxis]**2
    return pfx

def v0(pitches, y0=55.0):
    newpitches = prop_to_y(pitches, y0)
    vels = newpitches[:,np.newaxis][['vx0','vy0','vz0']].copy()
    vels.dtype='f8'
    return np.sqrt(rowdot(vels, vels))
    
    
def time_of_flight(pitches, yf=1.417):
    vyf = -np.sqrt(pitches['vy0']**2 + 2.0*pitches['ay']*(yf-pitches['y0']))
    T = (vyf - pitches['vy0'])/pitches['ay']
    return T
    
def final_velocity(pitches, yf=1.417):
    T = time_of_flight(pitches, yf)
    vfx = pitches['vx0']+pitches['ax']*T
    vfy = pitches['vy0']+pitches['ay']*T
    vfz = pitches['vz0']+pitches['az']*T
    return np.column_stack((vfx, vfy, vfz))
    
def average_velocities(pitches,y0=55.0, yf=1.417):
    if not np.all(pitches['y0']==y0):
        pprime = prop_to_y(pitches, y0)
    else:
        pprime = pitches
    T = time_of_flight(pprime, yf)
    vxbar = (2*pprime['vx0'] + pprime['ax']*T)/2
    vybar = (2*pprime['vy0'] + pprime['ay']*T)/2
    vzbar = (2*pprime['vz0'] + pprime['az']*T)/2
    return np.column_stack((vxbar, vybar, vzbar))

    
def prop_with_delta_t(pitches, pdt):
    '''Propagate pitch trajectory so that initial position is at
    a new delta_t'''
    newpitches=pitches.copy()
    newpitches['x0'] += pitches['vx0']*pdt + 0.5*pitches['ax']*pdt**2
    newpitches['y0'] += pitches['vy0']*pdt + 0.5*pitches['ay']*pdt**2
    newpitches['z0'] += pitches['vz0']*pdt + 0.5*pitches['az']*pdt**2
    newpitches['vx0'] += pitches['ax']*pdt
    newpitches['vy0'] += pitches['ay']*pdt
    newpitches['vz0'] += pitches['az']*pdt
    return newpitches
    
    
def prop_to_y(pitches, y):
    """propagate pitches to a given y value"""
    #solve the quadratic 0 = x0-xf + v0x*dt + 0.5*ax*dt**2
    #to get delta_t.
    if np.all(pitches['y0']==y):
        return pitches
    b = pitches['vy0']
    c = pitches['y0']-y
    a = pitches['ay']/2.0
    x1 = (-b+np.sqrt(b**2 - 4*a*c))/(2.0*a)
    x2 = 2.0*c/(-b+np.sqrt(b**2-4*a*c))
    pdt = (c/(a*x1))*(c<=0) + x2*(c>0)
    return prop_with_delta_t(pitches, pdt)
    
def CD(pitches, y0=55.0):
    adrag = drag(pitches)
    adragMag = np.sqrt(rowdot(adrag, adrag))
    vbar = v0(pitches, y0)
    return adragMag/(K*vbar)

def CL(pitches, y0=55.0):
    amagnus = magnus(pitches, nodrag=True)
    vbar = v0(pitches, y0)
    amagnusMag = np.sqrt(rowdot(amagnus, amagnus))
    return amagnusMag/(K*vbar)
    
