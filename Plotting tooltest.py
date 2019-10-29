# Made by Calvin Wong
# Last edited on May 8, 2019
# Python 2.7.14
# This script was created as a companion tool to the Stream Transect Tool
# created by Calvin Wong. This script takes elevation points created in the
# Stream Transect Tool and plots them on a graph.

import os
import arcpy
import numpy
import matplotlib.pyplot as plt

path = os.getcwd()
elevations = arcpy.GetParameterAsText(0)

# use the lineid value of the transect being plotted
initid = arcpy.GetParameterAsText(1)
lineid = int(initid) # id of line you wish to plot
initlength = arcpy.GetParameterAsText(2)
linelength = int(initlength)
print('Now generating plot')

array = arcpy.da.TableToNumPyArray(elevations, ['lineID', 'pos', 'RASTERVALU'],
                                   where_clause = "lineID = " + str(lineid))
sortarr = numpy.sort(array, order = ('pos'))
plt.xlabel('Position along transect (meters)')
plt.ylabel('Elevation (meters)')
plt.title('Elevation of transect ' + str(lineid))
plt.axis([0, linelength, min(sortarr['RASTERVALU'])-10,
          max(sortarr['RASTERVALU'])+10])
plt.plot(sortarr['pos'], sortarr['RASTERVALU'], 'b',
         sortarr['pos'], sortarr['RASTERVALU'], 'ob')
plt.savefig(arcpy.GetParameterAsText(3), dpi = 100, bbox_inches = 'tight')
print('Plot created')
print('Done')
