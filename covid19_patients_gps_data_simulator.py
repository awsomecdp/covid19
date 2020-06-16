import os
import pandas as pd
import requests
import json
import geocoder
from geopy import distance
from geopy.geocoders import Nominatim
from math import radians, sin, cos, acos
import geopy.distance
from datetime import datetime,timedelta
import boto3
import googlemaps
from googlemaps.convert import decode_polyline, encode_polyline
import json
from datetime import datetime
import math
import numpy
from collections import OrderedDict
import sys

s3 = boto3.resource('s3')

firehose = boto3.client('firehose')


def _calculate_distance(origin, destination):

    lat1, lon1 = origin['lat'], origin['lng']
    lat2, lon2 = destination['lat'], destination['lng']
    radius = 6371000  # metres

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d

def _round_up_time(time, period):

    # If time is an exact multiple of period, don't round up
    if time % period == 0:
        return time

    time = round(time)
    return time + period - (time % period)

def _fill_missing_times(times, lats, lngs, period):
    start_time = times[0]
    end_time = times[-1]
    
    new_times = range(start_time, end_time + 1, period)
    new_lats = numpy.interp(new_times, times, lats).tolist()
    new_lngs = numpy.interp(new_times, times, lngs).tolist()

    return new_times, new_lats, new_lngs

def get_points_along_path(maps_api_key, _from, _to, departure_time=None, period=600):

    if not departure_time:
        departure_time = datetime.now()

    gmaps = googlemaps.Client(key=maps_api_key)
    directions = gmaps.directions(_from, _to, departure_time=departure_time)
    #print(directions)
    steps = directions[0]['legs'][0]['steps']
    all_lats = []
    all_lngs = []
    all_times = []

    step_start_duration = 0
    step_end_duration = 0

    for step in steps:
        step_end_duration += step['duration']['value']
        points = decode_polyline(step['polyline']['points'])
        distances = []
        lats = []
        lngs = []
        start = None
        for point in points:
            if not start:
                start = point
                distance = 0
            else:
                distance = _calculate_distance(start, point)
                
            distances.append(distance)
            lats.append(point['lat'])
            lngs.append(point['lng'])
            
        missing_times = numpy.interp(distances[1:-1], [distances[0], distances[-1]], [step_start_duration, step_end_duration]).tolist()
        times = [step_start_duration] + missing_times + [step_end_duration]
        times = [_round_up_time(t, period) for t in times]
        
        times, lats, lngs = _fill_missing_times(times, lats, lngs, period)
        
        all_lats += lats
        all_lngs += lngs
        all_times += times

        step_start_duration = step_end_duration

    points = OrderedDict()
    for p in zip(all_times, all_lats,all_lngs):
        points[p[0]] = (round(p[1], 5), round(p[2],5))
        
    return points


if __name__ == '__main__':
    #if len(sys.argv) < 3:
     #   print('Usage: python ' + sys.argv[0] + ' AIzaSyAadFR1Tc5YD1xO_CFJfnG6beEsUA3Iotk "whitefield, banglore, karnataka, india"  "Marathahalli, banglore, karnataka, india"')
      #  print('For example')
        #print('Usage: python ' + sys.argv[0] + ' AJGHJ23242hBdDAXJDOSS "HashedIn Technologies, Bangalore"  "World Trade Centre, Bangalore"')
      #  exit(-1)
      #config_df= pd.read_excel('C:\\Users\\mmadired\\Documents\\CG_\\AWSomeBuilders_Project\\Testdata\\gps_enabled_mobiles.xlsx', index_col=None,usecols='A,B, C, D,E, F,G,H,I')
      config_df= pd.read_excel('s3://cg-covid19-poc/gps_enabled_mobiles/gps_enabled_mobiles.xlsx', index_col=None,usecols='A,B, C, D,E, F,G,H,I')
      #with open('C:\\Users\\mmadired\\Documents\\CG_\\AWSomeBuilders_Project\\Testdata\\gps_data_karnataka_11062020_2ndrun.csv', 'w') as f:
            for index,row in config_df.iterrows():
                    if row["generate"]=='Y':
                            print(str(row["Mobile"]))
#                        with open('C:\\Users\\mmadired\\Documents\\CG_\\AWSomeBuilders_Project\\Testdata\\'+str(row["Mobile"])+'_gps_data_2ndrun.json', 'w',newline='\n') as mf:
                            url = 'https://api.postalpincode.in/pincode/'+str(row["startpincode"])
                            req = requests.get(url)
                            #print(req.json())
                            print(req.json()[0]['PostOffice'][0]['Name'])
                            startaddress=(req.json()[0]['PostOffice'][0]['Division']+' '+req.json()[0]['PostOffice'][0]['State']+' '+req.json()[0]['PostOffice'][0]['Country'])
                            #coordinates1 =(startlocation.latitude, startlocation.longitude)
                            #print(coordinates1)
                            url = 'https://api.postalpincode.in/pincode/'+str(row["endpincode"])
                            #print(url)
                            req = requests.get(url)
                            endaddress=(req.json()[0]['PostOffice'][0]['Division']+' '+req.json()[0]['PostOffice'][0]['State']+' '+req.json()[0]['PostOffice'][0]['Country'])
                            #print(url)
                            #print(req.json())
                            print(req.json()[0]['PostOffice'][0]['Name'])
                            points = get_points_along_path("AIzaSyAadFR1Tc5YD1xO_CFJfnG6beEsUA3Iotk ",startaddress , endaddress)
                            listofcoor=[]
                            #print("List of points along the route")
                            #print("------------------------------")
                            for time, geo in points.items():
                                #print(datetime.now())
                                starttime=(datetime.now()-timedelta(days=0)).replace(minute=0, hour=0, second=0, microsecond=0)
                                starttime=starttime+timedelta(seconds=time)
                                # #print(time, geo[0],geo[1])
                                # #listofTuples = [("col1:",str(geo[0])),("col2:",str(geo[1])),("col3:",str(row["IMEI"])),("col4:",str(row["Mobile"])),("col5:",str(starttime.strftime('%Y:%m:%d %H:%M:%S')))]
                                # listofTuples = [('lat',geo[0]), ('long',geo[1]),('imei',row["IMEI"]), ('Mobile',row["Mobile"]),('Timestamp',starttime.strftime('%Y:%m:%d %H:%M:%S'))]
                                # dct = dict(listofTuples)
                                # response = firehose.put_record(
                                #             DeliveryStreamName='covidgpsstream',
                                #             Record={
                                #                        'Data': json.dumps(dct, indent=2,separators=(", ", ": "))
                                #                 }
                                #             )
                                blobstr = str(geo[0])+','+str(geo[1])+','+str(row["IMEI"])+","+str(row["Mobile"])+','+str(starttime.strftime('%Y-%m-%d %H:%M:%S')+'\n')
                                response = firehose.put_record(
                                            DeliveryStreamName='covidgpsstream',
                                            Record={
                                                        'Data': blobstr
                                                }
                                            )
   
            
