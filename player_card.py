import matplotlib.pyplot as plt
import utils

def plot_pfx(axes, xdata, ydata, pitchids,
             title='', xlabel='', ylabel='',marker='o'):
    for i in xrange(xdata.shape[0]):
        axes.plot(xdata[i], ydata[i], marker,
                  color = utils.pitch_descriptors[pitchids[i]][-1])
        axes.set_title(title)
        axes.set_xlabel(xlabel)
        axes.set_ylabel(ylabel)

def plot_sz(axes, xdata, ydata, result, title='', xlabel='X', ylabel='Z',
            marker='.'):
    for i in xrange(xdata.shape[0]):
        color = 'green' if result.lower().contains('ball') else 'red'
        axes.plot(xdata[i],ydata[i],marker,color=color)
    axes.set_title(title)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    axes.set_xlim(-5.,5.)
    axes.set_ylim(0.,8.)
def make_pitcher_plots(lastname, firstname, year, rotate_movements=False,
                       nodrag=False, stadium_name=None, rotated=False):
    pitches = utils.prop_to_y(utils.get_all_pitches(lastname, firstname, year),55)
    if stadium_name is not None:
        title = ' '.join([lastname, firstname, stadium_name])
    else:
        title = ' '.join([lastname, firstname])
    f1 = plt.figure()
    f1.title=title
    release_point = f1.add_subplot(111)
    plot_pfx(release_point, pitches['x0'], pitches['z0'], pitches['ptype'],
             title='release_point', xlabel='X(feet)', ylabel='Z(feet)')
    release_point.set_xlim(-5,5)
    release_point.set_ylim(0,8)
    f2 = plt.figure()
    f2.title=title
    movement = f2.add_subplot(111)
    movements = utils.movements(pitches, nodrag=nodrag, rotated=False)
    plot_pfx(movement, 12*movements[:,0], 12*movements[:,2], pitches['ptype'],
             title='pitch_movements', xlabel='X (inches)', ylabel='Z(inches)')
    
