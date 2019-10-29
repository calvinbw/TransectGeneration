# Made by Calvin Wong with help from David Green
# Code snippets repurposed from Linear Sampling Toolbox by Vini Indriasari
# Last edited May 8, 2019
# Python 2.7.14
# This tools aims to split a stream centerline at specified intervals and
# generate transects to determine depths along a stream

import arcpy
import os
import math
from arcpy.sa import *
import matplotlib
import matplotlib.pyplot as plt
import numpy
arcpy.CheckOutExtension('Spatial')

# set up environments
path = os.getcwd()
arcpy.env.workspace = path
arcpy.env.overwriteOutput = True

################# Inputs #####################

# input line feature class
inputline = arcpy.GetParameterAsText(0) # must be in UTM

# DEM raster
dem = arcpy.GetParameterAsText(1)

# spatial reference info
spatial_ref = arcpy.Describe(inputline).spatialReference

################## Outputs #####################

# shapefile to contain transect lines
outputlines = arcpy.GetParameterAsText(5)
transectdirname = os.path.dirname(outputlines)
transectbasename = os.path.basename(outputlines)
arcpy.CreateFeatureclass_management(transectdirname, transectbasename, 'POLYLINE',
                                    spatial_reference = spatial_ref)

# shapefile to contain points along the line
arcpy.CreateFeatureclass_management(path, 'points.shp', 'POINT',
                                    spatial_reference = spatial_ref)
outputpoints = '\\points.shp'
arcpy.AddField_management(outputpoints, 'lineID', 'SHORT')
arcpy.AddField_management(outputpoints, 'pos', 'FLOAT')

################# Input Variables #######################

# spacing between the transect lines 
linespacin = arcpy.GetParameterAsText(2) #meters
linespacing = int(linespacin)
# width of the transect line 
linelengt = arcpy.GetParameterAsText(3) #meters
linelength = int(linelengt)
# number of points on the transect line
tranpoint = arcpy.GetParameterAsText(4)
tranpoints = int(tranpoint)
################## Generate points along the stream ######################

# search cursor to look through streamline feature
scur = arcpy.da.SearchCursor(inputline, (['SHAPE@']))

intersects = [] # list to put generated points into

for row in scur:
    stream = row[0] # get stream geometry
    # define the length of stream to determine sampling locations
    dmax = stream.length 
    d = 0 # start generating points at start of line

    while d < dmax:
        point = stream.positionAlongLine(d)
        intersects.append(point) # add the point to the list
        d += linespacing # add the user-defined interval between points
        
del scur

#################### create transect lines #############################

transects = [] # list of transect lines across the stream

# split the stream into individual straight line segments
segments = arcpy.SplitLine_management(inputline, arcpy.Geometry())

# loop through the intersect points generated in previous step
for points in intersects:
    pt = points.firstPoint
    # get XY coords of point
    xcoord = pt.X
    ycoord = pt.Y

    # find the line segment overlapping the intersect point
    # code snippets in this block derived from Linear Sampling Toolbox developed by Vini Indriasari
    for line in segments:
        if line.contains(pt) or line.touches(pt):
            # get start and end of line segment
            startpoint = line.firstPoint
            endpoint = line.lastPoint

            # calculate slope angle 'a' of line segment
            rise = endpoint.Y - startpoint.Y
            run = endpoint.X - startpoint.X
            try:
                slope = rise/run
                a = math.atan(slope)
            except ZeroDivisionError:
                a = math.radians(90)

            # do some trig to find difference in xy
            wi = linelength/2
            dx = wi * math.cos(a)
            dy = wi * math.sin(a)

            # rotate origin side of the transect +90 deg
            xOri = xcoord + dy
            yOri = ycoord - dx

            # rotate destination side of transect -90 deg
            xDes = xcoord - dy
            yDes = ycoord + dx

            # create objects of the new origin and destination point
            ori = arcpy.Point(xOri, yOri)
            des = arcpy.Point(xDes, yDes)

            # add origin and destination to an array
            arr = arcpy.Array()
            arr.add(ori)
            arr.add(des)

            # Create a transect line out of the array
            line = arcpy.Polyline(arr, spatial_ref)

            # Append the new line into the transect list
            transects.append(line)

            # Input the transect line into the shapefile
            icur = arcpy.da.InsertCursor(outputlines, ['SHAPE@'])
            icur.insertRow([line])
            
            break #once a match is found, move onto next point in list
del icur
######################## generate the sampling points ######################

icur = arcpy.da.InsertCursor(outputpoints, ['SHAPE@', 'lineID', 'pos'])

# determine spacing between the sampling points
spacing = linelength / tranpoints

z = 0 # this number should end up matching with the transect line being processed

# create sample points
try:
    for line in transects:
        d = spacing/2
        for i in range(tranpoints):
            samp = []
            samppoint = line.positionAlongLine(d) # increment by fixed distance d
            samp.append(samppoint) # append the point to the samp list
            samp.append(z) # append number that SHOULD match line FID
            samp.append(d) # append position along line
            icur.insertRow(samp)
            d += spacing # add the interval between points
    # add the created points into the output feature class
        try:
            arcpy.CopyFeatures_management(samp, outputpoints)
        except:
            pass
        finally:
            z += 1
except:
    print('No transect lines created')
finally:
    print('Now calculating elevations')
del icur

###################### determine depth at each point#####################

elevpath = arcpy.GetParameterAsText(6)
elevhead = os.path.dirname(elevpath)
elevbasename = os.path.basename(elevpath)
elevations = arcpy.CreateFeatureclass_management(elevhead, elevbasename, 'POINT',
                                    spatial_reference = spatial_ref)
ExtractValuesToPoints(outputpoints, dem, elevations)
arcpy.DeleteField_management(elevations, 'Id') # get rid of unnecessary field

# check for empty elevations shapefile
if arcpy.management.GetCount(elevpath)[0] == '0':
    print('No elevations created. Check coordinate system of centerline and make sure the centerline is within the raster extent')
else:
    print('Elevations created')


##################### add the final points and transect line to the map#####################

mxd = arcpy.mapping.MapDocument('CURRENT')
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
transectlayer = arcpy.mapping.Layer(outputlines) # the transect lines layer
arcpy.mapping.AddLayer(df,transectlayer,'TOP')
elevationlayer = arcpy.mapping.Layer(elevpath) # the elvation points layer
arcpy.mapping.AddLayer(df, elevationlayer,'TOP')

################### delete intermediate shapefiles ######################

arcpy.Delete_management('splitline.shp')
arcpy.Delete_management('points.shp')
print('Done')
