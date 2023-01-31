# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# PURPOSE:
#   Normalize, hash, and partition datasets for Snap.
#   Currently only supporting JSON file formats.
#
# INPUT:
#   --source_bucket: S3 bucket containing input file (optional)
#   --output_bucket: S3 bucket for output data (optional)
#   --source_key: S3 key of input file also used as the key for the outputted file
#   --pii_fields: json formatted array containing column names that need to be hashed and the PII type of their data. The type must be PHONE, EMAIL,or MOBILE_AD_ID.
#   --segment_name: the name of the specific segment/audience that the data is being uploaded for
#
# OUTPUT:
#   - Transformed data files in user-specified output bucket
#
# SAMPLE COMMAND-LINE USAGE:
#
#    export JOB_NAME=mystack-GlueStack-12BSLR8H1F79M-snap-transformation-job
#    export SOURCE_BUCKET=mybucket
#    export SOURCE_KEY=mydata.json
#    export OUTPUT_BUCKET=mystack-etl-artifacts-zmtmhi
#    export PII_FIELDS='[{"column_name":"e-mail", "pii_type":"EMAIL"}, {"column_name":"phone_number", "pii_type":"PHONE"}, {"column_name":"mobile_advertiser_id", "pii_type":"MOBILE_AD_ID"}]'
#    export SEGMENT_NAME='myaudience'
#    export REGION=us-east-1
#    aws glue start-job-run --job-name $JOB_NAME --arguments '{"--source_bucket": "'$SOURCE_BUCKET'", "--output_bucket": "'$OUTPUT_BUCKET'", "--source_key": "'$SOURCE_KEY'", "--pii_fields": "'$PII_FIELDS'"}' --segment_name $SEGMENT_NAME --region $REGION
#
###############################################################################

import sys
import os
import json
import math
import hashlib
import numpy as np
import pandas as pd
import awswrangler as wr
from awsglue.utils import getResolvedOptions

snap_api_limit = 100000

###############################
# PARSE ARGS
###############################

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'source_bucket', 'source_key', 'output_bucket', 'pii_fields', 'segment_name'])
print("Runtime args for job " + args['JOB_NAME'] + ":")
print(args)
if 'source_bucket' not in args:
    sys.exit("ERROR: Missing source_bucket job parameter")
if 'source_key' not in args:
    sys.exit("ERROR: Missing source_key job parameter")
if 'output_bucket' not in args:
    sys.exit("ERROR: Missing output_bucket job parameter")
if 'segment_name' not in args:
    sys.exit("ERROR: Missing segment_name job parameter")

pii_fields = []
if 'pii_fields' in args:
    pii_fields = json.loads(args['pii_fields'])

###############################
# LOAD INPUT DATA
###############################

source_bucket = args['source_bucket']
source_key = args['source_key']
output_bucket = args['output_bucket']
output_key = os.path.splitext(source_key)[0]
segment_name = args['segment_name']

chunksize = 2000

print('Reading input file from: ')
print('s3://'+source_bucket+'/'+source_key)

dfs = wr.s3.read_json(path=['s3://'+source_bucket+'/'+source_key], chunksize=chunksize, lines=True, orient='records')
df = pd.DataFrame()
for chunk in dfs:
    # Save each chunk
    df = pd.concat([df, chunk])
    
###############################
# DATA NORMALIZATION
###############################

# df1 will contain integer, float, and datetime columns. This is not currently being used 
df1 = df.select_dtypes(exclude=[object])
# df2 will contain string columns
df2 = df.select_dtypes(include=[object])
df2 = df2.apply(lambda x: x.astype(str).str.normalize('NFKD').str.strip())

for field in pii_fields:
    if field['pii_type'] == "PHONE":
        column_name = field['column_name']
        df2[column_name] = df2[column_name].str.replace(r'[^0-9]+', '').str.lstrip('0')
    elif field['pii_type'] == "EMAIL":
        column_name = field['column_name']
    elif field['pii_type'] == "MOBILE_AD_ID":
        column_name = field['column_name']
        df2[column_name] = df2[column_name].str.lower()
    
###############################
# PII HASHING
###############################

for field in pii_fields:
    column = field['column_name']
    df2[column] = df2[column].apply(lambda x: hashlib.sha256(x.encode()).hexdigest())
    df2.rename(columns = {column:field['pii_type']+'_SHA256'}, inplace = True)

###############################
# SAVE OUTPUT DATA
###############################

# df = pd.concat([df1, df2], axis=1)
# Melt and rename dataframe to fit input of Snap Activator
df2 = df2.melt()
df2.rename(columns = {'variable':'schema', 'value':'hash'}, inplace = True)
df2['segment_name'] = segment_name

list_df = np.array_split(df2, math.ceil(df2.shape[0]/snap_api_limit))
num_file_digits = int(math.log10(len(list_df)))+1

for i in range(len(list_df)):
    output_file = 's3://'+output_bucket+'/output/snap/'+segment_name+'/'+output_key+str(i+1).zfill(num_file_digits)+'.csv'+'.gz'
    wr.s3.to_csv(df=list_df[i], path=output_file, compression='gzip')
