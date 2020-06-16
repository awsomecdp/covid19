
below sqls, basically transfer GPS data to multiple formats for Dashboading, Visualization and loading into Neptune Graph DB Edges format 
In this step we are creating external table to pointing path to GPS raw data posted by Kinesis.

CREATE EXTERNAL TABLE IF NOT EXISTS awsomecovid19.covid19_gps_tracker_data (
  latitude string,
  longitude string,
  imei string,
  Mobile string,
  Timestamp string
)  
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = ',',
  'field.delim' = ','
) LOCATION 's3://gps-data-firehose/'
TBLPROPERTIES ('has_encrypted_data'='false');

Step 9: views to read Step 8 table
CREATE OR REPLACE VIEW covid19_gps_data AS 
SELECT *
FROM
  awsomecovid19.covid19_gps_tracker_data;

CREATE OR REPLACE VIEW covid19_gps_data_neptune AS 
SELECT *
FROM
  covid19_gps_data;

Step 10: In this step calculating distance between two patients coordinates. using haversine distance formula.and its only for last one hour GPS data.

CREATE OR REPLACE VIEW covid19_gps_data_neptune_closedistance AS 
SELECT
  a.*
, "b"."latitude" "latitude2"
, "b"."longitude" "longitude2"
, "b"."imei" "imei2"
, "b"."mobile" "mobile2"
, "b"."timestamp" "timestamp2"
, ("acos"((("sin"((("pi"() * CAST("a"."latitude" AS double)) / 180.0)) * "sin"((("pi"() * CAST("b"."latitude" AS double)) / 180.0))) + (("cos"((("pi"() * CAST("a"."latitude" AS double)) / 180.0)) * "cos"((("pi"() * CAST("b"."latitude" AS double)) / 180.0))) * "cos"(((("pi"() * CAST("b"."longitude" AS double)) / 180.0) - (("pi"() * CAST("a"."longitude" AS double)) / 180.0)))))) * 6371) "distance"
FROM
  awsomecovid19.covid19_gps_data_neptune a
, awsomecovid19.covid19_gps_data_neptune b
WHERE CAST("a"."timestamp" AS timestamp) BETWEEN cast(current_timestamp as timestamp) - INTERVAL  '1' HOUR and cast (current_timestamp as timestamp)
 and CAST("b"."timestamp" AS timestamp) BETWEEN cast(current_timestamp as timestamp) - INTERVAL  '1' HOUR and cast (current_timestamp as timestamp);

Step 11:
In this we are taking only below 10km distance as relationships into consideration. and fetching patient no of mobile1 from master table.

CREATE OR REPLACE VIEW covid19_gps_data_neptune_within10km AS 
SELECT
  "a"."mobile"
, "a"."mobile2"
, "latitude"
, "longitude"
, "latitude2"
, "longitude2"
, cast("distance" as integer) as distance 
, "b"."patientno"
, "timestamp"
FROM
  covid19_gps_data_neptune_closedistance a
, awsomecovid19.covid19_gps_enabled_mobiles b
WHERE (("distance" BETWEEN 0.001 AND 10.0) AND (CAST("a"."mobile" AS varchar) = CAST("b"."mobile" AS varchar)))
 and cast(distance as varchar)!='NaN';


Step 12:

Below step we are fetching patients no of mobile2 from master table.
CREATE OR REPLACE VIEW covid19_gps_data_neptune_within10km_p2 AS 
SELECT DISTINCT
  "a"."mobile"
, "a"."mobile2"
, "latitude"
, "longitude"
, "latitude2"
, "longitude2"
, "distance"
, "a"."patientno"
, "timestamp"
, "b"."patientno" "patientno_contacted"
FROM
  covid19_gps_data_neptune_within10km a
, awsomecovid19.covid19_gps_enabled_mobiles b
WHERE ((CAST("a"."mobile2" AS varchar) = CAST("b"."mobile" AS varchar)));

Step 13:

In this step we are eliminating all same distance/same patient nos from final dataset.

CREATE OR REPLACE VIEW covid19_nearby_distances AS 
SELECT
  CONCAT(cast("row_number"() OVER () as varchar),replace(replace(replace(replace(cast(current_timestamp AS VARCHAR),'UTC'),'-'),':'),'.')) "id"
, 'distance' "label"
, "replace"("patientno", 'P-', '') "fromp"
, "replace"("patientno_contacted", 'P-', '') "top"
, CAST("distance" AS integer) "distance"
, "timestamp" "timestamp"
FROM
  covid19_gps_data_neptune_within10km_p2 a
WHERE ("patientno" <> "patientno_contacted") ;

