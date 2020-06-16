
Step 14: 
----------------------------------------------------------------------------------
-----------lambda to generate neptune format file
In this step we are creating Lambda to extract Graph DB format data of last one hour edges(Two patients criscrossed coordinates).

import boto3
import time

def lambda_handler(event, context):
        client = boto3.client('athena')
        queryStart = client.start_query_execution(
                            QueryString = 'SELECT distinct id as "~id",label as "~label",fromp as "~from",top as "~to",distance,timestamp FROM awsomecovid19.covid19_nearby_distances;',
                            QueryExecutionContext = {
                                                    'Database': 'awsomecovid19'
                                                    }
                                                ,
                            ResultConfiguration = { 
                                                 'OutputLocation': 's3://cg-covid19-poc/gps_data_neptune/'
                                                }
                            )
