import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

host = 'search-photos-dbzywnz6cgrj5ggwg4wfrrjzzy.us-east-1.es.amazonaws.com'
region = 'us-east-1'

def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

def query(term):
    query = {
        "size": 20,
        "query": {
            "match": {
                "labels": term
            }
        }
    }

    client = OpenSearch(hosts=[{
        'host': host,
        'port': 443
    }],
        http_auth=get_awsauth(region, 'es'),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection)

    res = client.search(index='photos', body=query)
    print(res)

    hits = res['hits']['hits']
    results = []
    for hit in hits:
        results.append(hit['_source'])

    return results

def lambda_handler(event, context):
    querystring = event['params']['querystring']['q']

    lexv2 = boto3.client('lexv2-runtime')

    response = lexv2.recognize_text(
            botId='5NVIZLNPJQ', # MODIFY HERE
            botAliasId='TSTALIASID', # MODIFY HERE
            localeId='en_US',
            sessionId='testuser',
            text=querystring)

    opensearch = boto3.client('opensearch')

    key1, key2 = '', ''
    ans1, ans2 = '', ''

    if response['interpretations'][0]['intent']['slots']['keywords'] is not None:
        key1 = response['interpretations'][0]['intent']['slots']['keywords']['value']['resolvedValues'][0]
        ans1 = query(key1)

    if response['interpretations'][0]['intent']['slots']['otherword'] is not None:
        key2 = response['interpretations'][0]['intent']['slots']['otherword']['value']['resolvedValues'][0]
        ans2 = query(key2)

    photos = []
    photos_set = set()
    s3url = 'http://photos-s3-bucket-b2-6998.s3-website-us-east-1.amazonaws.com/'

    if ans1 != '':
        for photo in ans1:
            if photo['objectKey'] in photos_set:
                continue
            photo_info = {
                'url': s3url + photo['objectKey'],
                'labels': photo['labels']
            }
            photos.append(photo_info)
            photos_set.add(photo['objectKey'])

    if ans2 != '':
        for photo in ans2:
            if photo['objectKey'] in photos_set:
                continue
            photo_info = {
                'url': s3url + photo['objectKey'],
                'labels': photo['labels']
            }
            photos.append(photo_info)
            photos_set.add(photo['objectKey'])

    if len(photos) > 0:
        return {
            'statusCode': 200,
            'body': photos
        }
    else:
        return {
            'statusCode': 6998,
            'body': 'no results'
        }
