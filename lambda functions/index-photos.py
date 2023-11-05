import json
import boto3
import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

host = 'search-photos-dbzywnz6cgrj5ggwg4wfrrjzzy.us-east-1.es.amazonaws.com'
region = 'us-east-1'

def s3_get_custome_labels(bucket, key):
    s3 = boto3.client('s3')
    response = s3.head_object(Bucket = bucket, Key = key)
    labels = []
    print(response)
    if len(response['Metadata']) == 0:
        return labels
    labels = response['Metadata']['customlabels'].split(',')
    return labels

def rek_get_labels(bucket, key):
    rek = boto3.client('rekognition')
    response = rek.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        MaxLabels=10,
        MinConfidence=90)
    labels = response['Labels']
    return labels

def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

client = OpenSearch(hosts=[{
    'host': host,
    'port': 443
}],
    http_auth=get_awsauth(region, 'es'),
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection)

def opensearch(object_key, labels):
    os_insert = {
        "objectKey": object_key,
        "bucket": "photos-s3-bucket-b2-6998",
        "createdTimestamp": datetime.datetime.now(),
        "labels": labels
    }

    # Insert data into Opensearch
    res = client.index(index="photos", body=os_insert)
    return res

def lambda_handler(event, context):
    bucket_name = 'photos-s3-bucket-b2-6998'
    object_key = str(event['Records'][0]['s3']['object']['key'])

    cus_labels = s3_get_custome_labels(bucket_name, object_key)
    rek_labels = rek_get_labels(bucket_name, object_key)

    labels = cus_labels + [label['Name'].lower() for label in rek_labels]
    os_return = opensearch(object_key, labels)

    return {
        'statusCode': 200,
        'body': json.dumps('Upload successfully!')
    }
